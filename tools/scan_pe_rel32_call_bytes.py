#!/usr/bin/env python3
"""Byte-level scan for x86 rel32 CALL encodings in executable PE sections.

This deliberately does not linearly disassemble from section start: PE code
sections can contain alignment/data and a linear sweep may lose instruction
boundaries before a real CALL. Matches are candidates only; validate each
address with a function-bounded disassembly before assigning semantics.
"""
from __future__ import annotations

import pathlib
import struct
import sys

import pefile


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: scan_pe_rel32_call_bytes.py <pe-file> <target-va> [output.md]"
        )
    source = pathlib.Path(sys.argv[1])
    target = int(sys.argv[2], 0) & 0xFFFFFFFF
    output = pathlib.Path(
        sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/rel32-call-byte-candidates.md"
    )
    pe = pefile.PE(data=source.read_bytes(), fast_load=False)
    rows: list[tuple[int, str, bytes]] = []

    for section in pe.sections:
        if not (section.Characteristics & 0x20000000):
            continue
        code = section.get_data()
        base_va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress
        name = section.Name.rstrip(bytes([0])).decode("ascii", "replace")
        for offset in range(max(0, len(code) - 4)):
            if code[offset] != 0xE8:
                continue
            displacement = struct.unpack_from("<i", code, offset + 1)[0]
            destination = (base_va + offset + 5 + displacement) & 0xFFFFFFFF
            if destination == target:
                lo = max(0, offset - 8)
                hi = min(len(code), offset + 13)
                rows.append((base_va + offset, name, code[lo:hi]))

    lines = [
        "# x86 rel32 CALL byte-pattern candidates",
        "",
        f"- Input: `{source}`",
        f"- Target VA: `0x{target:08X}`",
        "- Scans every byte in executable sections for opcode E8 + signed rel32.",
        "- This is a candidate scan, not instruction-boundary proof; inspect each site in its surrounding function.",
        "",
    ]
    if not rows:
        lines.append("- No E8 rel32 byte-pattern candidates found.")
    for call_va, section_name, sample in sorted(rows):
        lines += [
            f"## Candidate at 0x{call_va:08X} ({section_name})",
            "",
            f"- Bytes around candidate: `{sample.hex(' ')}`",
            "",
        ]
    lines += [f"- Total candidates: {len(rows)}", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output}; candidates={len(rows)}")


if __name__ == "__main__":
    main()
