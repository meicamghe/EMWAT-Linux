#!/usr/bin/env python3
"""Find raw PE references to an absolute VA (including data-section callback pointers)."""
import pathlib
import struct
import sys

import pefile


def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: scan_pe_pointer_refs.py <pe-file> <target-va> [output.md]")
    src = pathlib.Path(sys.argv[1])
    target = int(sys.argv[2], 0) & 0xFFFFFFFF
    out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/PE-pointer-refs.md")
    blob = src.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    needle = struct.pack("<I", target)

    lines = [
        "# Raw PE pointer-reference scan",
        "",
        f"- Input: `{src}`",
        f"- Target VA: `0x{target:08X}`",
        "- Scans raw section bytes for the exact little-endian 32-bit VA; this can find code immediates and static data pointers.",
        "- A match is a byte-pattern reference only. It does not by itself prove the value is a callback registration or a live pointer.",
        "",
        "## Matches",
        "",
    ]
    total = 0
    for section in pe.sections:
        data = section.get_data()
        if not data:
            continue
        name = section.Name.rstrip(b"\\0").decode("ascii", "replace")
        flags = []
        if section.Characteristics & 0x20000000:
            flags.append("execute")
        if section.Characteristics & 0x40000000:
            flags.append("read")
        if section.Characteristics & 0x80000000:
            flags.append("write")
        pos = 0
        while True:
            hit = data.find(needle, pos)
            if hit < 0:
                break
            total += 1
            raw = section.PointerToRawData + hit
            va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress + hit
            before = data[max(0, hit - 12):hit].hex(" ")
            after = data[hit + 4:min(len(data), hit + 20)].hex(" ")
            lines += [
                f"### Match {total}",
                "",
                f"- Section: `{name}` ({','.join(flags) or 'no-flags'})",
                f"- Section VA: `0x{va:08X}`",
                f"- Raw file offset: `0x{raw:08X}`",
                f"- Bytes before: `{before}`",
                f"- Bytes after: `{after}`",
                "",
            ]
            pos = hit + 1
    if total == 0:
        lines.append("No exact raw 32-bit references found.")
    lines += ["", f"- Total matches: {total}", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}; matches={total}")


if __name__ == "__main__":
    main()
