#!/usr/bin/env python3
"""Validate TD32 logical segment offsets against PE section-relative addresses."""
import pathlib
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from analyze_emwat_td32 import find_td32, parse_td32

TARGETS=("TGearImgProc@","TfrmSimpleImageEditor@","TfrmGScanPreview@")

def decode_name(names,index):
    return names[index] if 0 <= index < len(names) else f"<name-index-{index}>"

def secname(sec):
    return sec.Name.rstrip(bytes([0])).decode("ascii","replace")

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-module-map.md")
    blob=src.read_bytes()
    hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,names,modules,procedures=parse_td32(blob,base,end,directory)
    pe=pefile.PE(data=blob,fast_load=False)
    selected=[p for p in procedures if any(t.lower() in p["name"].lower() for t in TARGETS)]
    module_ids=sorted({p["module"] for p in selected})
    lines=[
        "# EMWAT TD32 segment-to-PE mapping validation","",
        f"- Input: {src}",f"- Target procedure records: {len(selected)}",
        "- Address model: procedure Offset is interpreted relative to its TD32 logical segment; segment number is matched to the 1-based PE section index.",
        "- Mapping is accepted only when procedure and module segment ranges fit the same executable section.",
        "","## PE sections","","| PE section index | Name | RVA | Virtual size | Raw pointer | Raw size | Executable |",
        "|---:|---|---:|---:|---:|---:|---:|"
    ]
    for i,s in enumerate(pe.sections,1):
        lines.append(f"| {i} | {secname(s)} | 0x{s.VirtualAddress:08X} | 0x{s.Misc_VirtualSize:X} | 0x{s.PointerToRawData:08X} | 0x{s.SizeOfRawData:X} | {bool(s.Characteristics & 0x20000000)} |")
    lines += ["","## Module segment descriptors","","| Module index | Module name | TD32 segment | Flags | Segment offset | Size | PE section candidate | Range fit |","|---:|---|---:|---:|---:|---:|---|---|"]
    for mid in module_ids:
        mod=modules.get(mid)
        if not mod: continue
        name_idx,segs=mod
        for segno,flags,offset,size in segs:
            if 1<=segno<=len(pe.sections):
                sec=pe.sections[segno-1]
                limit=max(sec.Misc_VirtualSize,sec.SizeOfRawData)
                fits=offset+size<=limit
                desc=f"{secname(sec)} (#{segno})"
                fit="yes" if fits else f"no (end 0x{offset+size:X} > 0x{limit:X})"
            else:
                desc="no matching PE section"; fit="no"
            lines.append(f"| {mid} | {decode_name(names,name_idx)} | {segno} | 0x{flags:04X} | 0x{offset:08X} | 0x{size:X} | {desc} | {fit} |")
    lines += ["","## Target procedure mappings",""]
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    for p in selected:
        mod=modules.get(p["module"])
        seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
        lines += [f"### {p['name']}","",f"- Module/segment: {p['module']}/{p['segment']}",f"- Procedure offset/size: 0x{p['offset']:08X}/0x{p['size']:X}"]
        if not seg:
            lines += ["- Mapping unresolved: TD32 segment descriptor missing.",""]; continue
        _,flags,sbase,ssize=seg
        lines.append(f"- TD32 module contribution: 0x{sbase:08X}..0x{sbase+ssize:08X} (flags 0x{flags:04X})")
        if not (1<=p["segment"]<=len(pe.sections)):
            lines += ["- Mapping unresolved: no PE section with this segment index.",""]; continue
        sec=pe.sections[p["segment"]-1]
        sec_limit=max(sec.Misc_VirtualSize,sec.SizeOfRawData)
        valid_range=(sbase<=p["offset"] and p["offset"]+p["size"]<=sbase+ssize)
        valid_section=(p["offset"]+p["size"]<=sec.SizeOfRawData)
        executable=bool(sec.Characteristics & 0x20000000)
        lines += [f"- PE section candidate: {secname(sec)} (index {p['segment']})",f"- Procedure inside TD32 module range: {valid_range}",f"- Procedure fits PE raw section: {valid_section}",f"- PE section executable: {executable}"]
        if not (valid_range and valid_section and executable):
            lines += ["- **Mapping unresolved:** range/section validation failed.",""]; continue
        raw=sec.PointerToRawData+p["offset"]
        rva=sec.VirtualAddress+p["offset"]
        va=pe.OPTIONAL_HEADER.ImageBase+rva
        data=blob[raw:raw+p["size"]]
        ins=list(md.disasm(data,va))
        lines += [f"- Mapped RVA/VA: 0x{rva:08X}/0x{va:08X}",f"- Raw file offset: 0x{raw:08X}",f"- First bytes: {data[:24].hex(' ')}","- Entry disassembly:"]
        for x in ins[:8]:
            lines.append(f"  - {x.address:08X} {x.mnemonic:<8} {x.op_str}")
        lines.append("")
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {out}; validated {len(selected)} target procedures")

if __name__=="__main__": main()
