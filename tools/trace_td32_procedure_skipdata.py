#!/usr/bin/env python3
"""Disassemble a TD32 procedure while preserving alignment across embedded data.

Capstone's skipdata mode emits .byte pseudo-instructions for undecodable spans,
allowing analysis to continue after inline constants/data. Such pseudo-instructions
are not code and must not be interpreted as executable instructions.
"""
import pathlib
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from analyze_emwat_td32 import find_td32, parse_td32


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: trace_td32_procedure_skipdata.py <pe-file> <target-va> [output.md]"
        )
    src = pathlib.Path(sys.argv[1])
    target = int(sys.argv[2], 0) & 0xFFFFFFFF
    out = pathlib.Path(
        sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/TD32-procedure-skipdata.md"
    )
    blob = src.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = hit
    _, names, modules, procedures = parse_td32(blob, base, end, directory)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    matches = []
    for proc in procedures:
        if not (1 <= proc["segment"] <= len(pe.sections)):
            continue
        section = pe.sections[proc["segment"] - 1]
        module = modules.get(proc["module"])
        segment = next(
            (item for item in module[1] if item[0] == proc["segment"]), None
        ) if module else None
        if not segment:
            continue
        _, _, segbase, segsize = segment
        if not (
            segbase <= proc["offset"]
            and proc["offset"] + proc["size"] <= segbase + segsize
        ):
            continue
        if proc["offset"] + proc["size"] > section.SizeOfRawData:
            continue
        start_va = image_base + section.VirtualAddress + proc["offset"]
        end_va = start_va + proc["size"]
        if start_va <= target < end_va:
            matches.append((proc, section, start_va))
    lines = [
        "# TD32 procedure trace (Capstone skipdata enabled)",
        "",
        "- Warning: `.byte` entries are undecoded data bytes, not instructions.",
        "- Skipdata mode is used to continue after inline data; validate control-flow targets before interpreting later instructions.",
        "",
        f"- Input: {src}",
        f"- Requested VA: 0x{target:08X}",
        "",
    ]
    if not matches:
        lines.append("- No TD32 procedure range contains the requested VA.")
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.skipdata = True
    for proc, section, start_va in sorted(matches, key=lambda item: item[2]):
        raw = section.PointerToRawData + proc["offset"]
        code = blob[raw:raw + proc["size"]]
        module = modules.get(proc["module"])
        name_idx = module[0] if module else -1
        module_name = names[name_idx] if 0 <= name_idx < len(names) else str(proc["module"])
        decoded = list(decoder.disasm(code, start_va))
        decoded_bytes = sum(ins.size for ins in decoded)
        data_count = sum(1 for ins in decoded if ins.mnemonic == ".byte")
        lines += [
            f"## {proc['name']}",
            "",
            f"- Module: {module_name}",
            f"- Segment: {proc['segment']}",
            f"- Procedure VA range: 0x{start_va:08X}–0x{start_va + proc['size'] - 1:08X}",
            f"- Procedure size: 0x{proc['size']:X} ({proc['size']} bytes)",
            f"- PE section: {section.Name.rstrip(bytes([0])).decode('ascii', errors='replace')}",
            f"- File offset: 0x{raw:08X}",
            f"- Requested VA offset: +0x{target - start_va:X}",
            f"- Decoded byte coverage: {decoded_bytes}/{len(code)}",
            f"- .byte pseudo-instruction count: {data_count}",
            "",
            "```asm",
        ]
        for ins in decoded:
            marker = "  <-- requested VA" if ins.address == target else ""
            lines.append(f"{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}{marker}")
        lines += ["```", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}; matching procedures={len(matches)}")


if __name__ == "__main__":
    main()
