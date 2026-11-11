#!/usr/bin/env python3
"""Diagnose TD32 procedure offsets using logical segment -> PE section mapping."""
import pathlib
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
from analyze_emwat_td32 import find_td32, parse_td32

PATTERNS=("TfrmSimpleImageEditor@","TfrmGScanPreview@","TGearImgProc@")

def secname(sec):
    return sec.Name.rstrip(bytes([0])).decode("ascii","replace")

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-address-diagnostics.md")
    blob=src.read_bytes()
    hit=find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base,end,directory,_=hit
    _,names,modules,procedures=parse_td32(blob,base,end,directory)
    pe=pefile.PE(data=blob,fast_load=False)
    selected=[p for p in procedures if any(t.lower() in p["name"].lower() for t in PATTERNS)]
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    lines=[
        "# EMWAT TD32 procedure address diagnostics","",
        f"- Input: {src}",f"- ImageBase: 0x{pe.OPTIONAL_HEADER.ImageBase:08X}",
        f"- Target methods: {len(selected)}",
        "- Correct candidate: select PE section by the TD32 segment index (1-based), then add the procedure Offset to that section's RVA and raw pointer.",
        "- The procedure Offset is not treated as a PE RVA or a raw file offset.",
        "","## Candidate summary","","| Procedure | Segment | TD32 offset | PE section | RVA | Raw offset | Range checks |",
        "|---|---:|---:|---|---:|---:|---|"
    ]
    for p in selected:
        mod=modules.get(p["module"])
        seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
        if not seg or not (1<=p["segment"]<=len(pe.sections)):
            lines.append(f"| {p['name']} | {p['segment']} | 0x{p['offset']:08X} | unresolved | — | — | no segment/section |")
            continue
        _,flags,sbase,ssize=seg
        sec=pe.sections[p["segment"]-1]
        rva=sec.VirtualAddress+p["offset"]
        raw=sec.PointerToRawData+p["offset"]
        within_td32=sbase<=p["offset"] and p["offset"]+p["size"]<=sbase+ssize
        within_pe=p["offset"]+p["size"]<=sec.SizeOfRawData
        executable=bool(sec.Characteristics & 0x20000000)
        checks=f"TD32={within_td32}; PE={within_pe}; executable={executable}"
        lines.append(f"| {p['name']} | {p['segment']} | 0x{p['offset']:08X} | {secname(sec)} | 0x{rva:08X} | 0x{raw:08X} | {checks} |")
    lines += ["","## Method entry bytes and disassembly",""]
    for p in selected:
        mod=modules.get(p["module"])
        seg=next((x for x in mod[1] if x[0]==p["segment"]),None) if mod else None
        lines += [f"### {p['name']}",""]
        if not seg or not (1<=p["segment"]<=len(pe.sections)):
            lines += ["- Mapping unresolved.",""]; continue
        _,flags,sbase,ssize=seg
        sec=pe.sections[p["segment"]-1]
        raw=sec.PointerToRawData+p["offset"]
        rva=sec.VirtualAddress+p["offset"]
        valid=(sbase<=p["offset"] and p["offset"]+p["size"]<=sbase+ssize and p["offset"]+p["size"]<=sec.SizeOfRawData and bool(sec.Characteristics & 0x20000000))
        lines += [f"- TD32 segment range: 0x{sbase:08X}..0x{sbase+ssize:08X} (flags 0x{flags:04X})",f"- PE section: {secname(sec)}",f"- RVA/VA: 0x{rva:08X}/0x{pe.OPTIONAL_HEADER.ImageBase+rva:08X}",f"- Raw file offset: 0x{raw:08X}",f"- All range checks passed: {valid}"]
        if valid:
            data=blob[raw:raw+p["size"]]
            lines += [f"- First 32 bytes: {data[:32].hex(' ')}","",chr(96)*3+"asm"]
            for ins in list(md.disasm(data,pe.OPTIONAL_HEADER.ImageBase+rva))[:16]:
                lines.append(f"{ins.address:08X}  {ins.mnemonic:<8} {ins.op_str}")
            lines += [chr(96)*3,""]
        else:
            lines += ["- Bytes not disassembled because mapping validation failed.",""]
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {out}; diagnosed {len(selected)} procedures")

if __name__=="__main__": main()
