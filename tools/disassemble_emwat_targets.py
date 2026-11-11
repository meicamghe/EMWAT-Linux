#!/usr/bin/env python3
"""Disassemble Delphi methods with per-method TD32/PE address validation."""
import pathlib
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from analyze_emwat_td32 import find_td32, parse_td32

PATTERNS = [
"TfrmSimpleImageEditor@CropImage","TfrmSimpleImageEditor@ToggleCropMode",
"TfrmSimpleImageEditor@btnRegisterClick","TfrmSimpleImageEditor@doCommand",
"TfrmSimpleImageEditor@pbImgViewerMouseDown","TfrmSimpleImageEditor@pbImgViewerMouseMove",
"TfrmSimpleImageEditor@pbImgViewerMouseUp","TfrmSimpleImageEditor@ShowCropRectangle",
"TfrmGScanPreview@doCommand","TfrmGScanPreview@btnCropClick",
"TfrmGScanPreview@btnHFlipClick","TfrmGScanPreview@btnLRotateClick",
"TfrmGScanPreview@btnRRotateClick","TfrmGScanPreview@btnVFlipClick",
"TfrmGScanPreview@uibtnRegisterClick","TfrmGScanPreview@Save_Tiff_MultyPages",
"TfrmGScanPreview@Scan","TGearImgProc@Rotate90","TGearImgProc@RotateLeft",
"TGearImgProc@RotateRight","TGearImgProc@FlipHorizontal",
"TGearImgProc@FlipVertical","TGearImgProc@SaveToFile","TGearImgProc@ScanToFile"]
COMMON = set("mov push pop call ret retn jmp je jne jz jnz ja jae jb jbe jg jge jl jle cmp test lea add sub xor and or inc dec imul idiv shl shr sar movzx movsx setne sete nop leave cdq neg not xchg".split())
BAD = set("int int1 int3 hlt arpl bound insb insd outsb outsd in out icebp ud2".split())

def section_rva(pe, rva, size):
    for s in pe.sections:
        lo=s.VirtualAddress; hi=lo+max(s.Misc_VirtualSize,s.SizeOfRawData)
        raw=s.PointerToRawData+rva-lo
        if lo <= rva and rva+size <= hi and raw+size <= s.PointerToRawData+s.SizeOfRawData:
            return s,raw
    return None,None

def section_raw(pe, raw, size):
    for s in pe.sections:
        lo=s.PointerToRawData; hi=lo+s.SizeOfRawData
        if lo <= raw and raw+size <= hi:
            return s,s.VirtualAddress+raw-lo
    return None,None

def score(data, va):
    # Decode strictly from the symbol address; skipping bytes can hide a bad mapping.
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    ins=list(md.disasm(data,va))
    if not ins: return None,[]
    covered=sum(x.size for x in ins)
    first=ins[:min(6,len(ins))]
    common=sum(x.mnemonic in COMMON for x in first)
    bad=sum(x.mnemonic in BAD for x in first)
    printable=sum(32<=b<127 for b in data)/max(1,len(data))
    ratio=covered/max(1,len(data))
    plausible=(common>=min(2,len(first)) and bad<=2 and printable<0.35 and ratio>0.35)
    val=ratio*40+(common/max(1,len(first)))*40-bad*25-printable*60
    return (val if plausible else None),ins

