#!/usr/bin/env python3
"""Trace Delphi Win32 VMT interface tables and interface vtables in a PE32 BPL."""
import pathlib, struct, sys, uuid
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

VMT_SELF=-88
VMT_INTF=-84
VMT_TYPEINFO=-72
VMT_CLASSNAME=-56
VMT_INSTANCESIZE=-52
VMT_PARENT=-48
ENTRY_SIZE=28

def u32(b,o): return struct.unpack_from("<I",b,o)[0]

def main():
    src=pathlib.Path(sys.argv[1])
    out=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "bpl-analysis/EmwatMethods-interface-tables.md")
    blob=src.read_bytes()
    pe=pefile.PE(data=blob,fast_load=False)
    image=pe.OPTIONAL_HEADER.ImageBase
    def va_raw(va):
        rva=va-image
        for s in pe.sections:
            span=max(s.Misc_VirtualSize,s.SizeOfRawData)
            if s.VirtualAddress<=rva<s.VirtualAddress+span:
                d=rva-s.VirtualAddress
                if d<s.SizeOfRawData: return s.PointerToRawData+d
        return None
    def raw_va(raw):
        for s in pe.sections:
            if s.PointerToRawData<=raw<s.PointerToRawData+s.SizeOfRawData:
                return image+s.VirtualAddress+raw-s.PointerToRawData
        return None
    def ptr(va):
        r=va_raw(va)
        return u32(blob,r) if r is not None and r+4<=len(blob) else None
    def shortstr(raw):
        if raw is None or raw>=len(blob): return None
        n=blob[raw]
        if not 1<=n<=120 or raw+1+n>len(blob): return None
        x=blob[raw+1:raw+1+n]
        try: return x.decode("ascii")
        except UnicodeDecodeError: return None
    def section_for_raw(raw):
        for s in pe.sections:
            if s.PointerToRawData<=raw<s.PointerToRawData+s.SizeOfRawData:
                return s.Name.rstrip(b"\x00").decode("ascii","replace")
        return "?"
    def disasm_vtable(vtable, count=12):
        r=va_raw(vtable)
        if r is None: return []
        md=Cs(CS_ARCH_X86,CS_MODE_32)
        result=[]
        for i in range(count):
            if r+4*(i+1)>len(blob): break
            target=u32(blob,r+4*i)
            tr=va_raw(target)
            if tr is None:
                result.append((i,target,"not mapped"))
                continue
            insns=list(md.disasm(blob[tr:tr+32],target))[:6]
            desc=("; ".join(f"{ins.mnemonic} {ins.op_str}" for ins in insns) if insns else "no decode")
            result.append((i,target,desc))
        return result

    # Discover Delphi wrapper classes likely related to image editing, scanning or Word.
    candidates={}
    # Collect likely class-name RTTI first, then scan aligned pointer fields once.
    class_names={}
    for m in __import__("re").finditer(rb"[\\x01-\\x78][A-Za-z_][A-Za-z0-9_@$]{2,100}",blob):
        raw=m.start()
        name=shortstr(raw)
        if not name or not name.startswith("T") or not any(k in name.lower() for k in ("editor","image","gear","scan","crop","word","field","document")):
            continue
        name_va=raw_va(raw)
        if name_va is not None:
            class_names[name_va]=name
    for pos in range(0, len(blob)-3, 4):
        name=class_names.get(u32(blob,pos))
        if name is None: continue
        field_va=raw_va(pos)
        if field_va is None: continue
        vmt=field_va-VMT_CLASSNAME
        vr=va_raw(vmt)
        if vr is None: continue
        selfp=ptr(vmt+VMT_SELF); size=ptr(vmt+VMT_INSTANCESIZE); parent=ptr(vmt+VMT_PARENT)
        if selfp==vmt and size is not None and 0x20<=size<=0x10000:
            candidates[vmt]=(name,vr,size,parent)

    lines=["# Delphi interface table trace","",
           f"- Input: {src}; PE32 ImageBase 0x{image:08X}",
           "- VMT header offsets used: self=-0x58, interface table=-0x54, typeinfo=-0x48, class name=-0x38.",
           f"- Candidate interface entries use {ENTRY_SIZE}-byte records (GUID + VTable + IOffset + ImplGetter); raw bytes are retained for independent validation.",""]
    md=Cs(CS_ARCH_X86,CS_MODE_32)
    found=0
    lines.append(f"- Candidate VMTs passing self-pointer and instance-size checks: {len(candidates)}")
    for vmt,(name,vr,size,parent) in sorted(candidates.items()):
        intf=ptr(vmt+VMT_INTF)
        ti=ptr(vmt+VMT_TYPEINFO)
        if not intf and not ti: continue
        lines += [f"## {name} — VMT 0x{vmt:08X}","",
                  f"- Instance size: 0x{size:X}; parent VMT: 0x{(parent or 0):08X}",
                  f"- Interface table pointer: 0x{(intf or 0):08X}",
                  f"- Class typeinfo pointer: 0x{(ti or 0):08X}"]
        ir=va_raw(intf) if intf else None
        if ir is None:
            lines += ["- Interface table pointer is null or unmapped.",""]
            continue
        count=struct.unpack_from("<I",blob,ir)[0]
        lines.append(f"- Interface entry count: {count}")
        if count>64:
            lines += ["- Count exceeds sanity limit; no entries decoded.",""]
            continue
        for i in range(count):
            e=ir+4+i*ENTRY_SIZE
            if e+ENTRY_SIZE>len(blob):
                lines.append(f"- Entry {i}: truncated")
                break
            rawguid=blob[e:e+16]
            iid=str(uuid.UUID(bytes_le=rawguid))
            vt, ioffset, getter=struct.unpack_from("<IiI",blob,e+16)
            found+=1
            lines += [f"### Interface entry {i}",
                      f"- IID: {iid}",
                      f"- VTable: 0x{vt:08X}; IOffset: {ioffset}; ImplGetter: 0x{getter:08X}",
                      f"- Raw entry: {blob[e:e+ENTRY_SIZE].hex(' ')}"]
            if vt and va_raw(vt) is not None:
                lines.append("- VTable slots:")
                for slot,target,desc in disasm_vtable(vt):
                    lines.append(f"  - +0x{slot*4:02X}: 0x{target:08X} — {desc}")
        lines.append("")
    # Decode the concrete Delphi tkInterface RTTI record for IIPEditor.
    # Win32 tkInterface TTypeData: IntfParent (4), IntfFlags (1), GUID (16), UnitName (ShortString).
    lines += ["## IIPEditor interface RTTI decode", ""]
    ii_hits=[]
    interface_names=("IIPEditor","IImageProcessor","IResultImage","IResultImageUnit","IProcessResult","Fields","Field","_Document","Document","Range","Selection","Tables")
    for interface_name in interface_names:
        encoded=interface_name.encode("ascii")
        for m in __import__("re").finditer(__import__("re").escape(encoded), blob):
            name_raw=m.start()
            type_raw=name_raw-2
            if type_raw < 0 or blob[type_raw] != 15 or blob[type_raw+1] != len(encoded):
                continue
            data_raw=name_raw+len(encoded)
            if data_raw+22 > len(blob):
                continue
            parent_ref=u32(blob,data_raw)
            flags=blob[data_raw+4]
            iid_raw=blob[data_raw+5:data_raw+21]
            unit=shortstr(data_raw+21)
            iid=str(uuid.UUID(bytes_le=iid_raw))
            type_va=raw_va(type_raw)
            ii_hits.append((interface_name,type_va,parent_ref,flags,iid,unit))
    for interface_name,type_va,parent_ref,flags,iid,unit in ii_hits:
        lines.append(f"### {interface_name}")
        lines.append(f"- TypeInfo: 0x{(type_va or 0):08X}; parent reference: 0x{parent_ref:08X}; flags: 0x{flags:02X}")
        lines.append(f"- IID: {iid}; unit: {unit or 'unknown'}")
        matches=[]
        for vmt,(name,vr,size,parent) in candidates.items():
            intf=ptr(vmt+VMT_INTF)
            ir=va_raw(intf) if intf else None
            if ir is None: continue
            n=struct.unpack_from("<I",blob,ir)[0]
            if n>64: continue
            for i in range(n):
                e=ir+4+i*ENTRY_SIZE
                if e+ENTRY_SIZE>len(blob): continue
                if str(uuid.UUID(bytes_le=blob[e:e+16])) == iid:
                    vt=u32(blob,e+16)
                    matches.append((name,vmt,vt,u32(blob,e+20)))
        for name,vmt,vt,ioffset in matches:
            lines.append(f"- Implementing class: {name}; VMT: 0x{vmt:08X}; interface VTable: 0x{vt:08X}; IOffset: 0x{ioffset:X}")
            vr=va_raw(vt)
            if vr is None: continue
            lines.append("- Interface vtable slots (12 entries sampled: slots 0-2 are IUnknown; later slots are implementation-specific):")
            for slot in range(12):
                target=u32(blob,vr+slot*4)
                tr=va_raw(target)
                if tr is None:
                    lines.append(f"  - +0x{slot*4:02X}: 0x{target:08X} (unmapped)")
                    continue
                insns=list(md.disasm(blob[tr:tr+32],target))[:6]
                desc="; ".join(f"{x.mnemonic} {x.op_str}" for x in insns) or "no decode"
                lines.append(f"  - +0x{slot*4:02X}: 0x{target:08X} — {desc}")
    if not ii_hits:
        lines.append("- No structurally valid requested tkInterface RTTI records found.")
    lines.append("")

    # Find IIPEditor shortstring/typeinfo occurrences and nearby references.
    lines += ["## IIPEditor RTTI/string candidates",""]
    hits=[]
    for term in (b"IIPEditor",b"IImageProcessor",b"IResultImage",b"IResultImageUnit",b"IProcessResult",b"Imageprocessing",b"TEditorNotificationType"):
        start=0
        while True:
            p=blob.find(term,start)
            if p<0: break
            hits.append((p,term.decode("ascii")))
            start=p+1
    for raw,term in hits[:250]:
        va=raw_va(raw)
        sample=blob[max(0,raw-16):min(len(blob),raw+len(term)+40)]
        lines.append(f"- file+0x{raw:X} VA={('0x%08X'%va) if va else 'unmapped'} term={term}; context={sample.hex(' ')}")
    lines += ["",f"- Candidate VMTs with metadata: {sum(1 for v,(n,r,s,p) in candidates.items() if ptr(v+VMT_INTF) or ptr(v+VMT_TYPEINFO))}",
              f"- Interface entries decoded: {found}",""]
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote {out}; candidate VMTs={len(candidates)}; interface entries={found}; RTTI hits={len(hits)}")

if __name__=="__main__": main()
