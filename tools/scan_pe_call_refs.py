#!/usr/bin/env python3
"""Find direct CALL references to a VA across all executable PE sections.

Unlike trace_td32_callers.py, this scan does not require TD32 procedure
boundaries and can therefore find call sites in unsymbolized code.
"""
import pathlib
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const


def main():
    if len(sys.argv) < 3:
        raise SystemExit(
            "usage: scan_pe_call_refs.py <pe-file> <target-va> [output.md] [context-instructions]"
        )
    src = pathlib.Path(sys.argv[1])
    target = int(sys.argv[2], 0) & 0xFFFFFFFF
    out = pathlib.Path(
        sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/PE-call-refs.md"
    )
    context_size = int(sys.argv[4], 0) if len(sys.argv) > 4 else 4

    pe = pefile.PE(data=src.read_bytes(), fast_load=False)
    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    rows = []

    for section in pe.sections:
        if not (section.Characteristics & 0x20000000):
            continue
        code = section.get_data()
        if not code:
            continue
        section_name = section.Name.rstrip(b"\0").decode("ascii", "replace")
        base_va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress
        instructions = list(decoder.disasm(code, base_va))
        for index, instruction in enumerate(instructions):
            if instruction.mnemonic != "call" or not instruction.operands:
                continue
            operand = instruction.operands[0]
            if operand.type != x86_const.X86_OP_IMM:
                continue
            if (operand.imm & 0xFFFFFFFF) != target:
                continue
            lo = max(0, index - context_size)
            hi = min(len(instructions), index + context_size + 1)
            context = "\n".join(
                f"  {item.address:08X}  {item.mnemonic:<8} {item.op_str}"
                for item in instructions[lo:hi]
            )
            rows.append((instruction.address, section_name, context))

    lines = [
        "# PE direct CALL reference scan",
        "",
        f"- Input: `{src}`",
        f"- Target VA: `0x{target:08X}`",
        "- Scans all executable PE sections; TD32 symbols are not required.",
        "- Only direct immediate CALL instructions are resolved; indirect/VMT calls are not.",
        "",
    ]
    if not rows:
        lines.append("- No direct CALL references found.")
    for call_va, section_name, context in sorted(rows):
        lines += [
            f"## Call at 0x{call_va:08X} ({section_name})",
            "",
            "```asm",
            context,
            "```",
            "",
        ]
    lines += [f"- Total direct CALL references: {len(rows)}", ""]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}; direct call references={len(rows)}")


if __name__ == "__main__":
    main()
