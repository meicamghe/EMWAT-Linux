#!/usr/bin/env python3
"""Disassemble a bounded x86 PE VA range without requiring TD32 procedure records."""
import pathlib
import re
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32


def va_to_raw(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for sec in pe.sections:
        lo = sec.VirtualAddress
        span = max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if lo <= rva < lo + span:
            raw = sec.PointerToRawData + rva - lo
            if raw < len(pe.__data__):
                return raw, sec
    return None, None


def main():
    if len(sys.argv) < 5:
        raise SystemExit(
            "usage: trace_pe_range.py <pe-file> <start-VA> <end-VA> <output.md>"
        )
    path = pathlib.Path(sys.argv[1])
    start = int(sys.argv[2], 0)
    end = int(sys.argv[3], 0)
    out = pathlib.Path(sys.argv[4])
    if end <= start:
        raise SystemExit("end-VA must be greater than start-VA")

    pe = pefile.PE(str(path), fast_load=False)
    blob = path.read_bytes()
    start_raw, start_sec = va_to_raw(pe, start)
    end_raw, end_sec = va_to_raw(pe, end - 1)
    if start_raw is None or end_raw is None or start_sec != end_sec:
        raise SystemExit("requested range must be file-backed in one PE section")
    if end_raw <= start_raw:
        raise SystemExit("invalid raw range")

    imports = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("ascii", "replace")
        for imp in entry.imports:
            if imp.address:
                name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
                imports[imp.address] = f"{dll}!{name}"

    code = blob[start_raw:end_raw + 1]
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    insns = list(decoder.disasm(code, start))
    secname = start_sec.Name.rstrip(bytes([0])).decode("ascii", "replace")
    lines = [
        "# Bounded PE code-range trace",
        "",
        f"- Input: `{path}`",
        f"- VA range: `0x{start:08X}–0x{end:08X}`",
        f"- Raw range: `0x{start_raw:08X}–0x{end_raw:08X}`",
        f"- Section: `{secname}`",
        f"- Decoded instructions: {len(insns)}",
        "",
        "> Range boundaries are caller-supplied. They may include alignment bytes or adjacent data; confirm function boundaries using VMT targets and other references.",
        "",
        "## Disassembly",
        "",
    ]
    cursor = start
    for ins in insns:
        if ins.address != cursor:
            lines.append(f"`{cursor:08X}`  <undecoded bytes>")
        rawhex = ins.bytes.hex(" ")
        note = ""
        direct = re.fullmatch(r"(?:0x)?([0-9a-fA-F]{6,8})", ins.op_str.strip())
        if ins.mnemonic in ("call", "jmp") and direct:
            target = int(direct.group(1), 16) & 0xFFFFFFFF
            if target in imports:
                note = f"  ; IAT: {imports[target]}"
        lines.append(
            f"`{ins.address:08X}`  `{rawhex}`  {ins.mnemonic:<8} {ins.op_str}{note}"
        )
        cursor = ins.address + ins.size
    if cursor < end:
        lines.append(f"`{cursor:08X}`  <{end-cursor} trailing bytes not decoded>")
    lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
