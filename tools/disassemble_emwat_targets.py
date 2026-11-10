#!/usr/bin/env python3
"""Disassemble Delphi methods whose ranges are recorded in Borland TD32."""
import pathlib, sys
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
import pefile
from analyze_emwat_td32 import find_td32, parse_td32

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-target-disassembly.md")
    blob=src.read_bytes()
    hit=find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base,end,dir_off,sig=hit
    entries,names,modules,procedures=parse_td32(blob,base,end,dir_off)
    pe=pefile.PE(data=blob,fast_load=False)
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    md.detail=False
    patterns=[
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
      "TGearImgProc@ScanToFile"
    ]
    selected=[p for p in procedures if any(k.lower() in p["name"].lower() for k in patterns)]
    lines=["# EMWAT target method disassembly","",f"- Input: {src}","- TD32 procedure records: {:,}".format(len(procedures)),f"- Matched methods: {len(selected)}","- Architecture: x86 / 32-bit",""]
    for p in selected:
      rva=p["offset"]
      try: raw=pe.get_offset_from_rva(rva)
      except Exception:
        lines += [f"## {p['name']}","","Could not map RVA 0x{rva:X} to a PE file offset.",""]
        continue
      code=blob[raw:raw+p["size"]]
      va=pe.OPTIONAL_HEADER.ImageBase+rva
      lines += [f"## {p['name']}","",f"- RVA: 0x{rva:08X}",f"- VA: 0x{va:08X}",f"- Raw file offset: 0x{raw:08X}",f"- TD32 size: 0x{p['size']:X} ({p['size']} bytes)","","```asm"]
      insns=list(md.disasm(code,va))
      for ins in insns:
        lines.append(f"{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
      if not insns: lines.append("; no instructions decoded")
      lines += ["```",""]
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {out}; matched {len(selected)} methods")

if __name__=="__main__": main()
