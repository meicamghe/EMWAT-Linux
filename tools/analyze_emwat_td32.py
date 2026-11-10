#!/usr/bin/env python3
"""Extract Borland TD32 symbols and procedure ranges from a Delphi PE/BPL."""
import argparse
import pathlib
import struct
import pefile

FB09 = 0x39304246
FB0A = 0x41304246
SST_MODULE = 0x120
SST_ALIGN_SYMBOLS = 0x125
SST_NAMES = 0x130
SYM_LPROC32 = 0x0204
SYM_GPROC32 = 0x0205

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]

def find_td32(blob):
    # TD32 has a signature/offset trailer; the signature is repeated at the base.
    for end in range(len(blob), max(0, len(blob)-4096), -1):
        if end < 8: break
        sig, back = struct.unpack_from("<II", blob, end-8)
        if sig not in (FB09, FB0A) or back < 8 or back > end:
            continue
        base = end - back
        if base + 8 <= len(blob):
            sig2, dir_off = struct.unpack_from("<II", blob, base)
            if sig2 == sig and base + dir_off + 16 <= end:
                return base, end, dir_off, sig
    # Also check the final trailer of the entire file.
    if len(blob) >= 8:
        sig, back = struct.unpack_from("<II", blob, len(blob)-8)
        if sig in (FB09, FB0A) and 8 <= back <= len(blob):
            base = len(blob)-back
            if base+8 <= len(blob):
                sig2, d = struct.unpack_from("<II", blob, base)
                if sig2 == sig and base+d+16 <= len(blob):
                    return base, len(blob), d, sig
    return None

