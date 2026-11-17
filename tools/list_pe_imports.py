#!/usr/bin/env python3
"""List PE import descriptors and IAT addresses for reverse-engineering."""
from __future__ import annotations

import pathlib
import sys

import pefile


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("usage: list_pe_imports.py <pe-file> [output.md]")
    source = pathlib.Path(sys.argv[1])
    output = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "analysis/pe-imports.md")
    pe = pefile.PE(data=source.read_bytes(), fast_load=False)
    lines = [
        "# PE import table",
        "",
        f"- Input: `{source}`",
        f"- Image base: `0x{pe.OPTIONAL_HEADER.ImageBase:08X}`",
        "",
    ]
    count = 0
    for descriptor in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = descriptor.dll.decode("ascii", "replace") if descriptor.dll else "?"
        lines += [f"## {dll}", ""]
        for imp in descriptor.imports:
            name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
            lines.append(f"- IAT `0x{imp.address:08X}`: `{name}`")
            count += 1
        lines.append("")
    lines += [f"- Total imported symbols: {count}", ""]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {output}; imports={count}")


if __name__ == "__main__":
    main()
