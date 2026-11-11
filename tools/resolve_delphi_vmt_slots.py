#!/usr/bin/env python3
"""Locate Delphi Win32 VMTs by their class-name RTTI and resolve selected slots."""
import pathlib, struct, sys
import pefile
from analyze_emwat_td32 import find_td32, parse_td32

TARGET_CLASSES = (
    "TfrmSimpleImageEditor", "TfrmGScanPreview", "TfrmImageTools",
    "TGearImgProc",
)
SLOTS = (0x64, 0x88, 0xA8, 0x108)
VMT_SELF = -88
VMT_CLASSNAME = -56
VMT_INSTANCESIZE = -52
VMT_PARENT = -48

def u32(data, off):
    return struct.unpack_from("<I", data, off)[0]

def va_to_raw(pe, va):
    rva = va - pe.OPTIONAL_HEADER.ImageBase
    for s in pe.sections:
        span = max(s.Misc_VirtualSize, s.SizeOfRawData)
        if s.VirtualAddress <= rva < s.VirtualAddress + span:
            delta = rva - s.VirtualAddress
            if delta < s.SizeOfRawData:
                return s.PointerToRawData + delta
    return None

def raw_to_va(pe, raw):
    for s in pe.sections:
        if s.PointerToRawData <= raw < s.PointerToRawData + s.SizeOfRawData:
            return pe.OPTIONAL_HEADER.ImageBase + s.VirtualAddress + raw - s.PointerToRawData
    return None

def section_name(s):
    return s.Name.rstrip(b"\\0").decode("ascii", "replace")

def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-vmt-slots.md")
    blob = src.read_bytes()
    pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit:
        raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = hit
    _, names, modules, procedures = parse_td32(blob, base, end, directory)
    by_va = {}
    proc_ranges = []
    for p in procedures:
        if not (1 <= p["segment"] <= len(pe.sections)):
            continue
        sec = pe.sections[p["segment"] - 1]
        mod = modules.get(p["module"])
        seg = next((x for x in mod[1] if x[0] == p["segment"]), None) if mod else None
        if not seg:
            continue
        _, _, segbase, segsize = seg
        if segbase <= p["offset"] < segbase + segsize and p["offset"] < sec.SizeOfRawData:
            va = pe.OPTIONAL_HEADER.ImageBase + sec.VirtualAddress + p["offset"]
            by_va.setdefault(va, []).append(p["name"])
            proc_ranges.append((va, va + p["size"], p["name"]))

    lines = ["# Delphi VMT slot resolution", "",
             "- PE32 Delphi package; VMT slots are 32-bit method pointers.",
             "- Candidate discovery: Delphi 2009+ Win32 layout: class name at VMT-0x38, instance size at VMT-0x34, parent at VMT-0x30; self pointer at VMT-0x58.",
             "- Requested slot offsets are byte offsets from the VMT base.", ""]
    for cls in TARGET_CLASSES:
        needle = bytes([len(cls)]) + cls.encode("ascii")
        positions = []
        pos = 0
        while True:
            pos = blob.find(needle, pos)
            if pos < 0: break
            positions.append(pos)
            pos += 1
        lines += [f"## {cls}", "", f"- Class-name shortstring occurrences: {len(positions)}"]
        candidates = []
        for string_raw in positions:
            string_va = raw_to_va(pe, string_raw)
            if string_va is None: continue
            ptr_raw = struct.pack("<I", string_va)
            for sec in pe.sections:
                start = sec.PointerToRawData
                stop = start + sec.SizeOfRawData
                p = blob.find(ptr_raw, start, stop)
                while p >= 0:
                    vmt_va = raw_to_va(pe, p) - VMT_CLASSNAME
                    vmt_raw = va_to_raw(pe, vmt_va)
                    if vmt_raw is not None and vmt_raw + 4 <= len(blob):
                        self_raw = va_to_raw(pe, vmt_va + VMT_SELF)
                        inst_raw = va_to_raw(pe, vmt_va + VMT_INSTANCESIZE)
                        parent_raw = va_to_raw(pe, vmt_va + VMT_PARENT)
                        if self_raw is not None and inst_raw is not None and parent_raw is not None:
                            selfptr = u32(blob, self_raw)
                            instsize = u32(blob, inst_raw)
                            parent = u32(blob, parent_raw)
                            if selfptr == vmt_va and 0x20 <= instsize <= 0x10000 and (parent == 0 or va_to_raw(pe, parent) is not None):
                                candidates.append((vmt_va, vmt_raw, True, instsize, parent))
                    p = blob.find(ptr_raw, p + 1, stop)
        uniq = {}
        for c in candidates: uniq[c[0]] = c
        if not uniq:
            lines += ["", "No VMT candidate found through the class-name RTTI pointer.", ""]
            continue
        for vmt_va, vmt_raw, self_ok, instsize, parent in sorted(uniq.values()):
            lines += ["", f"### Candidate VMT 0x{vmt_va:08X}",
                      f"- Raw offset: 0x{vmt_raw:X}",
                      f"- Self pointer matches VMT: {'yes' if self_ok else 'no'}",
                      f"- Instance size: 0x{instsize:X}",
                      f"- Parent VMT: 0x{parent:08X}"]
            for slot in SLOTS:
                slot_raw = va_to_raw(pe, vmt_va + slot)
                if slot_raw is None or slot_raw + 4 > len(blob):
                    lines.append(f"- Slot +0x{slot:X}: outside mapped raw data")
                    continue
                target = u32(blob, slot_raw)
                target_raw = va_to_raw(pe, target)
                target_names = by_va.get(target, [])
                if not target_names:
                    target_names = [name for start, end, name in proc_ranges if start <= target < end]
                if target_raw is not None:
                    lines.append(f"- Slot +0x{slot:X}: 0x{target:08X}" +
                                 (f" — inside TD32 procedure: {', '.join(target_names)}" if target_names else " — executable/data section address; no TD32 procedure range match"))
                else:
                    lines.append(f"- Slot +0x{slot:X}: 0x{target:08X} — not mapped to PE section")
        lines.append("")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
