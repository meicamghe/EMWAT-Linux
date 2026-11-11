#!/usr/bin/env python3
"""Resolve called helper VAs to TD32 procedure symbols and nearby symbols."""
import pathlib
import sys
import pefile
from analyze_emwat_td32 import find_td32, parse_td32

TARGET_VAS=(0x004AFEA8,0x004AFEC8,0x004AFED0,0x004EF0E4,0x004EEEC4,0x0061D36C,0x0061E680)

def secname(sec):
    return sec.Name.rstrip(bytes([0])).decode("ascii","replace")

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-helper-symbols.md")
    blob=src.read_bytes()
    hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,names,modules,procedures=parse_td32(blob,base,end,directory)
    pe=pefile.PE(data=blob,fast_load=False)
    lines=["# EMWAT helper address to TD32 symbol resolution","",f"- Input: {src}",f"- Procedure records: {len(procedures):,}","- Target helper addresses: "+", ".join(f"0x{x:08X}" for x in TARGET_VAS),"",""]
    for va in TARGET_VAS:
        rva=va-pe.OPTIONAL_HEADER.ImageBase
        sec=None
        for s in pe.sections:
            if s.VirtualAddress<=rva<s.VirtualAddress+max(s.Misc_VirtualSize,s.SizeOfRawData):
                sec=s; break
        lines += [f"## VA 0x{va:08X}",""]
        if sec is None:
            lines += [f"- RVA: 0x{rva:08X}; no containing PE section.",""]; continue
        segno=pe.sections.index(sec)+1
        offset=rva-sec.VirtualAddress
        raw=pe.get_offset_from_rva(rva)
        lines += [f"- PE section: {secname(sec)} (index {segno})",f"- Section-relative TD32 offset: 0x{offset:08X}",f"- Raw file offset: 0x{raw:08X}"]
        same=[p for p in procedures if p["segment"]==segno]
        containing=[p for p in same if p["offset"]<=offset<p["offset"]+p["size"]]
        if containing:
            lines.append("- Containing TD32 procedure symbol(s):")
            for p in containing:
                lines.append(f"  - {p['name']} (module {p['module']}, offset 0x{p['offset']:08X}, size 0x{p['size']:X}, +0x{offset-p['offset']:X})")
        else:
            lines.append("- No TD32 procedure symbol contains this address.")
        previous=sorted((p for p in same if p["offset"]<offset),key=lambda p:p["offset"],reverse=True)[:4]
        following=sorted((p for p in same if p["offset"]>offset),key=lambda p:p["offset"])[:4]
        lines.append("- Nearest preceding symbols:")
        for p in previous:
            lines.append(f"  - {p['name']} @ 0x{p['offset']:08X} (size 0x{p['size']:X})")
        lines.append("- Nearest following symbols:")
        for p in following:
            lines.append(f"  - {p['name']} @ 0x{p['offset']:08X} (size 0x{p['size']:X})")
        data=blob[raw:raw+24]
        lines += [f"- Bytes: {data.hex(' ')}",""]
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {out}; resolved {len(TARGET_VAS)} helper addresses")

if __name__=="__main__": main()
