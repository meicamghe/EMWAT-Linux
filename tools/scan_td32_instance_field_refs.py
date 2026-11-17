#!/usr/bin/env python3
"""Inventory accesses to a Delphi object-field offset inside TD32 class methods.

This is a candidate generator, not a proof that every matching base register is
Self. Use the emitted procedure names and instruction context to validate the
object pointer/data-flow before assigning a semantic meaning to a field.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const

from analyze_emwat_td32 import find_td32, parse_td32


def procedure_code(blob: bytes, pe: pefile.PE, modules: dict, proc: dict):
    """Return (VA, bytes) for a TD32 procedure if its range is file-backed."""
    if not (1 <= proc["segment"] <= len(pe.sections)):
        return None
    section = pe.sections[proc["segment"] - 1]
    module = modules.get(proc["module"])
    segment = (
        next((item for item in module[1] if item[0] == proc["segment"]), None)
        if module
        else None
    )
    if not segment:
        return None
    _, _, segment_base, segment_size = segment
    offset = proc["offset"]
    size = proc["size"]
    if not (segment_base <= offset and offset + size <= segment_base + segment_size):
        return None
    if offset + size > section.SizeOfRawData:
        return None
    raw = section.PointerToRawData + offset
    if raw + size > len(blob):
        return None
    va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress + offset
    return va, blob[raw:raw + size]


def access_kind(instruction) -> str:
    if instruction.mnemonic == "lea":
        return "address"
    if not instruction.operands:
        return "unknown"
    first = instruction.operands[0]
    if first.type == x86_const.X86_OP_MEM:
        if instruction.mnemonic in {"mov", "movss", "movsd", "movups", "movaps", "movdqu", "movdqa"}:
            return "write"
        if instruction.mnemonic in {
            "add", "adc", "sub", "sbb", "and", "or", "xor", "inc", "dec",
            "not", "neg", "shl", "shr", "sar", "rol", "ror", "xchg",
            "cmpxchg", "xadd", "bts", "btr", "btc",
        }:
            return "read/write"
        return "read/unknown"
    return "read"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("class_name", help="TD32 procedure-name prefix, e.g. TWordViwer")
    parser.add_argument("field_offset", type=lambda value: int(value, 0))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    blob = args.input.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    td32 = find_td32(blob)
    if not td32:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = td32
    _, _, modules, procedures = parse_td32(blob, base, end, directory)

    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    hits = []
    matched_procedures = 0
    for proc in procedures:
        name = proc.get("name", "")
        if not (name == args.class_name or name.startswith(args.class_name + ".")):
            continue
        code = procedure_code(blob, pe, modules, proc)
        if code is None:
            continue
        matched_procedures += 1
        start_va, procedure_bytes = code
        instructions = list(decoder.disasm(procedure_bytes, start_va))
        for index, instruction in enumerate(instructions):
            operands = [
                operand
                for operand in instruction.operands
                if operand.type == x86_const.X86_OP_MEM
                and operand.mem.disp == args.field_offset
            ]
            if not operands:
                continue
            memory = operands[0].mem
            base_name = instruction.reg_name(memory.base) if memory.base else "none"
            index_name = instruction.reg_name(memory.index) if memory.index else "none"
            hits.append(
                (
                    name,
                    instruction.address,
                    access_kind(instruction),
                    instruction.mnemonic,
                    instruction.op_str,
                    base_name,
                    index_name,
                )
            )

    lines = [
        f"# TD32 instance-field reference candidates: {args.class_name} +0x{args.field_offset:X}",
        "",
        f"- Input: `{args.input}`",
        f"- Class prefix: `{args.class_name}`",
        f"- Field displacement: `+0x{args.field_offset:X}`",
        f"- File-backed TD32 procedures scanned: {matched_procedures}",
        "- This is a displacement inventory only; a matching base register is not automatically proven to be Self.",
        "",
    ]
    if not hits:
        lines.append("- No matching memory operands found.")
    for name, va, access, mnemonic, op_str, base_name, index_name in sorted(hits, key=lambda item: item[1]):
        lines += [
            f"## {name} — `0x{va:08X}`",
            "",
            f"- Candidate access: `{access}`",
            f"- Base register: `{base_name}`; index register: `{index_name}`",
            "",
            "```asm",
            f"{va:08X}  {mnemonic:<8} {op_str}",
            "```",
            "",
        ]
    lines += [f"- Total matching instructions: {len(hits)}", ""]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {args.output}; procedures={matched_procedures}; field references={len(hits)}")


if __name__ == "__main__":
    main()
