#!/usr/bin/env python3
"""Decode TD32 procedures once and emit procedure/caller reports for many VAs."""
from __future__ import annotations

import pathlib
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const

from analyze_emwat_td32 import find_td32, parse_td32


def main() -> None:
    if len(sys.argv) < 4:
        raise SystemExit(
            "usage: trace_td32_batch.py <pe-file> <output-dir> <target-va> [target-va ...]"
        )

    source = pathlib.Path(sys.argv[1])
    output_dir = pathlib.Path(sys.argv[2])
    targets = [int(value, 0) & 0xFFFFFFFF for value in sys.argv[3:]]
    blob = source.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")

    base, end, directory, _ = hit
    names, modules, procedures = parse_td32(blob, base, end, directory)[1:]
    image_base = pe.OPTIONAL_HEADER.ImageBase

    decoder = Cs(CS_ARCH_X86, CS_MODE_32)
    decoder.detail = True
    decoded_procedures = []
    callers: dict[int, list[tuple[str, int, str]]] = {target: [] for target in targets}

    for proc in procedures:
        segment_index = proc["segment"]
        if not (1 <= segment_index <= len(pe.sections)):
            continue
        section = pe.sections[segment_index - 1]
        module = modules.get(proc["module"])
        segment = (
            next((item for item in module[1] if item[0] == segment_index), None)
            if module else None
        )
        if not segment:
            continue
        _, _, segment_base, segment_size = segment
        if not (
            segment_base <= proc["offset"]
            and proc["offset"] + proc["size"] <= segment_base + segment_size
        ):
            continue
        if proc["offset"] + proc["size"] > section.SizeOfRawData:
            continue

        raw_offset = section.PointerToRawData + proc["offset"]
        start_va = image_base + section.VirtualAddress + proc["offset"]
        code = blob[raw_offset:raw_offset + proc["size"]]
        instructions = list(decoder.disasm(code, start_va))
        module_name_index = module[0] if module else -1
        module_name = (
            names[module_name_index]
            if 0 <= module_name_index < len(names)
            else str(proc["module"])
        )
        decoded_procedures.append(
            (proc, section, start_va, raw_offset, code, instructions, module_name)
        )

        for index, instruction in enumerate(instructions):
            if instruction.mnemonic != "call" or not instruction.operands:
                continue
            operand = instruction.operands[0]
            if operand.type != x86_const.X86_OP_IMM:
                continue
            target = operand.imm & 0xFFFFFFFF
            if target not in callers:
                continue
            lo = max(0, index - 4)
            hi = min(len(instructions), index + 5)
            context = "\n".join(
                f"  {item.address:08X}  {item.mnemonic:<8} {item.op_str}"
                for item in instructions[lo:hi]
            )
            callers[target].append((proc["name"], instruction.address, context))

    output_dir.mkdir(parents=True, exist_ok=True)
    for target in targets:
        matching = [
            item for item in decoded_procedures
            if item[2] <= target < item[2] + item[0]["size"]
        ]
        lines = [
            "# Complete TD32 procedure trace",
            "",
            f"- Input: {source}",
            f"- Requested VA: 0x{target:08X}",
            "",
        ]
        if not matching:
            lines.append("- No TD32 procedure range contains the requested VA.")
        for proc, section, start_va, raw_offset, code, instructions, module_name in sorted(
            matching, key=lambda item: item[2]
        ):
            lines += [
                f"## {proc['name']}",
                "",
                f"- Module: {module_name}",
                f"- Segment: {proc['segment']}",
                f"- Procedure VA range: 0x{start_va:08X}–0x{start_va + proc['size'] - 1:08X}",
                f"- Procedure size: 0x{proc['size']:X} ({proc['size']} bytes)",
                f"- PE section: {section.Name.rstrip(bytes([0])).decode('ascii', errors='replace')}",
                f"- File offset: 0x{raw_offset:08X}",
                f"- Requested VA offset: +0x{target - start_va:X}",
                "",
                "```asm",
            ]
            decoded_bytes = sum(item.size for item in instructions)
            lines.append(
                f"; Decoded {decoded_bytes}/{len(code)} procedure bytes ({len(instructions)} instructions)"
            )
            for instruction in instructions:
                marker = "  <-- requested VA" if instruction.address == target else ""
                lines.append(
                    f"{instruction.address:08X}  {instruction.mnemonic:<8} {instruction.op_str}{marker}"
                )
            lines += ["```", ""]

        procedure_path = output_dir / f"{target:08X}-td32.md"
        procedure_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        rows = sorted(callers[target], key=lambda item: item[1])
        caller_lines = [
            "# Direct TD32 call-site scan",
            "",
            f"- Target VA: 0x{target:08X}",
            "- Only direct immediate CALL instructions inside TD32-bounded procedures are listed.",
            "- Indirect/VMT dispatches are not resolved by this scan.",
            "",
        ]
        if not rows:
            caller_lines.append("- No direct CALL xrefs found.")
        for procedure_name, call_va, context in rows:
            caller_lines += [
                f"## {procedure_name} — call at 0x{call_va:08X}",
                "",
                "```asm",
                context,
                "```",
                "",
            ]
        caller_lines += [f"- Total direct callsites: {len(rows)}", ""]
        caller_path = output_dir / f"{target:08X}-callers.md"
        caller_path.write_text("\n".join(caller_lines), encoding="utf-8")

        print(
            f"0x{target:08X}: procedures={len(matching)}, callers={len(rows)} "
            f"-> {procedure_path.name}, {caller_path.name}"
        )


if __name__ == "__main__":
    main()
