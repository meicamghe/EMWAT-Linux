#!/usr/bin/env python3
"""Resolve ImageGear/ImageEn import thunks and attribute calls to TD32 procedures.

Stage 1 discovers canonical x86 FF 25 import thunks from executable PE sections.
Stage 2 disassembles each bounded TD32 procedure and attributes decoded CALL
instructions to their containing Delphi procedure. This avoids treating every
raw E8 byte sequence in a section as a genuine call site.
"""
import pathlib
import re
import struct
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

from analyze_emwat_td32 import find_td32, parse_td32


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "analysis-input/EmwatMethods.bpl1")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-imaging-import-callers.md")
    blob = src.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    base = pe.OPTIONAL_HEADER.ImageBase

    imports = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("ascii", "replace")
        if "GEAR32PD" not in dll.upper() and "PKIECTRL23" not in dll.upper():
            continue
        for imp in entry.imports:
            if not imp.address:
                continue
            name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
            imports[imp.address] = (dll, name)

    executable = []
    thunks = {}
    for sec in pe.sections:
        if not (sec.Characteristics & 0x20000000):
            continue
        start = base + sec.VirtualAddress
        code = sec.get_data()
        executable.append((start, code))
        for i in range(max(0, len(code) - 5)):
            if code[i] == 0xFF and code[i + 1] == 0x25:
                slot = struct.unpack_from("<I", code, i + 2)[0]
                if slot in imports:
                    thunks[start + i] = (slot, imports[slot])

    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    td_base, td_end, directory, _ = hit
    _, _, modules, procedures = parse_td32(blob, td_base, td_end, directory)

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    calls = {slot: [] for slot in imports}
    mapped_procedures = 0
    decoded_calls = 0

    # TD32 logical segment numbers map to PE sections in this BPL. Use the
    # module's own segment bounds as an additional guard against bad records.
    for proc in procedures:
        segno = proc["segment"]
        if not (1 <= segno <= len(pe.sections)):
            continue
        sec = pe.sections[segno - 1]
        module = modules.get(proc["module"])
        seg = next((s for s in module[1] if s[0] == segno), None) if module else None
        if not seg or not (sec.Characteristics & 0x20000000):
            continue
        _, _, seg_start, seg_size = seg
        off, size = proc["offset"], proc["size"]
        if size <= 0 or not (seg_start <= off and off + size <= seg_start + seg_size):
            continue
        if off + size > sec.SizeOfRawData:
            continue
        raw = sec.PointerToRawData + off
        if raw + size > len(blob):
            continue

        va = base + sec.VirtualAddress + off
        mapped_procedures += 1
        for ins in md.disasm(blob[raw:raw + size], va):
            if ins.mnemonic != "call":
                continue
            decoded_calls += 1
            operand = ins.op_str.strip()
            target_match = re.fullmatch(r"(?:0x)?([0-9a-fA-F]{6,8})", operand)
            if target_match:
                target = int(target_match.group(1), 16) & 0xFFFFFFFF
                if target in thunks:
                    slot, (dll, name) = thunks[target]
                    calls[slot].append((ins.address, proc["name"], target, "thunk"))
                continue
            iat_match = re.search(r"\[(0x[0-9a-fA-F]+)\]", operand)
            if iat_match:
                slot = int(iat_match.group(1), 16)
                if slot in imports:
                    calls[slot].append((ins.address, proc["name"], None, "direct-IAT"))

    lines = [
        "# Imaging import call-site map", "",
        f"- Input: {src}",
        f"- ImageGear/ImageEn import slots: {len(imports)}",
        f"- Executable sections scanned for FF 25 thunks: {len(executable)}",
        f"- Import thunks resolved: {len(thunks)}",
        f"- TD32 procedures mapped to bounded PE code: {mapped_procedures}",
        f"- Decoded CALL instructions in those procedures: {decoded_calls}",
        "- Call sites below are decoded instructions attributed to their containing TD32 procedure; runtime execution is not implied.", "",
        "| DLL | Imported API | IAT slot | Thunk VA | Caller procedure | Call-site VA(s) |",
        "|---|---|---:|---:|---|---|",
    ]

    for slot, (dll, name) in sorted(imports.items(), key=lambda x: (x[1][0].lower(), x[1][1].lower())):
        refs = calls.get(slot, [])
        if not refs:
            lines.append(f"| {dll} | {name} | 0x{slot:08X} | " +
                         (", ".join(f"0x{va:08X}" for va, (s, _) in thunks.items() if s == slot) or "—") +
                         " | — | — |")
            continue
        thunk_vas = sorted({target for _, _, target, kind in refs if target is not None})
        thunk_text = ", ".join(f"0x{x:08X}" for x in thunk_vas) or "direct IAT"
        by_proc = {}
        for site, proc_name, target, kind in refs:
            by_proc.setdefault(proc_name, []).append(site)
        for proc_name, sites in sorted(by_proc.items()):
            lines.append(f"| {dll} | {name} | 0x{slot:08X} | {thunk_text} | {proc_name} | " +
                         ", ".join(f"0x{x:08X}" for x in sorted(sites)) + " |")

    lines += [
        "",
        "## Interpretation notes",
        "",
        "- Thunk identity comes from the PE import descriptor's IAT slot reached by an x86 indirect-jump thunk.",
        "- Caller attribution comes from disassembling each bounded TD32 procedure, not from scanning arbitrary section bytes for relative-call opcodes.",
        "- A decoded static call proves a code reference, not that the application executes that path at runtime.",
        "- Imports with no attributed CALL may be package/class metadata, initialization/finalization, unresolved indirect dispatch, or methods not represented by a decoded TD32 procedure.",
        "- Validate argument setup and calling convention in each caller before implementing a native replacement.",
        "",
    ]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}: imports={len(imports)}, thunks={len(thunks)}, "
          f"mapped_procedures={mapped_procedures}, decoded_calls={decoded_calls}, "
          f"attributed_calls={sum(map(len, calls.values()))}")


if __name__ == "__main__":
    main()
