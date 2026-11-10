#!/usr/bin/env python3
"""Inspect TD32 module/segment descriptors and address candidates for target methods."""
import pathlib
import sys

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from analyze_emwat_td32 import find_td32, parse_td32

TARGETS = (
    "TGearImgProc@", "TfrmSimpleImageEditor@", "TfrmGScanPreview@",
)


def decode_name(names, index):
    return names[index] if 0 <= index < len(names) else f"<name-index-{index}>"


def section_raw(pe, rva, size):
    for sec in pe.sections:
        start = sec.VirtualAddress
        end = start + max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if start <= rva and rva + size <= end:
            raw = sec.PointerToRawData + rva - start
            if raw + size <= sec.PointerToRawData + sec.SizeOfRawData:
                return sec, raw
    return None, None


def section_for_raw(pe, raw, size):
    for sec in pe.sections:
        start = sec.PointerToRawData
        if start <= raw and raw + size <= start + sec.SizeOfRawData:
            return sec
    return None


def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-module-map.md")
    blob = src.read_bytes()
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory = hit[:3]
    _, names, modules, procedures = parse_td32(blob, base, end, directory)
    pe = pefile.PE(data=blob, fast_load=False)
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    selected = [p for p in procedures if any(t.lower() in p["name"].lower() for t in TARGETS)]
    module_ids = sorted({p["module"] for p in selected})
    lines = [
        "# EMWAT TD32 module and segment mapping inspection", "",
        f"- Input: {src}", f"- Target procedure records: {len(selected)}",
        f"- Relevant module indexes: {', '.join(map(str, module_ids))}", "",
        "## Module descriptors", "",
    ]
    for mid in module_ids:
        module = modules.get(mid)
        if not module:
            lines += [f"### Module {mid}", "- Missing module descriptor", ""]
            continue
        name_idx, segments = module
        lines += [
            f"### Module {mid}: {decode_name(names, name_idx)}",
            f"- Module name index: {name_idx}",
            f"- Segment descriptors: {len(segments)}",
            "",
            "| Segment | Flags | TD32 offset | Size | End |",
            "|---:|---:|---:|---:|---:|",
        ]
        for seg, flags, offset, size in segments:
            lines.append(f"| {seg} | 0x{flags:04X} | 0x{offset:08X} | 0x{size:X} | 0x{offset + size:08X} |")
        lines.append("")

    lines += ["## Procedure address candidates", ""]
    for p in selected:
        module = modules.get(p["module"])
        seg = next((s for s in module[1] if s[0] == p["segment"]), None) if module else None
        lines += [
            f"### {p['name']}", "",
            f"- Module: {p['module']} ({decode_name(names, module[0]) if module else 'missing'})",
            f"- Segment: {p['segment']}; procedure offset: 0x{p['offset']:08X}; size: 0x{p['size']:X}",
        ]
        if seg:
            _, flags, segbase, segsize = seg
            lines.append(f"- Segment flags/range: 0x{flags:04X}; 0x{segbase:08X}..0x{segbase + segsize:08X}")
        candidates = []
        sec, raw = section_raw(pe, p["offset"], p["size"])
        if sec is not None:
            candidates.append(("offset-as-RVA", raw, pe.OPTIONAL_HEADER.ImageBase + p["offset"], sec))
        sec = section_for_raw(pe, p["offset"], p["size"])
        if sec is not None:
            rva = sec.VirtualAddress + p["offset"] - sec.PointerToRawData
            candidates.append(("offset-as-raw", p["offset"], pe.OPTIONAL_HEADER.ImageBase + rva, sec))
        if not candidates:
            lines += ["- No complete candidate fits a PE section.", ""]
            continue
        for label, raw, va, sec in candidates:
            section_name = sec.Name.rstrip(b"\\0").decode("ascii", "replace")
            data = blob[raw:raw + min(p["size"], 64)]
            insns = list(md.disasm(data, va))
            lines += [
                f"- {label}: raw=0x{raw:08X}, VA=0x{va:08X}, section={section_name}",
                f"  - Bytes: {data[:24].hex(' ')}",
                "  - Disassembly:",
            ]
            if insns:
                for ins in insns[:8]:
                    lines.append(f"    - {ins.address:08X} {ins.mnemonic:<8} {ins.op_str}")
            else:
                lines.append("    - no instruction decoded at candidate start")
        lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}; inspected {len(selected)} procedures across {len(module_ids)} modules")


if __name__ == "__main__":
    main()
