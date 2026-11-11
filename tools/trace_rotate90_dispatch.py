#!/usr/bin/env python3
"""Resolve Delphi import thunks and trace TGearImgProc +0x28 field usage."""
import pathlib, sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from capstone.x86 import X86_OP_IMM, X86_OP_MEM
from analyze_emwat_td32 import find_td32, parse_td32

def main():
    src=pathlib.Path(sys.argv[1]); out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-rotate90-deep-trace.md")
    blob=src.read_bytes(); pe=pefile.PE(data=blob, fast_load=False)
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    imports={}
    for entry in getattr(pe,"DIRECTORY_ENTRY_IMPORT",[]):
        dll=entry.dll.decode(errors="replace")
        for imp in entry.imports:
            if imp.address:
                name=imp.name.decode(errors="replace") if imp.name else f"ordinal_{imp.ordinal}"
                imports[imp.address]=(dll,name)
    def va_raw(va):
        rva=va-pe.OPTIONAL_HEADER.ImageBase
        for s in pe.sections:
            if s.VirtualAddress <= rva < s.VirtualAddress+s.SizeOfRawData:
                return s.PointerToRawData+rva-s.VirtualAddress
    hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 not found")
    base,end,directory,_=hit
    _,_,modules,procs=parse_td32(blob,base,end,directory)
    mapped=[]
    for p in procs:
        if not (1<=p["segment"]<=len(pe.sections)): continue
        sec=pe.sections[p["segment"]-1]; mod=modules.get(p["module"])
        seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
        if not seg: continue
        _,_,sb,ss=seg
        if not(sb<=p["offset"] and p["offset"]+p["size"]<=sb+ss): continue
        if p["offset"]+p["size"]>sec.SizeOfRawData: continue
        raw=sec.PointerToRawData+p["offset"]
        if raw+p["size"]>len(blob): continue
        va=pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress+p["offset"]
        mapped.append((va,va+p["size"],p,raw))
    def label(va):
        z=[x for x in mapped if x[0]<=va<x[1]]
        if not z:return "no TD32 symbol"
        return min(z,key=lambda x:x[1]-x[0])[2]["name"]
    lines=["# Deep Rotate90 dispatch trace","","## Import thunk resolution","",
           f"- Import entries parsed: {len(imports)}",""]
    for va in [0x0062F430,0x0062F42C,0x0062F428,0x0062F454,0x0062F450,0x0062F44C]:
        lines.append(f"- IAT 0x{va:08X}: {imports.get(va,('not found',''))[0]}!{imports.get(va,('','unresolved'))[1]}")
    lines += ["","## Code thunks around 0x004035D8",""]
    for va in range(0x004035D8,0x00403760,8):
        raw=va_raw(va)
        if raw is None: continue
        ins=list(md.disasm(blob[raw:raw+6],va))
        if not ins: continue
        i=ins[0]
        if i.mnemonic=="jmp" and i.operands and i.operands[0].type==X86_OP_MEM:
            slot=i.operands[0].mem.disp & 0xffffffff
            dll,name=imports.get(slot,("not found","unresolved"))
            lines.append(f"- 0x{va:08X}: jmp [0x{slot:08X}] -> {dll}!{name}")
    lines += ["","## TGearImgProc and Imageprocessing field references (+0x28)",""]
    for start,stop,p,raw in mapped:
        name=p["name"]
        if "GearImgProc" not in name and "Imageprocessing" not in name: continue
        for i in md.disasm(blob[raw:raw+p["size"]],start):
            for op in i.operands:
                if op.type==X86_OP_MEM and op.mem.disp==0x28:
                    lines.append(f"- 0x{i.address:08X}: {name}: {i.mnemonic} {i.op_str}")
    lines += ["","## TGearImgProc constructors, setters, and related procedures",""]
    for start,stop,p,raw in mapped:
        n=p["name"]
        if "GearImgProc" in n:
            lines.append(f"- 0x{start:08X} size=0x{p['size']:X}: {n}")
    lines += ["","## Interpretation","",
      "- Rotate90 loads the object pointer from [self+0x28], loads its first VMT slot, and invokes that slot indirectly.",
      "- The previous 0x004035D8 address is a jump thunk; this report resolves its IAT target separately.",
      "- Only references inside Imageprocessing/TGearImgProc symbols are listed here; generic +0x28 stack-frame references are excluded.",
      "- Runtime class identity still requires resolving the assigned object's constructor or interface implementation.",
      ""]
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {out}; imports={len(imports)}; mapped procedures={len(mapped)}")
if __name__=="__main__": main()
