#!/usr/bin/env python3
"""Trace a known PE virtual address through short x86 thunks and report its code."""
import pathlib
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_MEM, X86_OP_IMM

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
    if len(sys.argv) < 3:
        raise SystemExit("usage: trace_pe_target.py <pe-file> <VA> [output.md]")
    path = pathlib.Path(sys.argv[1])
    va = int(sys.argv[2], 0)
    out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/EmwatMethods-target-address-trace.md")
    pe = pefile.PE(str(path), fast_load=False)
    blob = path.read_bytes()
    imports = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        for imp in entry.imports:
            if imp.address:
                name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
                imports[imp.address] = f"{entry.dll.decode('ascii','replace')}!{name}"
    md = ["# EMWAT PE target-address trace", "", f"- Input: {path}", f"- Requested VA: `0x{va:08X}`", ""]
    md += ["## Thunk chain", ""]
    current = va
    seen = set()
    md_lines = []
    md_lines.append("## Disassembly")
    md_lines.append("")
    for depth in range(8):
        if current in seen:
            md.append(f"- Cycle detected at `0x{current:08X}`.")
            break
        seen.add(current)
        raw, sec = va_to_raw(pe, current)
        if raw is None:
            md.append(f"- `0x{current:08X}`: not mapped to file-backed PE section.")
            break
        secname = sec.Name.rstrip(bytes([0])).decode("ascii", "replace")
        md.append(f"- Hop {depth}: `0x{current:08X}`, raw `0x{raw:08X}`, section `{secname}`.")
        if current in imports:
            md.append(f"  - IAT import: **{imports[current]}**")
            break
        code = blob[raw:raw+48]
        insns = list(Cs(CS_ARCH_X86, CS_MODE_32).disasm(code, current))
        if not insns:
            md.append("  - No instruction decoded.")
            break
        for ins in insns[:10]:
            md_lines.append(f"`{ins.address:08X}`  {ins.mnemonic:<8} {ins.op_str}")
        first = insns[0]
        if first.mnemonic == "jmp" and first.operands:
            op = first.operands[0]
            if op.type == X86_OP_IMM:
                current = op.imm & 0xFFFFFFFF
                continue
            if op.type == X86_OP_MEM and op.mem.base == 0 and op.mem.index == 0:
                slot = op.mem.disp & 0xFFFFFFFF
                if slot in imports:
                    md.append(f"  - Indirect jump through IAT `0x{slot:08X}`: **{imports[slot]}**")
                    break
                slot_raw, _ = va_to_raw(pe, slot)
                if slot_raw is not None and slot_raw + 4 <= len(blob):
                    current = int.from_bytes(blob[slot_raw:slot_raw+4], "little")
                    md.append(f"  - Indirect jump slot `0x{slot:08X}` resolves to `0x{current:08X}`.")
                    continue
        md.append("  - No simple direct/absolute-indirect JMP thunk; stop following.")
        break
    md += ["", *md_lines, ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
