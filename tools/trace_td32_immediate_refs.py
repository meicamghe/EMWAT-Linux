#!/usr/bin/env python3
"""Find immediate-address references to a VA inside TD32-bounded procedures."""
import pathlib
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const
from analyze_emwat_td32 import find_td32, parse_td32


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: trace_td32_immediate_refs.py <pe-file> <target-va> [output.md]")
    src = pathlib.Path(sys.argv[1])
    target = int(sys.argv[2], 0) & 0xFFFFFFFF
    out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/EmwatMethods-immediate-refs.md")
    blob = src.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = hit
    _, _, modules, procedures = parse_td32(blob, base, end, directory)
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    rows = []
    for proc in procedures:
        if not (1 <= proc["segment"] <= len(pe.sections)):
            continue
        sec = pe.sections[proc["segment"] - 1]
        module = modules.get(proc["module"])
        seg = next((item for item in module[1] if item[0] == proc["segment"]), None) if module else None
        if not seg:
            continue
        _, _, segbase, segsize = seg
        if not (segbase <= proc["offset"] and proc["offset"] + proc["size"] <= segbase + segsize):
            continue
        if proc["offset"] + proc["size"] > sec.SizeOfRawData:
            continue
        raw = sec.PointerToRawData + proc["offset"]
        va = pe.OPTIONAL_HEADER.ImageBase + sec.VirtualAddress + proc["offset"]
        insns = list(decoder.disasm(blob[raw:raw + proc["size"]], va))
        for index, ins in enumerate(insns):
            if not any(op.type == x86_const.X86_OP_IMM and (op.imm & 0xFFFFFFFF) == target for op in ins.operands):
                continue
            lo = max(0, index - 5)
            hi = min(len(insns), index + 6)
            context = "\n".join(
                f"  {item.address:08X}  {item.mnemonic:<8} {item.op_str}"
                for item in insns[lo:hi]
            )
            rows.append((proc["name"], ins.address, context))
    lines = [
        "# TD32 immediate-reference scan", "",
        f"- Target VA: 0x{target:08X}",
        "- Scans immediate operands inside TD32-bounded procedures; it does not detect computed addresses or arbitrary data references.", ""
    ]
    if not rows:
        lines.append("- No immediate references found.")
    for name, va, context in sorted(rows, key=lambda item: item[1]):
        lines += [f"## {name} — reference at 0x{va:08X}", "", "```asm", context, "```", ""]
    lines += [f"- Total immediate references: {len(rows)}", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}; immediate references={len(rows)}")


if __name__ == "__main__":
    main()
