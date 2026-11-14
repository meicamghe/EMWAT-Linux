#!/usr/bin/env python3
"""List TD32 procedures whose decorated names mention selected Delphi classes."""
import pathlib, sys
import pefile
from analyze_emwat_td32 import find_td32, parse_td32

if len(sys.argv) < 3:
    raise SystemExit("usage: find_td32_class_procedures.py <pe-file> <class-substring> [more substrings...]")
path = pathlib.Path(sys.argv[1])
needles = [x.lower() for x in sys.argv[2:]]
blob = path.read_bytes()
pe = pefile.PE(data=blob, fast_load=False)
hit = find_td32(blob)
if not hit:
    raise SystemExit("TD32 debug signature not found")
base, end, directory, _ = hit
_, names, modules, procedures = parse_td32(blob, base, end, directory)
rows = []
for proc in procedures:
    name = proc["name"]
    if not any(n in name.lower() for n in needles):
        continue
    if not (1 <= proc["segment"] <= len(pe.sections)):
        continue
    sec = pe.sections[proc["segment"] - 1]
    if proc["offset"] >= sec.SizeOfRawData:
        continue
    va = pe.OPTIONAL_HEADER.ImageBase + sec.VirtualAddress + proc["offset"]
    module = modules.get(proc["module"])
    module_name = names[module[0]] if module and module[0] < len(names) else str(proc["module"])
    rows.append((module_name, name, va, proc["size"], proc["symbol"]))
print("# TD32 class procedure index")
print()
print(f"- Input: `{path}`")
print(f"- Matching procedures: {len(rows)}")
print()
print("| Module | Decorated procedure | VA | Size | Symbol |")
print("|---|---|---:|---:|---|")
for module, name, va, size, symbol in sorted(rows, key=lambda x: (x[0], x[2])):
    print(f"| {module} | `{name}` | `0x{va:08X}` | `0x{size:X}` | {symbol} |")
