#!/usr/bin/env python3
"""Scan TD32-bounded methods of a Delphi class for field-offset references."""

from __future__ import annotations

import argparse
import pathlib
import re
import subprocess
import sys

import pefile
from capstone import CS_ARCH_X86, CS_MODE_32, Cs, CS_AC_READ, CS_AC_WRITE
from capstone.x86 import X86_OP_MEM


def parse_methods(text: str, class_name: str):
    for line in text.splitlines():
        if "|" not in line or f"@{class_name}@" not in line:
            continue
        parts = [p.strip().strip("`") for p in line.split("|")]
        if len(parts) < 5:
            continue
        va_match = re.search(r"0x[0-9A-Fa-f]+", parts[3])
        size_match = re.search(r"0x[0-9A-Fa-f]+", parts[4])
        if not va_match or not size_match:
            continue
        yield parts[2], int(va_match.group(0), 16), int(size_match.group(0), 16)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("binary")
    ap.add_argument("class_name")
    ap.add_argument("output")
    ap.add_argument("--offsets", nargs="+", default=["0x58"])
    args = ap.parse_args()

    offsets = {int(x, 0) for x in args.offsets}
    pe = pefile.PE(args.binary, fast_load=False)
    image_base = pe.OPTIONAL_HEADER.ImageBase
    symbols = subprocess.run(
        [sys.executable, "tools/find_td32_class_procedures.py", args.binary, args.class_name],
        check=True, capture_output=True, text=True,
    ).stdout

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    out = [
        f"# {args.class_name} field-offset reference scan",
        "",
        f"- Binary: `{args.binary}`",
        f"- Offsets: {', '.join(hex(x) for x in sorted(offsets))}",
        "",
    ]
    total_methods = 0
    total_refs = 0

    for decorated, va, size in parse_methods(symbols, args.class_name):
        total_methods += 1
        rva = va - image_base
        try:
            raw = pe.get_offset_from_rva(rva)
        except pefile.PEFormatError:
            continue
        blob = pe.__data__[raw:raw + size]
        insns = list(md.disasm(blob, va))
        hits = []
        for i, insn in enumerate(insns):
            for op_index, op in enumerate(insn.operands):
                if op.type != X86_OP_MEM or op.mem.disp not in offsets:
                    continue
                access = op.access
                direction = "read/write" if (access & CS_AC_READ and access & CS_AC_WRITE) else "write" if access & CS_AC_WRITE else "read" if access & CS_AC_READ else "address/unknown"
                context = insns[max(0, i - 2):min(len(insns), i + 3)]
                rendered = " | ".join(f"{x.address:08X}: {x.mnemonic} {x.op_str}" for x in context)
                hits.append((insn.address, op.mem.disp, direction, rendered))
        if hits:
            out.append(f"## {decorated}")
            out.append(f"- Procedure: 0x{va:08X}, size 0x{size:X}")
            for address, offset, direction, rendered in hits:
                total_refs += 1
                out.append(f"- {direction} field +0x{offset:X} at 0x{address:08X}")
                out.append(f"  - {rendered}")
            out.append("")

    out.extend([
        "## Summary",
        f"- TD32 methods scanned: {total_methods}",
        f"- Field references found: {total_refs}",
        "",
    ])
    pathlib.Path(args.output).write_text("\n".join(out), encoding="utf-8")
    print(f"Scanned {total_methods} methods; found {total_refs} references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
