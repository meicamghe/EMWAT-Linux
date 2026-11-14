#!/usr/bin/env python3
"""Enumerate Delphi TD32 methods related to abstract dispatch and XML conversion."""
import pathlib
import sys
import pefile
from analyze_emwat_td32 import find_td32, parse_td32

if len(sys.argv) < 2:
    raise SystemExit("usage: search_td32_word_methods.py <bpl-file> [output.md]")
src = pathlib.Path(sys.argv[1])
out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-word-dispatch-symbols.md")
blob = src.read_bytes()
hit = find_td32(blob)
if not hit:
    raise SystemExit("TD32 debug signature not found")
base, end, directory, _ = hit
_, names, modules, procedures = parse_td32(blob, base, end, directory)
pe = pefile.PE(data=blob, fast_load=False)

def module_name(mod):
    item = modules.get(mod)
    if not item:
        return f"<module-{mod}>"
    idx = item[0]
    return names[idx] if idx < len(names) else f"<name-{idx}>"

terms = ("paramstoxml", "performmethod", "temwmethod", "temwatmethod",
         "teditworddocument", "temwatinvokeparam", "editworddocument",
         "xmlwordconfig", "wordconfig", "twordfields", "twordfield",
         "get_fields", "set_fields", "wordxp@fields", "wordxp@field", "getdocfieldindex", "filltextfield", "fillimagefield", "fillmswfields", "addimagestodoc", "fillprintdocfields", "fillimgfldsforprint", "beforeclose", "documentbeforeclose", "onclose", "closemydoc", "close", "storyranges", "formfields", "formfield", "get_storyranges", "get_formfields")
selected = [p for p in procedures if any(t in p["name"].lower() for t in terms)]
lines = [
    "# EMWAT Delphi word-method and dispatch symbol inventory", "",
    f"- Input: `{src}`",
    f"- TD32 procedures: {len(procedures):,}",
    f"- Matching procedures: {len(selected)}",
    "- This is a symbol inventory; names and offsets alone do not prove runtime dispatch or override relationships.", "",
    "## Matching procedures", "",
    "| TD32 module | Module name | Symbol | Segment | Section offset | Mapped VA | Size |",
    "|---:|---|---|---:|---:|---:|---:|",
]
for p in sorted(selected, key=lambda x: (x["module"], x["name"].lower(), x["offset"])):
    section = pe.sections[p["segment"] - 1] if 1 <= p["segment"] <= len(pe.sections) else None
    module = modules.get(p["module"])
    seg = next((item for item in module[1] if item[0] == p["segment"]), None) if module else None
    valid = bool(section and seg and seg[2] <= p["offset"] and p["offset"] + p["size"] <= seg[2] + seg[3]
                 and p["offset"] + p["size"] <= section.SizeOfRawData)
    va = pe.OPTIONAL_HEADER.ImageBase + section.VirtualAddress + p["offset"] if valid else None
    va_text = f"0x{va:08X}" if va is not None else "unmapped"
    lines.append(f'| {p["module"]} | {module_name(p["module"])} | `{p["name"]}` | {p["segment"]} | 0x{p["offset"]:08X} | {va_text} | 0x{p["size"]:X} |')

lines += ["", "## TD32 module segment descriptors", "",
          "| Module | Module name | Segment | Flags | Segment base | Segment size |",
          "|---:|---|---:|---:|---:|---:|"]
for mid, (name_idx, segs) in sorted(modules.items()):
    mname = names[name_idx] if name_idx < len(names) else f"<name-{name_idx}>"
    if any(p["module"] == mid for p in selected):
        for seg, flags, off, size in segs:
            lines.append(f"| {mid} | {mname} | {seg} | 0x{flags:04X} | 0x{off:08X} | 0x{size:X} |")

lines += ["", "## Imported package/module names", ""]
dlls = sorted({entry.dll.decode("ascii", "replace") for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", [])})
for dll in dlls:
    lines.append(f"- `{dll}`")
lines += ["", "## Interpretation notes", "",
          "- A short procedure that jumps to Delphi RTL AbstractError is consistent with an abstract-method trap, but the symbol inventory alone cannot identify a concrete override.",
          "- A concrete override may have a different decorated name, be registered through a VMT, or reside in another package/module not present in this BPL.",
          "- Mapped VA is computed as PE ImageBase + section.VirtualAddress + TD32 section offset, and is emitted only when the procedure fits both its module segment descriptor and the PE section."]
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Wrote {out}; matched {len(selected)} procedures")
