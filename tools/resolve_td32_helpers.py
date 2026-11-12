#!/usr/bin/env python3
"""Build a TD32-resolved direct-call graph for EMWAT image/scanning methods."""
import pathlib
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM
from analyze_emwat_td32 import find_td32, parse_td32

TARGETS=(
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
# Word lifecycle probes; print-handler symbols remain distinct.
"Wordviewer@OpenDoc","TWordViwer@SilentSaveEmwatDoc",
"TWordViwer@StoreFieldValuesForPrint","TWordViwer@OnControlerNotify",
"TEDPController@Notify","TEditWordDocument@PerformMethod")

def secname(sec):
    return sec.Name.rstrip(bytes([0])).decode("ascii","replace")

def map_va(pe,va):
    rva=va-pe.OPTIONAL_HEADER.ImageBase
    for index,sec in enumerate(pe.sections,1):
        if sec.VirtualAddress<=rva<sec.VirtualAddress+max(sec.Misc_VirtualSize,sec.SizeOfRawData):
            return index,sec,rva-sec.VirtualAddress
    return None,None,None

def resolve_symbol(procedures,segment,offset):
    matches=[p for p in procedures if p["segment"]==segment and p["offset"]<=offset<p["offset"]+p["size"]]
    return matches

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-helper-symbols.md")
    blob=src.read_bytes()
    hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,names,modules,procedures=parse_td32(blob,base,end,directory)
    pe=pefile.PE(data=blob,fast_load=False)
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    md.detail=True
    selected=[p for p in procedures if any(t.lower() in p["name"].lower() for t in TARGETS)]
    lines=["# EMWAT image/scanning call graph","",f"- Input: {src}",f"- TD32 procedure records: {len(procedures):,}",f"- Target methods analyzed: {len(selected)}","- Direct call targets are resolved against TD32 procedure ranges using the validated PE section-relative mapping.","- Virtual/indirect calls are retained as unresolved dispatches.",""]
    unique_targets=set()
    for p in selected:
        if not (1<=p["segment"]<=len(pe.sections)):
            continue
        sec=pe.sections[p["segment"]-1]
        mod=modules.get(p["module"])
        seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
        if not seg: continue
        _,_,sbase,ssize=seg
        if not (sbase<=p["offset"] and p["offset"]+p["size"]<=sbase+ssize and p["offset"]+p["size"]<=sec.SizeOfRawData):
            continue
        raw=sec.PointerToRawData+p["offset"]
        rva=sec.VirtualAddress+p["offset"]
        va=pe.OPTIONAL_HEADER.ImageBase+rva
        data=blob[raw:raw+p["size"]]
        ins=list(md.disasm(data,va))
        direct=[]
        indirect=[]
        for x in ins:
            if x.mnemonic=="call" and x.operands:
                op=x.operands[0]
                if op.type==CS_OP_IMM:
                    target=op.imm & 0xFFFFFFFF
                    direct.append((x.address,target))
                    unique_targets.add(target)
                else:
                    indirect.append((x.address,x.op_str))
        lines += [f"## {p['name']}","",f"- Entry VA: 0x{va:08X}; size: 0x{p['size']:X}"]
        if direct:
            lines.append("- Direct calls:")
            for call_va,target in direct:
                segno,tsec,toff=map_va(pe,target)
                resolved=resolve_symbol(procedures,segno,toff) if segno else []
                if resolved:
                    for sym in resolved:
                        lines.append(f"  - 0x{call_va:08X} -> 0x{target:08X} {sym['name']} (segment {segno}, +0x{toff-sym['offset']:X})")
                else:
                    lines.append(f"  - 0x{call_va:08X} -> 0x{target:08X} {secname(tsec) if tsec else 'outside PE sections'} (no containing TD32 procedure)")
        else:
            lines.append("- No direct calls.")
        if indirect:
            lines.append("- Indirect/virtual calls:")
            for call_va,opstr in indirect:
                lines.append(f"  - 0x{call_va:08X}: call {opstr}")
        lines.append("")
    lines += ["## Unique direct call targets","",f"- Unique direct-call addresses: {len(unique_targets)}","","| VA | Resolved TD32 symbol(s) |","|---:|---|"]
    for target in sorted(unique_targets):
        segno,sec,off=map_va(pe,target)
        resolved=resolve_symbol(procedures,segno,off) if segno else []
        if resolved:
            label="; ".join(x["name"] for x in resolved)
        else:
            label=f"unresolved ({secname(sec) if sec else 'outside PE sections'})"
        lines.append(f"| 0x{target:08X} | {label} |")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {out}; analyzed {len(selected)} methods and {len(unique_targets)} unique direct-call targets")

if __name__=="__main__": main()
