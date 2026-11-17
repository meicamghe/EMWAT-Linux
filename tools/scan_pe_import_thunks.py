#!/usr/bin/env python3
"""Locate exact x86 absolute IAT JMP/CALL instruction sites in a PE.

Raw pointer-reference scans identify the four-byte IAT operand, not the start
of the instruction. This scanner matches the complete FF 25 / FF 15 opcode
plus its absolute IAT operand and reports the exact instruction VA.
"""
from __future__ import annotations

import pathlib
import struct
import sys

import pefile


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: scan_pe_import_thunks.py <pe-file> <iat-va> [<iat-va> ...]"
        )
    source = pathlib.Path(sys.argv[1])
    targets = [int(value, 0) & 0xFFFFFFFF for value in sys.argv[2:]]
    pe = pefile.PE(data=source.read_bytes(), fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    rows: list[tuple[int, int, str, str]] = []

    for section in pe.sections:
        if not (section.Characteristics & 0x20000000):
            continue
        blob = section.get_data()
        base_va = image_base + section.VirtualAddress
        for i in range(max(0, len(blob) - 5)):
            opcode = blob[i:i + 2]
            if opcode not in (b"\\xff\\x25", b"\\xff\\x15"):
                continue
            operand = struct.unpack_from("<I", blob, i + 2)[0]
            if operand in targets:
                kind = "JMP [IAT]" if opcode == b"\\xff\\x25" else "CALL [IAT]"
                rows.append((operand, base_va + i, kind, section.Name.rstrip(bytes([0])).decode("ascii", "replace")))

    print(f"# Exact PE import thunk instruction scan\n\n- Input: `{source}`\n- Image base: `0x{image_base:08X}`\n")
    for target in targets:
        matches = [row for row in rows if row[0] == target]
        print(f"## IAT `0x{target:08X}`")
        if not matches:
            print("- No FF 25/FF 15 absolute IAT instruction found.\n")
            continue
        for _, va, kind, section in matches:
            print(f"- `0x{va:08X}`: `{kind}` ({section})")
        print("")

if __name__ == "__main__":
    main()
