#!/usr/bin/env python3
"""Inspect a PE global pointer to a small table of Delphi string pointers.

This is a static-data aid, not a runtime memory dumper. It reports when a global
or pointed-to object lives in zero-filled/unmapped data rather than inventing
values. Delphi UnicodeString pointers are decoded only when the preceding
length field is plausible.
"""
from __future__ import annotations

import pathlib
import struct
import sys

import pefile


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit(
            "usage: dump_pe_delphi_pointer_table.py <pe-file> <global-va> "
            "<entry-count> [output.md]"
        )
    source = pathlib.Path(sys.argv[1])
    global_va = int(sys.argv[2], 0) & 0xFFFFFFFF
    count = int(sys.argv[3], 0)
    output = pathlib.Path(
        sys.argv[4] if len(sys.argv) > 4 else "bpl-analysis/delphi-pointer-table.md"
    )
    if not 1 <= count <= 64:
        raise SystemExit("entry-count must be between 1 and 64")

    blob = source.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    image_base = int(pe.OPTIONAL_HEADER.ImageBase)

    def raw_offset(va: int) -> int | None:
        rva = va - image_base
        if rva < 0:
            return None
        for section in pe.sections:
            start = int(section.VirtualAddress)
            raw_size = int(section.SizeOfRawData)
            if start <= rva < start + raw_size:
                return int(section.PointerToRawData) + (rva - start)
        return None

    def read_u32(va: int) -> int | None:
        offset = raw_offset(va)
        if offset is None or offset + 4 > len(blob):
            return None
        return struct.unpack_from("<I", blob, offset)[0]

    def decode_delphi_unicode(va: int) -> str | None:
        data_offset = raw_offset(va)
        length_offset = raw_offset(va - 4)
        if data_offset is None or length_offset is None:
            return None
        length = struct.unpack_from("<I", blob, length_offset)[0]
        if length > 512 or data_offset + length * 2 > len(blob):
            return None
        raw = blob[data_offset:data_offset + length * 2]
        try:
            return raw.decode("utf-16le").replace("\\x00", "\\\\0")
        except UnicodeDecodeError:
            return None

    lines = [
        "# Delphi pointer-table inspection",
        "",
        f"- Input PE: `{source}`",
        f"- Global pointer VA: `0x{global_va:08X}`",
        f"- Requested entries: {count}",
        "- Static file bytes only; relocated/runtime-initialized pointers may be unavailable.",
        "",
    ]
    global_offset = raw_offset(global_va)
    if global_offset is None:
        lines += [
            "The global pointer has no raw-file backing (possibly zero-filled or runtime-initialized).",
            "",
        ]
    else:
        table_va = read_u32(global_va)
        lines += [
            f"- Global raw offset: `0x{global_offset:08X}`",
            f"- Stored table pointer: `{('0x%08X' % table_va) if table_va is not None else 'unreadable'}`",
            "",
        ]
        if table_va in (None, 0) or raw_offset(table_va) is None:
            lines += [
                "The pointed-to table is not statically backed by raw section bytes; no entries decoded.",
                "",
            ]
        else:
            lines += ["## Entries", ""]
            for index in range(count):
                slot_va = table_va + index * 4
                pointer = read_u32(slot_va)
                lines.append(f"### Entry {index}")
                lines.append("")
                lines.append(f"- Slot VA: `0x{slot_va:08X}`")
                lines.append(
                    f"- Stored pointer: `{('0x%08X' % pointer) if pointer is not None else 'unreadable'}`"
                )
                if pointer not in (None, 0):
                    decoded = decode_delphi_unicode(pointer)
                    if decoded is None:
                        lines.append("- Delphi UnicodeString decode: unavailable/unverified")
                    else:
                        lines.append(f"- Delphi UnicodeString candidate: `{decoded}`")
                lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
