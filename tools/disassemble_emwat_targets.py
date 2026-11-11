#!/usr/bin/env python3
"""Disassemble Delphi methods with strict per-method TD32/PE address validation."""
import pathlib, sys
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
"TGearImgProc@FlipVertical","TGearImgProc@SaveToFile","TGearImgProc@ScanToFile",
"TGearImgProc@$bctr","TGearImgProc@Crop","TGearImgProc@Flip",
"TGearImgProc@SetEditorForm","TGearImgProc@ShowEditor",
"TGearImgProc@NotifyEditor","TGearImgProc@LoadPage",
"TGearImgProc@PaintCanvas","TGearImgProc@CheckErrors",
"TGearImgProc@CheckOutputParameter"]
COMMON=set("mov push pop call ret retn jmp je jne jz jnz ja jae jb jbe jg jge jl jle cmp test lea add sub xor and or inc dec imul idiv shl shr sar movzx movsx setne sete nop leave cdq neg not xchg".split())
BAD=set("int int1 int3 hlt arpl bound insb insd outsb outsd in out icebp ud2".split())

def section_rva(pe,rva,size):
    for s in pe.sections:
        lo=s.VirtualAddress; hi=lo+max(s.Misc_VirtualSize,s.SizeOfRawData)
        raw=s.PointerToRawData+rva-lo
        if lo<=rva and rva+size<=hi and raw+size<=s.PointerToRawData+s.SizeOfRawData: return s,raw
    return None,None

def section_raw(pe,raw,size):
    for s in pe.sections:
        lo=s.PointerToRawData; hi=lo+s.SizeOfRawData
        if lo<=raw and raw+size<=hi: return s,s.VirtualAddress+raw-lo
    return None,None

def score(data,va):
    # Judge only the entry bytes: later exception tables or embedded constants
    # can make a valid Delphi method look noisy when decoded linearly.
    head=data[:min(32,len(data))]
    entry_ins=list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(head,va))
    if not entry_ins:
        return None,[]
    first=entry_ins[:min(8,len(entry_ins))]
    common=sum(x.mnemonic in COMMON for x in first)
    bad=sum(x.mnemonic in BAD for x in first)
    covered=sum(x.size for x in entry_ins)/max(1,len(head))
    entry_core=any(x.mnemonic in {"mov","push","call","cmp","test","lea","sub","xor"} for x in first[:4])
    plausible=(common>=min(3,len(first)) and entry_core and first[0].mnemonic not in {"popal","add","or","inc","dec"} and bad==0 and covered>0.55)
    value=covered*40+(common/max(1,len(first)))*50-bad*30
    # Return a full-length decode for the report; the score uses only the entry.
    full_ins=list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(data,va))
    return (value if plausible else None),full_ins

def candidate(blob,pe,p,segno,segbase,segend):
    # TD32 Segment is a 1-based logical segment index. In this PE it maps
    # to the corresponding PE section; procedure Offset is relative to it.
    if not (1 <= segno <= len(pe.sections)):
        return None
    sec=pe.sections[segno-1]
    if not (sec.Characteristics & 0x20000000):
        return None
    if not (segbase <= p["offset"] and p["offset"]+p["size"] <= segend):
        return None
    if p["offset"]+p["size"] > sec.SizeOfRawData:
        return None
    raw=sec.PointerToRawData+p["offset"]
    rva=sec.VirtualAddress+p["offset"]
    if raw+p["size"] > len(blob):
        return None
    data=blob[raw:raw+p["size"]]
    value,ins=score(data,pe.OPTIONAL_HEADER.ImageBase+rva)
    return {"mode":"segment-relative","raw":raw,"rva":rva,"section":sec,"score":value,"insns":ins,"data":data}

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-target-disassembly.md")
    blob=src.read_bytes(); hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,_,modules,procedures=parse_td32(blob,base,end,directory)
    pe=pefile.PE(data=blob,fast_load=False)
    selected=[p for p in procedures if any(k.lower() in p["name"].lower() for k in PATTERNS)]
    lines=["# EMWAT target method disassembly","",f"- Input: {src}",f"- TD32 procedure records: {len(procedures):,}",f"- Matched methods: {len(selected)}","- Architecture: x86 / 32-bit","- Address mapping: TD32 segment-index to PE-section mapping, segment-relative procedure offsets, and instruction plausibility.","- A method is left unresolved if its bytes do not decode plausibly from the symbol address.",""]
    mapped=0
    for p in selected:
        mod=modules.get(p["module"]); seg=next((s for s in mod[1] if s[0]==p["segment"]),None) if mod else None
        lines += [f"## {p['name']}",""]
        if not seg:
            lines += ["- Mapping unavailable: matching TD32 segment descriptor not found.",""]; continue
        _,flags,sbase,ssize=seg; send=sbase+ssize
        raw_candidate=candidate(blob,pe,p,p["segment"],sbase,send)
        cs=[c for c in [raw_candidate] if c is not None and c["score"] is not None]
        if not cs:
            lines += [
                f"- Module/segment: {p['module']}/{p['segment']} (flags 0x{flags:04X})",
                f"- Segment RVA range: 0x{sbase:08X}..0x{send:08X}",
                f"- Procedure offset/size: 0x{p['offset']:08X}/0x{p['size']:X}",
                "- **Unresolved by instruction-quality filter.**"
            ]
            if raw_candidate:
                secname=raw_candidate["section"].Name.rstrip(bytes([0])).decode("ascii","replace")
                lines += [
                    f"- Segment-relative candidate: RVA 0x{raw_candidate['rva']:08X}, raw 0x{raw_candidate['raw']:08X}, section {secname}",
                    f"- First 32 bytes: {raw_candidate['data'][:32].hex(' ')}",
                    "", chr(96)*3+"asm"
                ]
                for ins in raw_candidate["insns"][:16]:
                    lines.append(f"{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
                lines += [chr(96)*3,""]
            else:
                lines += ["- No in-bounds segment-relative PE candidate.",""]
            continue
        cs.sort(key=lambda c:c["score"],reverse=True); c=cs[0]; mapped+=1
        confidence="high" if len(cs)==1 or c["score"]-cs[1]["score"]>=8 else "tentative"
        secname=c["section"].Name.rstrip(bytes([0])).decode("ascii","replace")
        lines += [f"- Module/segment: {p['module']}/{p['segment']} (flags 0x{flags:04X})",f"- Segment RVA range: 0x{sbase:08X}..0x{send:08X}",f"- Procedure offset/size: 0x{p['offset']:08X}/0x{p['size']:X}",f"- Selected interpretation: **{c['mode']}** ({confidence}; score {c['score']:.1f})",f"- Mapped RVA/VA: 0x{c['rva']:08X} / 0x{pe.OPTIONAL_HEADER.ImageBase+c['rva']:08X}",f"- Raw file offset: 0x{c['raw']:08X}; PE section: {secname}"]
        for alt in cs: lines.append(f"- Candidate {alt['mode']}: RVA 0x{alt['rva']:08X}, raw 0x{alt['raw']:08X}, score {alt['score']:.1f}")
        lines += ["","\x60\x60\x60asm"]
        for ins in c["insns"]: lines.append(f"{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
        lines += ["\x60\x60\x60",""]
    lines += ["## Validation summary","",f"- Methods with plausible mapped code: {mapped}/{len(selected)}",f"- Methods left unresolved: {len(selected)-mapped}",""]
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {out}; matched {len(selected)}; plausible {mapped}; unresolved {len(selected)-mapped}")

if __name__=="__main__": main()
