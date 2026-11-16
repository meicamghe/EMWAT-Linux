#!/usr/bin/env python3
"""Inspect a Delphi Win32 VMT at a known virtual address."""
import pathlib, struct, sys
import pefile
from analyze_emwat_td32 import find_td32, parse_td32

VMT_SELF=-88
VMT_CLASSNAME=-56
VMT_INSTANCESIZE=-52
VMT_PARENT=-48

def u32(b,o): return struct.unpack_from("<I",b,o)[0]
def va_raw(pe,va):
    rva=va-pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        span=max(s.Misc_VirtualSize,s.SizeOfRawData)
        if s.VirtualAddress<=rva<s.VirtualAddress+span:
            d=rva-s.VirtualAddress
            if d<s.SizeOfRawData: return s.PointerToRawData+d
    return None
def main():
    if len(sys.argv)<3: raise SystemExit("usage: inspect_delphi_vmt_address.py <pe-file> <vmt-va> [output.md]")
    path=pathlib.Path(sys.argv[1]); vmt=int(sys.argv[2],0)
    out=pathlib.Path(sys.argv[3] if len(sys.argv)>3 else "bpl-analysis/EmwatMethods-vmt-address.md")
    blob=path.read_bytes(); pe=pefile.PE(data=blob,fast_load=False)
    hit=find_td32(blob)
    names={}
    if hit:
        base,end,directory,_=hit
        _,_,modules,procedures=parse_td32(blob,base,end,directory)
        for p in procedures:
            if not (1<=p["segment"]<=len(pe.sections)): continue
            sec=pe.sections[p["segment"]-1]
            mod=modules.get(p["module"])
            seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
            if not seg: continue
            _,_,segbase,segsize=seg
            if segbase<=p["offset"]<segbase+segsize and p["offset"]<sec.SizeOfRawData:
                va=pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress+p["offset"]
                names.setdefault(va,[]).append(p["name"])
    def readva(addr):
        raw=va_raw(pe,addr)
        return u32(blob,raw) if raw is not None and raw+4<=len(blob) else None
    def label(addr):
        if addr is None: return "unmapped"
        return ", ".join(names.get(addr,[])) or "no exact TD32 entry"
    fields={
      "Self pointer":readva(vmt+VMT_SELF),
      "Class-name field":readva(vmt+VMT_CLASSNAME),
      "Instance size":readva(vmt+VMT_INSTANCESIZE),
      "Parent VMT":readva(vmt+VMT_PARENT),
    }
    td32_status = "available" if hit else "not present; addresses shown without symbol labels"
    lines=["# Delphi VMT address inspection","",f"- VMT VA: 0x{vmt:08X}","",f"- TD32 symbols: {td32_status}",""]
    for k,val in fields.items():
        if val is None: lines.append(f"- {k}: unmapped")
        elif k=="Instance size": lines.append(f"- {k}: 0x{val:X}")
        else: lines.append(f"- {k}: 0x{val:08X} ({label(val)})")
    cname=fields["Class-name field"]
    if cname:
        raw=va_raw(pe,cname)
        if raw is not None:
            n=blob[raw]
            sample=blob[raw:raw+32]
            decoded=""
            if n<=80 and raw+1+n<=len(blob):
                decoded=blob[raw+1:raw+1+n].decode("ascii","replace")
            lines += ["",f"- Class-name target bytes: {sample.hex(' ')}",f"- Shortstring interpretation: {decoded or 'not a valid shortstring'}"]
    lines += ["","## Leading VMT slots",""]
    for off in range(0,0x60,4):
        val=readva(vmt+off)
        if val is None: lines.append(f"- +0x{off:02X}: unmapped")
        else: lines.append(f"- +0x{off:02X}: 0x{val:08X} ({label(val)})")
    lines.append("")
    out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\n".join(lines),encoding="utf-8")
    print(f"Wrote {out}")
if __name__=="__main__": main()
