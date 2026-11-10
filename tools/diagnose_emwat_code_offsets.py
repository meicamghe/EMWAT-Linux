#!/usr/bin/env python3
"""Diagnose TD32 procedure address interpretations before trusting disassembly."""
import pathlib
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile
from analyze_emwat_td32 import find_td32, parse_td32


PATTERNS = [
    "TfrmSimpleImageEditor@CropImage",
    "TfrmSimpleImageEditor@ToggleCropMode",
    "TfrmSimpleImageEditor@btnRegisterClick",
    "TfrmSimpleImageEditor@doCommand",
    "TfrmSimpleImageEditor@pbImgViewerMouseDown",
    "TfrmSimpleImageEditor@pbImgViewerMouseMove",
    "TfrmSimpleImageEditor@pbImgViewerMouseUp",
    "TfrmSimpleImageEditor@ShowCropRectangle",
    "TfrmGScanPreview@doCommand",
    "TfrmGScanPreview@btnCropClick",
    "TfrmGScanPreview@btnHFlipClick",
    "TfrmGScanPreview@btnLRotateClick",
    "TfrmGScanPreview@btnRRotateClick",
    "TfrmGScanPreview@btnVFlipClick",
    "TfrmGScanPreview@uibtnRegisterClick",
    "TfrmGScanPreview@Save_Tiff_MultyPages",
    "TfrmGScanPreview@Scan",
    "TGearImgProc@Rotate90",
    "TGearImgProc@RotateLeft",
    "TGearImgProc@RotateRight",
    "TGearImgProc@FlipHorizontal",
    "TGearImgProc@FlipVertical",
    "TGearImgProc@SaveToFile",
    "TGearImgProc@ScanToFile",
]
TARGET_MODULES = {65, 67, 98}


def section_for_rva(pe, rva, size):
    for sec in pe.sections:
        start = sec.VirtualAddress
        end = start + max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if start <= rva and rva + size <= end:
            return sec
    return None


def section_for_raw(pe, raw, size):
    for sec in pe.sections:
        start = sec.PointerToRawData
        end = start + sec.SizeOfRawData
        if start <= raw and raw + size <= end:
            return sec
    return None


def section_name(sec):
    return sec.Name.rstrip(bytes([0])).decode("ascii", "replace")


