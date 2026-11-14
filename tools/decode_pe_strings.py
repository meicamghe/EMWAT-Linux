#!/usr/bin/env python3
"""Decode ANSI and UTF-16LE strings stored at PE virtual addresses."""
import argparse
import pathlib
import pefile


def va_to_raw(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for section in pe.sections:
        start = section.VirtualAddress
        span = max(section.Misc_VirtualSize, section.SizeOfRawData)
        if start <= rva < start + span:
            raw = section.PointerToRawData + rva - start
            if raw < len(pe.__data__):
                return raw, section
    return None, None


def read_terminated(blob, offset, limit, terminator):
    end = blob.find(terminator, offset, min(len(blob), offset + limit))
    if end < 0:
        end = min(len(blob), offset + limit)
    return blob[offset:end]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=pathlib.Path)
    parser.add_argument("vas", nargs="+", type=lambda value: int(value, 0))
    parser.add_argument("--max-bytes", type=lambda value: int(value, 0), default=0x400)
    args = parser.parse_args()

    blob = args.input.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    for va in args.vas:
        raw, section = va_to_raw(pe, va)
        print(f"VA 0x{va:08X}:")
        if raw is None:
            print("  not file-backed")
            continue
        name = section.Name.rstrip(b"\\x00").decode("ascii", "replace")
        print(f"  raw=0x{raw:08X} section={name}")
        if raw >= 8:
            refcount = int.from_bytes(blob[raw - 8:raw - 4], "little", signed=True)
            length = int.from_bytes(blob[raw - 4:raw], "little", signed=True)
            print(f"  possible Delphi header: refcount={refcount} length={length}")
        wide = read_terminated(blob, raw, args.max_bytes, b"\\x00\\x00")
        if len(wide) % 2:
            wide = wide[:-1]
        try:
            decoded_wide = wide.decode("utf-16le").replace("\\r", "\\r").replace("\\n", "\\n")
        except UnicodeDecodeError:
            decoded_wide = "<invalid UTF-16LE>"
        ansi = read_terminated(blob, raw, args.max_bytes, b"\\x00")
        decoded_ansi = ansi.decode("cp1252", "replace")
        print(f"  UTF-16LE: {decoded_wide!r}")
        print(f"  ANSI: {decoded_ansi!r}")


if __name__ == "__main__":
    main()
