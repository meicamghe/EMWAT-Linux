#!/usr/bin/env python3
"""List TD32 procedures matching symbol-name fragments with their PE VAs."""
from __future__ import annotations

import pathlib
import sys

import pefile

from analyze_emwat_td32 import find_td32, parse_td32


def main() -> None:
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: list_td32_symbols.py <pe-file> <name-fragment> [fragment ...]"
        )
    source = pathlib.Path(sys.argv[1])
    terms = tuple(item.casefold() for item in sys.argv[2:])
    blob = source.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = hit
    _, names, modules, procedures = parse_td32(blob, base, end)
    image_base = pe.OPTIONAL_HEADER.ImageBase

    rows: list[tuple[int, int, str, int, int, str]] = []
    for proc in procedures:
        name = str(proc.get("name", ""))
        if not any(term in name.casefold() for term in terms):
            continue
        segment_index = int(proc.get("segment", 0))
        if not (1 <= segment_index <= len(pe.sections)):
            continue
        section = pe.sections[segment_index - 1]
        module = modules.get(proc["module"])
        segment = next(
            (item for item in module[1] if item[0] == segment_index), None
        ) if module else None
        if not segment:
            continue
        _, _, segment_base, segment_size = segment
        offset = int(proc["offset"])
        size = int(proc["size"])
        if not (segment_base <= offset and offset + size <= segment_base + segment_size):
            continue
        if offset + size > section.SizeOfRawData:
            continue
        start_va = image_base + section.VirtualAddress + offset
        module_name = (
            names[module[0]]
            if module and 0 <= module[0] < len(names)
            else str(proc["module"])
        )
        rows.append((start_va, size, module_name, segment_index, offset, name))

    print("# TD32 symbol matches")
    print()
    print(f"- Source: `{source}`")
    print(f"- Search terms: {', '.join(terms)}")
    print(f"- Matches: {len(rows)}")
    print()
    print("| VA | Size | Module | Segment | Name |")
    print("|---:|---:|---|---:|---|")
    for va, size, module_name, segment, _offset, name in sorted(rows):
        safe_name = name.replace("|", "\\|")
        print(f"| `0x{va:08X}` | {size} | {module_name} | {segment} | `{safe_name}` |")


if __name__ == "__main__":
    main()
