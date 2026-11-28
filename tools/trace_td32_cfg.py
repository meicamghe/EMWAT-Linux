#!/usr/bin/env python3
"""Control-flow-aware disassembly of one TD32 procedure, skipping inline data."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

import pefile
from capstone import (
    Cs,
    CS_ARCH_X86,
    CS_MODE_32,
    CS_GRP_CALL,
    CS_GRP_JUMP,
    CS_GRP_RET,
)
from capstone.x86 import X86_OP_IMM

from analyze_emwat_td32 import find_td32, parse_td32


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("target_va", type=lambda value: int(value, 0))
    parser.add_argument("output", type=Path)
    parser.add_argument("--max-instructions", type=int, default=30000)
    args = parser.parse_args()

    blob = args.input.read_bytes()
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 stream not found")
    base, end, directory_offset, _signature = hit
    _entries, names, _modules, procedures = parse_td32(blob, base, end, directory_offset)
    pe = pefile.PE(data=blob, fast_load=True)
    image_base = int(pe.OPTIONAL_HEADER.ImageBase)

    matches = []
    for procedure in procedures:
        segment_id = int(procedure.get("segment", 0))
        if segment_id < 1 or segment_id > len(pe.sections):
            continue
        section = pe.sections[segment_id - 1]
        start = image_base + int(section.VirtualAddress) + int(procedure.get("offset", -1))
        size = int(procedure.get("size", 0))
        if size > 0 and start <= args.target_va < start + size:
            matches.append((size, procedure, section, start))
    if not matches:
        raise SystemExit(f"No TD32 procedure contains 0x{args.target_va:08X}")
    _size, procedure, section, start_va = min(matches, key=lambda item: item[0])

    procedure_size = int(procedure["size"])
    raw_offset = int(section.PointerToRawData) + int(procedure["offset"])
    code = blob[raw_offset : raw_offset + procedure_size]
    end_va = start_va + procedure_size
    module_name = "<unknown>"
    module_id = int(procedure.get("module", -1))
    if 0 <= module_id < len(names):
        module_name = str(names[module_id])
    procedure_name = str(procedure.get("name", "<unnamed>"))

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    md.detail = True
    pending = [start_va]
    queued = {start_va}
    visited: set[int] = set()
    decoded = {}
    invalid_paths: set[int] = set()
    branch_edges: set[tuple[int, int, str]] = set()
    direct_calls: set[tuple[int, int]] = set()
    indirect_branches: set[int] = set()

    while pending and len(decoded) < args.max_instructions:
        block_start = pending.pop()
        pc = block_start
        while start_va <= pc < end_va and pc not in visited and len(decoded) < args.max_instructions:
            offset = pc - start_va
            if offset < 0 or offset >= len(code):
                invalid_paths.add(pc)
                break
            insns = list(md.disasm(code[offset:], pc, count=1))
            if not insns:
                invalid_paths.add(pc)
                break
            insn = insns[0]
            decoded[pc] = insn
            visited.add(pc)
            next_pc = pc + insn.size

            operand_target = None
            if insn.operands and insn.operands[0].type == X86_OP_IMM:
                operand_target = int(insn.operands[0].imm)

            if insn.group(CS_GRP_CALL):
                if operand_target is not None:
                    direct_calls.add((pc, operand_target))
                    if start_va <= operand_target < end_va and operand_target not in queued:
                        pending.append(operand_target)
                        queued.add(operand_target)
                pc = next_pc
                continue

            if insn.group(CS_GRP_RET) or insn.mnemonic in ("ret", "retf", "iret", "iretd"):
                break

            if insn.group(CS_GRP_JUMP):
                if operand_target is not None:
                    branch_edges.add((pc, operand_target, insn.mnemonic))
                    if start_va <= operand_target < end_va and operand_target not in queued:
                        pending.append(operand_target)
                        queued.add(operand_target)
                else:
                    indirect_branches.add(pc)
                if insn.mnemonic not in ("jmp", "ljmp") and next_pc < end_va and next_pc not in queued:
                    pending.append(next_pc)
                    queued.add(next_pc)
                break

            if insn.mnemonic in ("ud2", "hlt", "int3"):
                break
            pc = next_pc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# CFG trace — {procedure_name}",
        "",
        f"- Requested VA: `0x{args.target_va:08X}`",
        f"- Procedure range: `0x{start_va:08X}–0x{end_va:08X}` (`0x{procedure_size:X}` bytes)",
        f"- TD32 module: `{module_name}`",
        f"- Reachable instructions decoded: {len(decoded)}",
        f"- Bytes represented by reachable instructions: {sum(insn.size for insn in decoded.values())}",
        f"- Bytes not reached by this CFG walk: {procedure_size - sum(insn.size for insn in decoded.values())}",
        f"- Invalid/unmapped paths: {len(invalid_paths)}",
        f"- Direct calls: {len(direct_calls)}",
        f"- Indirect branch sites: {len(indirect_branches)}",
        "",
        "This is a control-flow walk from the procedure entry. Unreachable inline data is intentionally not linearly disassembled as code.",
        "",
        "## Branch edges",
        "",
    ]
    for source, target, mnemonic in sorted(branch_edges):
        lines.append(f"- `0x{source:08X}` — {mnemonic} → `0x{target:08X}`")
    lines.extend(["", "## Direct calls", ""])
    for source, target in sorted(direct_calls):
        lines.append(f"- `0x{source:08X}` → `0x{target:08X}`")
    lines.extend(["", "## Instructions", "", "```asm"])
    for address, insn in sorted(decoded.items()):
        lines.append(f"{address:08X}  {insn.mnemonic:<9} {insn.op_str}")
    lines.extend(["```", ""])
    args.output.write_text("\n".join(lines), encoding="utf-8")
    print(
        f"{procedure_name}: {len(decoded)} reachable instructions, "
        f"{len(direct_calls)} calls, {len(branch_edges)} branch edges"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
