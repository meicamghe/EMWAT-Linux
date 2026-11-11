#!/usr/bin/env python3
"""Trace the Rotate90 helper and object-field +0x28 references in a Delphi PE32 BPL."""
import pathlib, struct, sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM
from analyze_emwat_td32 import find_td32, parse_td32

IMAGE_BASE = 0x00400000
TARGET_HELPER = 0x004035D8
ROTATE90 = 0x004EF138
FIELD_OFFSET = 0x28

def va_to_raw(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + s.SizeOfRawData:
            return s.PointerToRawData + rva - s.VirtualAddress
    return None

def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-rotate90-trace.md")
    blob = src.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = hit
    _, names, modules, procedures = parse_td32(blob, base, end, directory)
    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True

    mapped = []
    for p in procedures:
        if not (1 <= p["segment"] <= len(pe.sections)):
            continue
        sec = pe.sections[p["segment"] - 1]
        mod = modules.get(p["module"])
        seg = next((x for x in mod[1] if x[0] == p["segment"]), None) if mod else None
        if not seg:
            continue
        _, _, segbase, segsize = seg
        if not (segbase <= p["offset"] and p["offset"] + p["size"] <= segbase + segsize):
            continue
        if p["offset"] + p["size"] > sec.SizeOfRawData:
            continue
        rva = sec.VirtualAddress + p["offset"]
        raw = sec.PointerToRawData + p["offset"]
        if raw + p["size"] > len(blob):
            continue
        va = pe.OPTIONAL_HEADER.ImageBase + rva
        mapped.append((va, va + p["size"], p, raw))

    def proc_label(va):
        hits = [(a,b,p) for a,b,p,_ in mapped if a <= va < b]
        if not hits: return "no TD32 procedure range"
        a,b,p = min(hits, key=lambda x:x[1]-x[0])
        return f"{p['name']} (0x{a:08X}..0x{b:08X})"

    helper_raw = va_to_raw(pe, TARGET_HELPER)
    if helper_raw is None:
        raise SystemExit(f"Target helper {TARGET_HELPER:08X} is not mapped")
    helper_ins = list(md.disasm(blob[helper_raw:helper_raw+0x180], TARGET_HELPER))

    callsites = []
    field_refs = []
    for start, stop, p, raw in mapped:
        code = blob[raw:raw+p["size"]]
        for ins in md.disasm(code, start):
            if ins.mnemonic == "call" and ins.operands and ins.operands[0].type == X86_OP_IMM:
                if ins.operands[0].imm & 0xFFFFFFFF == TARGET_HELPER:
                    callsites.append((ins.address, p["name"]))
            for op in ins.operands:
                if op.type == X86_OP_MEM and op.mem.disp == FIELD_OFFSET:
                    field_refs.append((ins.address, ins.mnemonic, ins.op_str, p["name"]))

    lines = [
        "# Rotate90 helper and +0x28 field trace", "",
        f"- Input: {src}",
        f"- TD32 procedure records mapped: {len(mapped):,}",
        f"- Helper: 0x{TARGET_HELPER:08X} ({proc_label(TARGET_HELPER)})",
        f"- Rotate90: 0x{ROTATE90:08X} ({proc_label(ROTATE90)})",
        "",
        "## Helper disassembly (linear decode, capped at 0x180 bytes)", "",
        "```asm",
    ]
    lines += [f"{i.address:08X}  {i.mnemonic:<8} {i.op_str}" for i in helper_ins]
    lines += ["```", "", "## Direct callers of helper", ""]
    if callsites:
        for va, name in callsites:
            lines.append(f"- 0x{va:08X}: {name}")
    else:
        lines.append("- No direct TD32 procedure callsite found.")
    lines += ["", "## TD32 procedures accessing displacement +0x28", "",
              "- These are candidate field references only; displacement alone does not prove the field is the Rotate90 object.", ""]
    for va, mnemonic, op_str, name in field_refs:
        lines.append(f"- 0x{va:08X}: `{mnemonic} {op_str}` — {name}")
    lines += ["", "## Procedure names suggesting construction or assignment", ""]
    candidates = [p for _,_,p,_ in mapped if any(k in p["name"].lower() for k in
                  ("create", "constructor", "init", "set_", "assign", "gearimgproc", "imageprocessing"))]
    for p in candidates:
        lines.append(f"- {p['name']} (segment {p['segment']}, offset 0x{p['offset']:08X}, size 0x{p['size']:X})")
    lines += ["", "## Interpretation limits", "",
              "- The indirect call at Rotate90 reads the first pointer from the VMT of the object stored at [self+0x28].",
              "- A field-offset cross-reference is not sufficient to identify the runtime class. Follow the assignment/constructor path and resolve the stored object's VMT before assigning semantics.",
              "- The helper's linear decode may include embedded data after a return; validate function boundaries against control flow and TD32 ranges.",
              ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}; helper callers={len(callsites)}; +0x28 references={len(field_refs)}")

if __name__ == "__main__":
    main()
