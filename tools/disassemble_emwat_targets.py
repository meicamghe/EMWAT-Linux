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
    best=-1e9; best_ins=[]
    for skip in range(min(12,len(data))):
        md=Cs(CS_ARCH_X86,CS_MODE_32)
        ins=list(md.disasm(data[skip:],va+skip))
        if not ins: continue
        covered=sum(x.size for x in ins)
        common=sum(x.mnemonic in COMMON for x in ins)
        bad=sum(x.mnemonic in BAD for x in ins)
        printable=sum(32<=b<127 for b in data)/max(1,len(data))
        val=covered*.25+common*2-bad*5-printable*25
        if ins[0].mnemonic in {"push","mov","sub","jmp","call","pop"}: val+=3
        if val>best: best,best_ins=val,ins
    return best,best_ins

def candidate(blob,pe,p,mode,segbase,segend):
    if mode=="RVA":
        rva=p["offset"]; sec,raw=section_rva(pe,rva,p["size"])
    else:
        raw=p["offset"]; sec,rva=section_raw(pe,raw,p["size"])
    if sec is None or not (sec.Characteristics & 0x20000000): return None
    if not (segbase<=rva and rva+p["size"]<=segend): return None
    data=blob[raw:raw+p["size"]]
    sc,ins=score(data,pe.OPTIONAL_HEADER.ImageBase+rva)
    return {"mode":mode,"raw":raw,"rva":rva,"sec":sec,"score":sc,"ins":ins}

def main():
    src=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-target-disassembly.md")
    blob=src.read_bytes(); hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,_,modules,procedures=parse_td32(blob,base,end,directory)
    pe=pefile.PE(data=blob,fast_load=False)
    selected=[p for p in procedures if any(k.lower() in p["name"].lower() for k in PATTERNS)]
    lines=["# EMWAT target method disassembly","",f"- Input: {src}",f"- TD32 procedure records: {len(procedures):,}",f"- Matched methods: {len(selected)}","- Architecture: x86 / 32-bit","- Address mapping: per-method candidate validation against executable PE sections, TD32 segment RVA bounds, and instruction plausibility.","- No global raw-offset/RVA assumption is made.",""]
    mapped=0
    for p in selected:
        mod=modules.get(p["module"]); seg=next((s for s in mod[1] if s[0]==p["segment"]),None) if mod else None
        lines += [f"## {p['name']}",""]
        if not seg:
            lines += ["- Mapping unavailable: matching TD32 segment descriptor not found.",""]; continue
        _,flags,sbase,ssize=seg; send=sbase+ssize
        cs=[c for mode in ("RVA","RAW") if (c:=candidate(blob,pe,p,mode,sbase,send)) is not None]
        if not cs:
            lines += [f"- Module/segment: {p['module']}/{p['segment']} (flags 0x{flags:04X})",f"- Segment RVA range: 0x{sbase:08X}..0x{send:08X}",f"- Procedure offset/size: 0x{p['offset']:08X}/0x{p['size']:X}","- Mapping unresolved: no candidate fits an executable section and the TD32 segment range.",""]; continue
        cs.sort(key=lambda c:c["score"],reverse=True); c=cs[0]; mapped+=1
        conf="high" if len(cs)==1 or c["score"]-cs[1]["score"]>=8 else "tentative"
        secname=c["sec"].Name.rstrip(bytes([0])).decode("ascii","replace")
        lines += [f"- Module/segment: {p['module']}/{p['segment']} (flags 0x{flags:04X})",f"- Segment RVA range: 0x{sbase:08X}..0x{send:08X}",f"- Procedure offset/size: 0x{p['offset']:08X}/0x{p['size']:X}",f"- Selected interpretation: **{c['mode']}** ({conf}; score {c['score']:.1f})",f"- Mapped RVA/VA: 0x{c['rva']:08X} / 0x{pe.OPTIONAL_HEADER.ImageBase+c['rva']:08X}",f"- Raw file offset: 0x{c['raw']:08X}; PE section: {secname}"]
        for x in cs: lines.append(f"- Candidate {x['mode']}: RVA 0x{x['rva']:08X}, raw 0x{x['raw']:08X}, score {x['score']:.1f}")
        lines += ["","\x60\x60\x60asm"]
        for x in c["ins"]: lines.append(f"{x.address:08X}  {x.mnemonic:<8} {x.op_str}")
        lines += ["\x60\x60\x60",""]
    lines += ["## Validation summary","",f"- Methods mapped to an executable candidate: {mapped}/{len(selected)}",""]
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {out}; matched {len(selected)}; mapped {mapped}")

if __name__=="__main__": main()
