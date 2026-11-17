#!/usr/bin/env python3
"""Byte-scan executable PE sections for FF 15/FF 25 absolute IAT references."""
from __future__ import annotations

import pathlib
import struct
import sys

import pefile


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: scan_pe_ff15_iat_refs.py <pe-file> <iat-va> [output.md]"
        )
    source = pathlib.Path(sys.argv[1])
    target = int(sys.argv[2], 0) & 0xFFFFFFFF
    output = pathlib.Path(
        sys.argv[3] if len(sys.argv) > 3 else "analysis/pe-indirect-call-refs.md"
    )
    pe = pefile.PE(data=source.read_bytes(), fast_load=False)
    rows: list[tuple[int, str, str, bytes]] = []

    for section in pe.sections:
        if not (section.Characteristics & 0x20000000):
            continue
        code = section.get_data()
        base_va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress
        name = section.Name.rstrip(bytes([0])).decode("ascii", "replace")
        for offset in range(max(0, len(code) - 5)):
            if code[offset] != 0xFF or code[offset + 1] not in (0x15, 0x25):
                continue
            operand = struct.unpack_from("<I", code, offset + 2)[0]
            if operand != target:
                continue
            lo = max(0, offset - 8)
            hi = min(len(code), offset + 10)
            kind = "CALL [absolute]" if code[offset + 1] == 0x15 else "JMP [absolute]"
            rows.append((base_va + offset, name, kind, code[lo:hi]))

    lines = [
        "# x86 absolute indirect IAT reference scan",
        "",
        f"- Input: `{source}`",
        f"- IAT VA: `0x{target:08X}`",
        "- Scans executable bytes for FF 15 (CALL [abs]) and FF 25 (JMP [abs]).",
        "- Byte matches are candidates; validate callsites in surrounding disassembly.",
        "",
    ]
    if not rows:
        lines.append("- No FF 15/FF 25 references found.")
    for address, section_name, kind, sample in sorted(rows):
        lines += [
            f"## {kind} at 0x{address:08X} ({section_name})",
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
