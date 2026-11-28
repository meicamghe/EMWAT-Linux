#!/usr/bin/env python3
"""Dump PE virtual-address ranges and recover nearby ANSI/UTF-16LE strings.

This is a developer-side reverse-engineering helper. It uses only the Python
standard library and does not modify the input file.
"""
from __future__ import annotations

import argparse
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PESection:
    name: str
    virtual_address: int
    virtual_size: int
    raw_offset: int
    raw_size: int


@dataclass(frozen=True)
class PEImage:
    data: bytes
    image_base: int
    size_of_headers: int
    sections: tuple[PESection, ...]

    def va_to_offset(self, va: int) -> int:
        rva = va - self.image_base
        if rva < 0:
            raise ValueError(f"VA 0x{va:X} is below image base 0x{self.image_base:X}")

        if rva < self.size_of_headers:
            if rva >= len(self.data):
                raise ValueError(f"header RVA 0x{rva:X} is outside the file")
            return rva

        for section in self.sections:
            extent = max(section.virtual_size, section.raw_size)
            start = section.virtual_address
            if start <= rva < start + extent:
                delta = rva - start
                if delta >= section.raw_size:
                    raise ValueError(
                        f"VA 0x{va:X} lies in zero-filled virtual data of "
                        f"section {section.name!r}, not in the file"
                    )
                offset = section.raw_offset + delta
                if offset >= len(self.data):
                    raise ValueError(f"mapped file offset 0x{offset:X} is outside the file")
                return offset

        raise ValueError(f"VA 0x{va:X} is not covered by a PE section")


def parse_pe_bytes(data: bytes) -> PEImage:
    if len(data) < 0x40 or data[:2] != b"MZ":
        raise ValueError("input is not a valid DOS/PE image (missing MZ header)")

    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset + 24 > len(data) or data[pe_offset:pe_offset + 4] != b"PE\0\0":
        raise ValueError("input is missing a valid PE signature")

    coff_offset = pe_offset + 4
    section_count = struct.unpack_from("<H", data, coff_offset + 2)[0]
    optional_size = struct.unpack_from("<H", data, coff_offset + 16)[0]
    optional_offset = coff_offset + 20
    if optional_offset + optional_size > len(data) or optional_size < 64:
        raise ValueError("truncated PE optional header")

    magic = struct.unpack_from("<H", data, optional_offset)[0]
    if magic == 0x10B:  # PE32
        if optional_size < 64:
            raise ValueError("truncated PE32 optional header")
        image_base = struct.unpack_from("<I", data, optional_offset + 28)[0]
    elif magic == 0x20B:  # PE32+
        if optional_size < 64:
            raise ValueError("truncated PE32+ optional header")
        image_base = struct.unpack_from("<Q", data, optional_offset + 24)[0]
    else:
        raise ValueError(f"unsupported PE optional-header magic 0x{magic:04X}")

    size_of_headers = struct.unpack_from("<I", data, optional_offset + 60)[0]
    section_table = optional_offset + optional_size
    sections: list[PESection] = []

    for index in range(section_count):
        offset = section_table + index * 40
        if offset + 40 > len(data):
            raise ValueError("truncated PE section table")
        raw_name = data[offset:offset + 8].split(b"\0", 1)[0]
        name = raw_name.decode("ascii", errors="replace")
        virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from(
            "<IIII", data, offset + 8
        )
        sections.append(
            PESection(
                name=name,
                virtual_address=virtual_address,
                virtual_size=virtual_size,
                raw_offset=raw_offset,
                raw_size=raw_size,
            )
        )

    return PEImage(
        data=data,
        image_base=image_base,
        size_of_headers=size_of_headers,
        sections=tuple(sections),
    )