def describe_candidate(blob, md, label, raw, size, preferred_va=None):
    if raw < 0 or raw + size > len(blob):
        return [f"### {label}", f"- Raw offset: {raw}", "- Out of file bounds", ""]
    data = blob[raw:raw + size]
    va = preferred_va if preferred_va is not None else 0x400000 + raw
    lines = [
        f"### {label}",
        f"- Raw file offset: 0x{raw:08X}",
        f"- First 32 bytes: {data[:32].hex(' ')}",
    ]
    insns = list(md.disasm(data, va))
    if not insns:
        lines.append("- Decode: no instructions")
    else:
        for ins in insns[:14]:
            lines.append(f"  - {ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
    lines.append("")
    return lines


def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-address-diagnostics.md")
    blob = src.read_bytes()
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, dir_off, _sig = hit
    _entries, names, modules, procedures = parse_td32(blob, base, end, dir_off)
    pe = pefile.PE(data=blob, fast_load=False)
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    lines = [
        "# EMWAT TD32 address-mapping diagnostics",
        "",
        f"- Input: {src}",
        f"- File size: {len(blob):,} bytes",
        f"- ImageBase: 0x{pe.OPTIONAL_HEADER.ImageBase:08X}",
        "",
        "## PE section mapping",
        "",
        "| Section | RVA | Virtual size | Raw pointer | Raw size | Characteristics |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for sec in pe.sections:
        lines.append(
            f"| {section_name(sec)} | 0x{sec.VirtualAddress:08X} | 0x{sec.Misc_VirtualSize:X} | "
            f"0x{sec.PointerToRawData:08X} | 0x{sec.SizeOfRawData:X} | 0x{sec.Characteristics:08X} |"
        )

    lines += [
        "",
        "## TD32 module and segment descriptors",
        "",
        "| Module index | Module name index | Module name | Segment | Flags | TD32 offset | Size | RVA mapping | Raw mapping |",
        "|---:|---:|---|---:|---:|---:|---:|---|---|",
    ]
    for module_id in sorted(TARGET_MODULES):
        if module_id not in modules:
            lines.append(f"| {module_id} | — | missing module | — | — | — | — | — | — |")
            continue
        module_name_idx, segments = modules[module_id]
        module_name = names[module_name_idx] if module_name_idx < len(names) else f"<name-index-{module_name_idx}>"
        for segno, flags, seg_offset, seg_size in segments:
            sec = section_for_rva(pe, seg_offset, max(1, seg_size))
            if sec:
                raw = pe.get_offset_from_rva(seg_offset)
                rva_desc = f"{section_name(sec)} @ 0x{seg_offset:08X}"
                raw_desc = f"0x{raw:08X}"
            else:
                rva_desc = "not in PE section"
                raw_desc = "—"
            raw_sec = section_for_raw(pe, seg_offset, max(1, seg_size))
            if raw_sec:
                raw_desc += f" ({section_name(raw_sec)} raw range)"
            lines.append(
                f"| {module_id} | {module_name_idx} | {module_name} | {segno} | 0x{flags:04X} | "
                f"0x{seg_offset:08X} | 0x{seg_size:X} | {rva_desc} | {raw_desc} |"
            )

    selected = [p for p in procedures if any(k.lower() in p["name"].lower() for k in PATTERNS)]
    lines += ["", f"## Procedure candidates ({len(selected)})", ""]
    for p in selected:
        module = modules.get(p["module"])
        seg = next((s for s in module[1] if s[0] == p["segment"]), None) if module else None
        lines += [f"## {p['name']}", ""]
        if not seg:
            lines += ["- No matching TD32 segment descriptor", ""]
            continue

        _segno, flags, seg_base, seg_size = seg
        proc = p["offset"]
        size = p["size"]
        module_name_idx = module[0]
        module_name = names[module_name_idx] if module_name_idx < len(names) else f"<name-index-{module_name_idx}>"
        lines += [
            f"- Module index: {p['module']} ({module_name}); segment: {p['segment']}; flags: 0x{flags:04X}",
            f"- Segment range: 0x{seg_base:08X}..0x{seg_base + seg_size:08X}",
            f"- Procedure offset: 0x{proc:08X}; size: 0x{size:X}",
            f"- Procedure within segment: {seg_base <= proc and proc + size <= seg_base + seg_size}",
        ]

        sec = section_for_rva(pe, proc, size)
        if sec:
            raw_rva = pe.get_offset_from_rva(proc)
            lines.append(f"- RVA interpretation: section {section_name(sec)}, raw 0x{raw_rva:08X}")
            lines += describe_candidate(
                blob, md, "Candidate A — TD32 offset treated as PE RVA",
                raw_rva, size, pe.OPTIONAL_HEADER.ImageBase + proc,
            )
        else:
            lines += ["- RVA interpretation: not contained in a PE section", ""]

        raw_sec = section_for_raw(pe, proc, size)
        if raw_sec:
            mapped_rva = raw_sec.VirtualAddress + (proc - raw_sec.PointerToRawData)
            mapped_va = pe.OPTIONAL_HEADER.ImageBase + mapped_rva
            lines.append(f"- Raw-offset mapping: section {section_name(raw_sec)}, RVA 0x{mapped_rva:08X}, VA 0x{mapped_va:08X}")
            lines.append(f"- Raw-offset section executable: {bool(raw_sec.Characteristics & 0x20000000)}")
        else:
            mapped_va = None
            lines.append("- Raw-offset mapping: not contained in PE raw section data")
        lines += describe_candidate(
            blob, md, "Candidate B — TD32 offset treated as raw file offset",
            proc, size, mapped_va,
        )

        relative = proc - seg_base
        lines += describe_candidate(
            blob, md, "Candidate C — segment-relative offset treated as raw file offset",
            relative, size,
        )

        if sec:
            raw_seg = pe.get_offset_from_rva(seg_base)
            lines += describe_candidate(
                blob, md, "Candidate D — segment-base raw offset plus relative offset",
                raw_seg + relative, size, pe.OPTIONAL_HEADER.ImageBase + proc,
            )

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}; diagnosed {len(selected)} procedures")


if __name__ == "__main__":
    main()
