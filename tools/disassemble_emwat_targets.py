#!/usr/bin/env python3
"""Disassemble Delphi methods using TD32 file offsets mapped through PE sections."""
import pathlib
import sys

from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile
from analyze_emwat_td32 import find_td32, parse_td32


def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-target-disassembly.md")
    blob = src.read_bytes()
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")

    base, end, dir_off, _sig = hit
    _entries, _names, modules, procedures = parse_td32(blob, base, end, dir_off)
    pe = pefile.PE(data=blob, fast_load=False)
    md = Cs(CS_ARCH_X86, CS_MODE_32)

    patterns = [
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
    selected = [p for p in procedures if any(k.lower() in p["name"].lower() for k in patterns)]
    lines = [
        "# EMWAT target method disassembly",
        "",
        f"- Input: {src}",
        f"- TD32 procedure records: {len(procedures):,}",
        f"- Matched methods: {len(selected)}",
        "- Architecture: x86 / 32-bit",
        "- Address mapping: TD32 procedure offset is an absolute PE RVA; validated against [segment base, segment base + segment size)",
        "- Raw file offsets are obtained with pefile.get_offset_from_rva(RVA)",
        "",
    ]

    for p in selected:
        module = modules.get(p["module"])
        seg_info = next((s for s in module[1] if s[0] == p["segment"]), None) if module else None
        lines += [f"## {p['name']}", ""]
        if seg_info is None:
            lines += [
                f"- TD32 module index: {p['module']}",
                f"- TD32 segment: {p['segment']}",
                "- **Mapping unavailable:** no matching segment descriptor in this module record.",
                "",
            ]
            continue

        _seg, seg_flags, seg_base, seg_size = seg_info
        rva = p["offset"]
        proc_size = p["size"]
        seg_end = seg_base + seg_size
        if rva < seg_base or rva + proc_size > seg_end:
            lines += [
                f"- TD32 segment base RVA: 0x{seg_base:08X}",
                f"- TD32 segment end RVA: 0x{seg_end:08X}",
                f"- Procedure RVA/size: 0x{rva:08X}/0x{proc_size:X}",
                "- **Mapping rejected:** procedure range is outside its TD32 segment.",
                "",
            ]
            continue

        # TD32 segment/procedure offsets in this BPL are file-relative offsets.
        # Resolve them through the PE section table; they are not RVAs.
        raw = rva
        section = next(
            (s for s in pe.sections
             if s.PointerToRawData <= raw
             and raw + proc_size <= s.PointerToRawData + s.SizeOfRawData),
            None,
        )
        if section is None:
            lines += [
                f"- TD32 file offset: 0x{raw:08X}",
                "- **Mapping rejected:** procedure range is not contained in PE raw section data.",
                "",
            ]
            continue
        if not (section.Characteristics & 0x20000000):
            lines += [
                f"- TD32 file offset: 0x{raw:08X}",
                f"- PE section: {section.Name.rstrip(bytes([0])).decode('ascii', 'replace')}",
                "- **Mapping rejected:** containing PE section is not marked executable.",
                "",
            ]
            continue
        rva = section.VirtualAddress + (raw - section.PointerToRawData)
        if raw + proc_size > len(blob):
            lines += [
                f"- TD32 file offset: 0x{raw:08X}",
                "- **Mapping rejected:** procedure bytes extend beyond the file.",
                "",
            ]
            continue

        va = pe.OPTIONAL_HEADER.ImageBase + rva
        section_name = section.Name.rstrip(bytes([0])).decode("ascii", "replace")
        code = blob[raw:raw + proc_size]
        va = pe.OPTIONAL_HEADER.ImageBase + rva
        section_name = section.Name.rstrip(bytes([0])).decode("ascii", "replace")
        lines += [
            f"- TD32 module index: {p['module']}",
            f"- TD32 segment: {p['segment']} (flags 0x{seg_flags:04X})",
            f"- TD32 segment file-offset range: 0x{seg_base:08X}..0x{seg_end:08X}",
            f"- TD32 procedure file offset: 0x{raw:08X}",
            f"- Mapped RVA: 0x{rva:08X}",
            f"- VA: 0x{va:08X}",
            f"- PE section: {section_name}",
            f"- Raw file offset: 0x{raw:08X}",
            f"- TD32 size: 0x{proc_size:X} ({proc_size} bytes)",
            "",
            "```asm",
        ]
        insns = list(md.disasm(code, va))
        for ins in insns:
            lines.append(f"{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
        if not insns:
            lines.append("; no instructions decoded")
        lines += ["```", ""]

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}; matched {len(selected)} methods")


if __name__ == "__main__":
    main()
