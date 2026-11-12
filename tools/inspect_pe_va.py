#!/usr/bin/env python3
"""Inspect a PE virtual address and nearby pointer/string data."""
import argparse
import pathlib
import struct
import pefile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("va", type=lambda x: int(x, 0))
    ap.add_argument("--before", type=lambda x: int(x, 0), default=0x60)
    ap.add_argument("--after", type=lambda x: int(x, 0), default=0xA0)
    args = ap.parse_args()

    blob = pathlib.Path(args.input).read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase

    def raw_offset(va):
        rva = va - image_base
        for sec in pe.sections:
            start = sec.VirtualAddress
            end = start + max(sec.Misc_VirtualSize, sec.SizeOfRawData)
            if start <= rva < end:
                off = sec.PointerToRawData + (rva - start)
                if off < len(blob):
                    return off, sec.Name.rstrip(b"\\0").decode("ascii", "replace")
        return None, None

    print(f"ImageBase=0x{image_base:08X} target=0x{args.va:08X}")
    for va in range(args.va - args.before, args.va + args.after, 4):
        off, secname = raw_offset(va)
        if off is None or off + 4 > len(blob):
            print(f"0x{va:08X}: <not file-backed>")
            continue
        value = struct.unpack_from("<I", blob, off)[0]
        target_off, target_sec = raw_offset(value)
        extra = f" -> file+0x{target_off:X} ({target_sec})" if target_off is not None else ""
        print(f"0x{va:08X}: {value:08X}{extra}")

    off, secname = raw_offset(args.va)
    if off is not None:
        print(f"\\nASCII candidates at target (section {secname}):")
        for delta in range(0, 0x80, 4):
            pos = off + delta
            chunk = blob[pos:pos+48].split(b"\\0", 1)[0]
            if len(chunk) >= 4 and all(32 <= b < 127 for b in chunk):
                print(f"+0x{delta:X}: {chunk.decode('ascii', 'replace')}")

if __name__ == "__main__":
    main()
