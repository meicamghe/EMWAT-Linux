#!/usr/bin/env python3
"""Find direct CALL xrefs to a VA in TD32-bounded procedures."""
import pathlib, sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const
from analyze_emwat_td32 import find_td32, parse_td32

def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: trace_td32_callers.py <pe-file> <target-va> [output.md]")
    src=pathlib.Path(sys.argv[1]); target=int(sys.argv[2],0)
    out=pathlib.Path(sys.argv[3] if len(sys.argv)>3 else "bpl-analysis/EmwatMethods-callers.md")
    blob=src.read_bytes(); pe=pefile.PE(data=blob,fast_load=False)
    hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,_,modules,procedures=parse_td32(blob,base,end,directory)
    md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True
    rows=[]
    for p in procedures:
        if not (1<=p["segment"]<=len(pe.sections)): continue
        sec=pe.sections[p["segment"]-1]
        mod=modules.get(p["module"])
        seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
        if not seg: continue
        _,_,segbase,segsize=seg
        if not (segbase<=p["offset"] and p["offset"]+p["size"]<=segbase+segsize): continue
        if p["offset"]+p["size"]>sec.SizeOfRawData: continue
        raw=sec.PointerToRawData+p["offset"]
        va=pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress+p["offset"]
        insns=list(md.disasm(blob[raw:raw+p["size"]],va))
        for i,ins in enumerate(insns):
            if ins.mnemonic!="call" or not ins.operands: continue
            op=ins.operands[0]
            if op.type==x86_const.X86_OP_IMM and (op.imm & 0xFFFFFFFF)==target:
                lo=max(0,i-4); hi=min(len(insns),i+5)
                context="\n".join(f"  {x.address:08X}  {x.mnemonic:<8} {x.op_str}" for x in insns[lo:hi])
                rows.append((p["name"],ins.address,context))
    lines=["# Direct TD32 call-site scan","",f"- Target VA: 0x{target:08X}",
           "- Only direct immediate CALL instructions inside TD32-bounded procedures are listed.",
           "- Indirect/VMT dispatches are not resolved by this scan.",""]
    if not rows: lines.append("- No direct CALL xrefs found.")
    for name,va,context in sorted(rows,key=lambda x:x[1]):
        lines += [f"## {name} — call at 0x{va:08X}","",chr(96)*3+"asm",context,chr(96)*3,""]
    lines += [f"- Total direct callsites: {len(rows)}",""]
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {out}; direct callsites={len(rows)}")
if __name__=="__main__": main()
