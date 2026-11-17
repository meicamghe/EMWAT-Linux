#!/usr/bin/env python3
"""Resolve exact x86 IAT JMP thunks and direct callers in a PE."""
from __future__ import annotations

import pathlib
import struct
import sys

import pefile


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit("usage: scan_pe_iat_callers.py <pe-file> <iat-va> [<iat-va> ...]")
    source = pathlib.Path(sys.argv[1])
    targets = [int(value, 0) & 0xFFFFFFFF for value in sys.argv[2:]]
    pe = pefile.PE(data=source.read_bytes(), fast_load=False)
    base = pe.OPTIONAL_HEADER.ImageBase
    sections = [
        (base + section.VirtualAddress, section.get_data(),
         section.Name.rstrip(bytes([0])).decode("ascii", "replace"))
        for section in pe.sections if section.Characteristics & 0x20000000
    ]

    print(f"# IAT thunk and caller scan\n\n- Input: {source}\n- Image base: 0x{base:08X}\n")
    for target in targets:
        thunks: list[tuple[int, str]] = []
        direct_iat_calls: list[tuple[int, str]] = []
        for va, data, name in sections:
            for offset in range(max(0, len(data) - 5)):
                op = data[offset:offset + 2]
                operand = struct.unpack_from("<I", data, offset + 2)[0]
                if op == b"\xff\x25" and operand == target:
                    thunks.append((va + offset, name))
                elif op == b"\xff\x15" and operand == target:
                    direct_iat_calls.append((va + offset, name))

        thunk_vas = {va for va, _ in thunks}
        rel_calls: list[tuple[int, int, str]] = []
        for va, data, name in sections:
            for offset in range(max(0, len(data) - 4)):
                if data[offset] != 0xE8:
                    continue
                displacement = struct.unpack_from("<i", data, offset + 1)[0]
                destination = (va + offset + 5 + displacement) & 0xFFFFFFFF
                if destination in thunk_vas:
                    rel_calls.append((va + offset, destination, name))

        print(f"## IAT 0x{target:08X}")
        if thunks:
            for address, name in thunks:
                print(f"- JMP thunk: 0x{address:08X} ({name})")
        else:
            print("- No exact FF 25 IAT thunk found.")
        if direct_iat_calls:
            for address, name in direct_iat_calls:
                print(f"- Direct CALL [IAT]: 0x{address:08X} ({name})")
        if rel_calls:
            for address, destination, name in rel_calls:
                print(f"- Direct CALL rel32 to thunk 0x{destination:08X}: 0x{address:08X} ({name})")
        if not direct_iat_calls and not rel_calls:
            print("- No direct callsites found by FF 15 or E8 rel32 scan.")
        print("")


if __name__ == "__main__":
    main()
