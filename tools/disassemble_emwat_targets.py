#!/usr/bin/env python3
"""Disassemble Delphi methods using Borland TD32 module segment mappings."""
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
        "- Address mapping: PE RVA = TD32 segment base + procedure offset; procedure range validated within segment",
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
        proc_off = p["offset"]
        if proc_off + p["size"] > seg_size:
            lines += [
                f"- TD32 segment base RVA: 0x{seg_base:08X}",
                f"- TD32 segment size: 0x{seg_size:X}",
                f"- Procedure offset/size: 0x{proc_off:X}/0x{p['size']:X}",
                "- **Mapping rejected:** procedure range exceeds its TD32 segment.",
                "",
            ]
            continue

        rva = seg_base + proc_off
        try:
            raw = pe.get_offset_from_rva(rva)
        except Exception as exc:
            lines += [
                f"- TD32 segment base RVA: 0x{seg_base:08X}",
                f"- Procedure offset: 0x{proc_off:08X}",
                f"- Candidate RVA: 0x{rva:08X}",
                f"- **Mapping failed:** {exc}",
                "",
            ]
            continue

        code = blob[raw:raw + p["size"]]
        va = pe.OPTIONAL_HEADER.ImageBase + rva
        section = next(
            (s.Name.rstrip(b"\\0").decode("ascii", "replace")
             for s in pe.sections
             if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData)),
            "unknown",
        )
        lines += [
            f"- TD32 module index: {p['module']}",
            f"- TD32 segment: {p['segment']} (flags 0x{seg_flags:04X})",
            f"- TD32 segment base RVA: 0x{seg_base:08X}",
            f"- Procedure offset within segment: 0x{proc_off:08X}",
            f"- Candidate RVA: 0x{rva:08X}",
            f"- VA: 0x{va:08X}",
            f"- PE section: {section}",
            f"- Raw file offset: 0x{raw:08X}",
            f"- TD32 size: 0x{p['size']:X} ({p['size']} bytes)",
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