def parse_td32(blob, base, end, dir_off):
    directory = base + dir_off
    hdr_size, ent_size, count, next_dir, flags = struct.unpack_from("<HHIII", blob, directory)
    if ent_size < 12 or count > 100000 or directory + hdr_size + count*ent_size > end:
        raise ValueError("Invalid TD32 subsection directory")
    entries = []
    for i in range(count):
        p = directory + hdr_size + i*ent_size
        typ, mod, off, size = struct.unpack_from("<HHII", blob, p)
        if base+off+size <= end:
            entries.append((typ, mod, base+off, size))
    # names table
    names = []
    for typ, mod, off, size in entries:
        if typ != SST_NAMES or size < 4: continue
        n = u32(blob, off)
        p, limit = off+4, off+size
        for _ in range(min(n, 200000)):
            if p >= limit: break
            ln = blob[p]; p += 1
            start = p
            while p < limit and blob[p] != 0:
                p += 1
            names.append(blob[start:p].decode("utf-8", "replace"))
            p += 1
    modules = {}
    for typ, mod, off, size in entries:
        if typ != SST_MODULE or size < 28: continue
        overlay, lib, seg_count, style, name_idx, timestamp = struct.unpack_from("<HHHHII", blob, off)
        segs=[]
        p=off+28
        for _ in range(min(seg_count, 4096)):
            if p+12 > off+size: break
            seg, sflags, soff, ssize = struct.unpack_from("<HHII", blob, p)
            segs.append((seg,sflags,soff,ssize)); p+=12
        modules[mod]=(name_idx,segs)
    procedures=[]
    for typ, mod, off, size in entries:
        if typ != SST_ALIGN_SYMBOLS or size < 4: continue
        p=off+4
        limit=off+size
        while p+4 <= limit:
            rec_size=u16(blob,p)
            if rec_size < 2 or p+2+rec_size > limit: break
            sym=u16(blob,p+2)
            if sym in (SYM_LPROC32,SYM_GPROC32) and rec_size >= 42:
                payload=p+4
                parent, pend, pnext, length, dbg_start, dbg_end, code_off = struct.unpack_from("<IIIIIII",blob,payload)
                segment=u16(blob,payload+28)
                name_idx=u32(blob,payload+36)
                name=names[name_idx] if name_idx < len(names) else f"<name-index-{name_idx}>"
                procedures.append({"module":mod,"name":name,"segment":segment,"offset":code_off,"size":length,"debug_start":dbg_start,"debug_end":dbg_end,"symbol":"GPROC32" if sym==SYM_GPROC32 else "LPROC32"})
            p += rec_size+2
    return entries,names,modules,procedures

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("--out",default="bpl-analysis/EmwatMethods-TD32-analysis.md")
    args=ap.parse_args()
    path=pathlib.Path(args.input); blob=path.read_bytes()
    pe=pefile.PE(data=blob,fast_load=False)
    sections=[]
    for s in pe.sections:
        sections.append((s.Name.rstrip(b"\\0").decode("ascii","replace"),s.PointerToRawData,s.SizeOfRawData))
    candidates=[]
    # Prefer the PE debug-directory payload if it is TD32, then scan sections.
    for entry in getattr(pe,"DIRECTORY_ENTRY_DEBUG",[]):
        ptr=entry.struct.PointerToRawData; size=entry.struct.SizeOfData
        if ptr and size and ptr+size<=len(blob):
            hit=find_td32(blob[ptr:ptr+size])
            if hit: candidates.append((ptr,ptr+size,hit))
    if not candidates:
        for name,ptr,size in sections:
            if name==".debug" or name.lower().startswith(".debug"):
                hit=find_td32(blob[ptr:ptr+size])
                if hit: candidates.append((ptr,ptr+size,hit))
    if not candidates:
        hit=find_td32(blob)
        if hit: candidates.append((0,len(blob),hit))
    lines=["# EMWAT Methods TD32 debug analysis","",f"- Input: {path}","- File size: {:,} bytes".format(len(blob))]
    if not candidates:
        lines += ["","**TD32 signature not located.** The PE debug payload may use a different layout."]
    else:
        region_start,region_end,(base,end,dir_off,sig)=candidates[0]
        # find_td32 offsets are relative to the searched region
        base += region_start; end += region_start
        entries,names,modules,procedures=parse_td32(blob,base,end,base+dir_off-region_start if False else dir_off)
        lines += ["",f"- TD32 signature: {'FB09' if sig==FB09 else 'FB0A'}","- TD32 base file offset: 0x{:X}".format(base),f"- Subsections: {len(entries)}",f"- Name records: {len(names)}",f"- Module records: {len(modules)}",f"- Procedure records: {len(procedures)}",""]
        lines += ["## Subsection directory","","| Type | Module | Size | File offset |","|---:|---:|---:|---:|"]
        for typ,mod,off,size in entries:
            lines.append(f"| 0x{typ:04X} | {mod} | {size:,} | 0x{off:X} |")
        lines += ["","## Target procedures","","| Module | Procedure | Segment | Offset | Size | Debug range |","|---|---|---:|---:|---:|---:|"]
        targets=("simpleimageeditor","gscanpreview","imageprocessing","resultimage")
        selected=[x for x in procedures if any(t in x["name"].lower() for t in targets)]
        for x in selected:
            modname=names[modules[x["module"]][0]] if x["module"] in modules and modules[x["module"]][0]<len(names) else str(x["module"])
            lines.append(f"| {modname} | {x['name']} | {x['segment']} | 0x{x['offset']:08X} | 0x{x['size']:X} | +0x{x['debug_start']:X}..+0x{x['debug_end']:X} |")
        lines += ["","## All target symbol names",""]
        for x in selected:
            lines.append(f"- {x['name']} (segment {x['segment']}, offset 0x{x['offset']:08X}, size 0x{x['size']:X})")
        if not selected:
            lines.append("No matching procedure records were decoded; inspect all procedure records and module indexes.")
    out=pathlib.Path(args.out); out.parent.mkdir(parents=True,exist_ok=True); out.write_text("\\n".join(lines)+"\\n",encoding="utf-8")
    print(f"Wrote {out} ({len(lines)} lines)")

if __name__=="__main__":
    main()
