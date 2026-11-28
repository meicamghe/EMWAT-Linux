from __future__ import annotations

import importlib.util
import struct
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "emwat_dump_pe_va_ranges", ROOT / "scripts" / "dump_pe_va_ranges.py"
)
assert SPEC is not None and SPEC.loader is not None
PE_DUMP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PE_DUMP
SPEC.loader.exec_module(PE_DUMP)

dump_range = PE_DUMP.dump_range
find_printable_runs = PE_DUMP.find_printable_runs
parse_pe_bytes = PE_DUMP.parse_pe_bytes


def make_pe32(
    *,
    virtual_size: int = 0x200,
    raw_size: int = 0x200,
) -> bytes:
    data = bytearray(0x500)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into(
        "<HHIIIHH",
        data,
        0x84,
        0x014C,
        1,
        0,
        0,
        0,
        0xE0,
        0x0102,
    )
    optional = 0x98
    struct.pack_into("<H", data, optional, 0x10B)
    struct.pack_into("<I", data, optional + 28, 0x400000)
    struct.pack_into("<I", data, optional + 60, 0x200)
    section = optional + 0xE0
    data[section:section + 8] = b".text\0\0\0"
    struct.pack_into(
        "<IIII",
        data,
        section + 8,
        virtual_size,
        0x1000,
        raw_size,
        0x200,
    )
    data[0x210:0x220] = bytes(range(0x40, 0x50))
    return bytes(data)


def test_pe32_va_maps_to_raw_file_offset():
    image = parse_pe_bytes(make_pe32())
    assert image.image_base == 0x400000
    assert image.va_to_offset(0x401010) == 0x210
    assert image.data[image.va_to_offset(0x401010, 0x10)] == 0x40


def test_pe_header_va_maps_directly():
    image = parse_pe_bytes(make_pe32())
    assert image.va_to_offset(0x400100, 0x20) == 0x100


def test_virtual_only_section_tail_is_not_mapped_to_file():
    image = parse_pe_bytes(make_pe32(virtual_size=0x300, raw_size=0x100))
    with pytest.raises(ValueError, match="zero-filled virtual data"):
        image.va_to_offset(0x401180, 4)


def test_range_cannot_cross_raw_section_boundary():
    image = parse_pe_bytes(make_pe32(virtual_size=0x200, raw_size=0x100))
    with pytest.raises(ValueError, match="zero-filled virtual data"):
        image.va_to_offset(0x4010F0, 0x20)


def test_utf16le_string_scanner_reports_virtual_address():
    data = "Open".encode("utf-16le") + b"\0\0" + b"\x00\x00"
    assert list(find_printable_runs(data, 0x401000, wide=True)) == [
        (0x401000, "Open")
    ]


def test_dump_range_includes_va_and_raw_bytes():
    image = parse_pe_bytes(make_pe32())
    output = dump_range(image, 0x401010, 0x10)
    assert "VA 0x00401010" in output
    assert "file offset 0x210" in output
    assert "0x00401010" in output
    assert "40 41 42 43" in output