def find_printable_runs(data: bytes, base_va: int, *, wide: bool, minimum: int = 4):
    """Yield (VA, decoded_text) for printable ASCII or UTF-16LE runs."""
    step = 2 if wide else 1
    index = 0
    while index + step <= len(data):
        start = index
        chars: list[str] = []
        while index + step <= len(data):
            if wide:
                codepoint = data[index] | (data[index + 1] << 8)
                printable = 0x20 <= codepoint <= 0x7E
                char = chr(codepoint) if printable else ""
            else:
                codepoint = data[index]
                printable = 0x20 <= codepoint <= 0x7E
                char = chr(codepoint) if printable else ""
            if not printable:
                break
            chars.append(char)
            index += step
        if len(chars) >= minimum:
            yield base_va + start, "".join(chars)
        index = max(index + step, start + step)


def dump_range(image: PEImage, va: int, length: int) -> str:
    if length <= 0:
        raise ValueError("range length must be positive")
    offset = image.va_to_offset(va)
    end = offset + length
    if end > len(image.data):
        raise ValueError(
            f"range VA 0x{va:X}+0x{length:X} extends beyond the input file"
        )
    chunk = image.data[offset:end]
    lines = [
        f"VA 0x{va:08X} length 0x{length:X} -> file offset 0x{offset:X}",
        "  +VA       DWORD      BYTES                                           ASCII",
    ]
    for row in range(0, len(chunk), 16):
        row_bytes = chunk[row:row + 16]
        padded = row_bytes.ljust(16, b" ")
        dword = (
            f"0x{struct.unpack('<I', row_bytes[:4])[0]:08X}"
            if len(row_bytes) >= 4 else " " * 10
        )
        hex_part = " ".join(f"{value:02X}" for value in row_bytes)
        ascii_part = "".join(chr(value) if 0x20 <= value <= 0x7E else "." for value in row_bytes)
        lines.append(
            f"  0x{va + row:08X} {dword:10} {hex_part:<47} {ascii_part}"
        )

    ansi = list(find_printable_runs(chunk, va, wide=False))
    wide = list(find_printable_runs(chunk, va, wide=True))
    if ansi or wide:
        lines.append("  printable strings:")
        for address, value in ansi:
            lines.append(f"    ANSI  0x{address:08X}: {value}")
        for address, value in wide:
            lines.append(f"    UTF16 0x{address:08X}: {value}")
    return "\n".join(lines)


DEFAULT_RANGES = (
    (0x0047DD2C, 0xA0),  # TGPImage interface metadata
    (0x0062EE88, 0x90),  # candidate interface VTable blocks
    (0x004A1784, 0x190),  # hidden print-worker string area
    (0x004026B4, 0x80),  # stale-output helper
    (0x0044B508, 0x80),  # ForceSinglePageFiles XMLRTL helper
)


def parse_range(value: str) -> tuple[int, int]:
    try:
        address_text, length_text = value.split(":", 1)
        address = int(address_text, 0)
        length = int(length_text, 0)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(
            "range must be VA:LENGTH, for example 0x0062EE88:0x90"
        ) from exc
    if address < 0 or length <= 0:
        raise argparse.ArgumentTypeError("range address must be non-negative and length positive")
    return address, length


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pe_file", type=Path, help="original PE/BPL file")
    parser.add_argument(
        "--range",
        dest="ranges",
        action="append",
        type=parse_range,
        help="VA:LENGTH range; repeat to override the built-in EMWAT ranges",
    )
    args = parser.parse_args()

    data = args.pe_file.read_bytes()
    image = parse_pe_bytes(data)
    ranges = tuple(args.ranges) if args.ranges else DEFAULT_RANGES
    print(
        f"PE image base: 0x{image.image_base:X}; "
        f"sections: {len(image.sections)}; file size: 0x{len(data):X}"
    )
    for index, section in enumerate(image.sections):
        print(
            f"  {section.name:8} RVA=0x{section.virtual_address:08X} "
            f"VS=0x{section.virtual_size:X} RAW=0x{section.raw_offset:X}/0x{section.raw_size:X}"
        )
    for va, length in ranges:
        print()
        print(dump_range(image, va, length))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
