import re, struct, json, pathlib
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

src = pathlib.Path("analysis-input/EmwatMethods.bpl1")
data = src.read_bytes()
pe = pefile.PE(data=data, fast_load=False)
out = []
def emit(s=""): out.append(str(s))
emit("# EMWAT Methods BPL static analysis")
emit(f"- File: {src}")
emit(f"- Size: {len(data):,} bytes")
emit(f"- Machine: 0x{pe.FILE_HEADER.Machine:04X}")
emit(f"- ImageBase: 0x{pe.OPTIONAL_HEADER.ImageBase:08X}")
emit(f"- EntryPoint RVA: 0x{pe.OPTIONAL_HEADER.AddressOfEntryPoint:08X}")
emit("\n## Sections")
for sec in pe.sections:
    emit(f"- {sec.Name.rstrip(bytes([0])).decode(errors='replace')}: RVA=0x{sec.VirtualAddress:08X}, VA=0x{pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress:08X}, raw={sec.SizeOfRawData:,}, virtual={sec.Misc_VirtualSize:,}, flags=0x{sec.Characteristics:08X}")
emit("\n## Imports")
for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
    emit(f"### {entry.dll.decode(errors='replace')}")
    for imp in entry.imports:
        emit(f"- {imp.name.decode(errors='replace') if imp.name else 'ordinal '+str(imp.ordinal)}")
emit("\n## Relevant strings and code references")
patterns = re.compile(rb"(?i)(image|scan|twain|wia|rotate|crop|flip|paint|register|simpleimage|gscan|imag[e]?en|tiff|jpeg|undo|redo|print|page|command)")
strings = []
for enc, pat in [("ascii", rb"[\x20-\x7e]{5,}"), ("utf16le", rb"(?:[\x20-\x7e]\x00){5,}")]:
    for m in re.finditer(pat, data):
        raw = m.group(0)
        try: val = raw.decode("ascii" if enc=="ascii" else "utf-16le")
        except: continue
        if patterns.search(raw):
            strings.append((m.start(), val, enc))
seen=set()
for off,val,enc in strings:
    if (off,val) in seen: continue
    seen.add((off,val))
    emit(f"- file+0x{off:X} [{enc}] {val[:220]}")
# x86 disassembly of executable sections, collect instructions that reference relevant string VAs
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
str_targets = {}
for off,val,enc in strings:
    try:
        rva = pe.get_rva_from_offset(off)
        str_targets[pe.OPTIONAL_HEADER.ImageBase+rva] = (off,val)
    except: pass
emit("\n## Direct x86 references to relevant strings")
refs=0
for sec in pe.sections:
    if not (sec.Characteristics & 0x20000000): continue
    code=sec.get_data()
    base=pe.OPTIONAL_HEADER.ImageBase+sec.VirtualAddress
    for ins in md.disasm(code, base):
        for op in ins.operands:
            if op.type == 2 and op.imm in str_targets:
                off,val=str_targets[op.imm]
                emit(f"- VA 0x{ins.address:08X}: {ins.mnemonic} {ins.op_str} -> file+0x{off:X}: {val[:160]}")
                refs+=1
                if refs>=5000: break
        if refs>=5000: break
    if refs>=5000: break
emit(f"\nTotal direct refs recorded: {refs}")
pathlib.Path("bpl-analysis").mkdir(exist_ok=True)
pathlib.Path("bpl-analysis/EmwatMethods-static-analysis.md").write_text("\n".join(out),encoding="utf-8")
print(f"Generated report: {len(out)} lines; {refs} direct references")
