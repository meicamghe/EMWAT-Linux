#!/usr/bin/env python3
"""Map Delphi TRegistry import thunks and direct call sites in a PE image."""
import pathlib
import re
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const

src = pathlib.Path("analysis-input/EmwatMethods.bpl1")
out = pathlib.Path("word-lifecycle-analysis/registry-api-call-sites.md")
blob = src.read_bytes()
pe = pefile.PE(data=blob, fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
imports = {}
for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
    dll = entry.dll.decode("ascii", "replace")
    for imp in entry.imports:
        if imp.address and imp.name:
            name = imp.name.decode("ascii", "replace")
            if "Registry" in name or "TRegistry" in name or any(x in name for x in ("RegOpenKey", "RegQueryValue")):
                imports[imp.address] = f"{dll}!{name}"

decoder = Cs(CS_ARCH_X86, CS_MODE_32)
decoder.detail = True
thunks = {}
sections = []
for sec in pe.sections:
    data = sec.get_data()
    if not data:
        continue
    start = base + sec.VirtualAddress
    sections.append((sec, start, data))
    if not (sec.Characteristics & 0x20000000):
        continue
    for ins in decoder.disasm(data, start):
        if ins.mnemonic == "jmp" and ins.operands and ins.operands[0].type == x86_const.X86_OP_MEM:
            mem = ins.operands[0].mem
            if mem.base == 0 and mem.index == 0 and mem.disp in imports:
                thunks[ins.address] = imports[mem.disp]

# Scan executable sections for direct calls/jumps to those import thunks.
hits = []
for sec, start, data in sections:
    if not (sec.Characteristics & 0x20000000):
        continue
    insns = list(decoder.disasm(data, start))
    for i, ins in enumerate(insns):
        if ins.mnemonic not in ("call", "jmp") or not ins.operands:
            continue
        op = ins.operands[0]
        if op.type != x86_const.X86_OP_IMM or op.imm not in thunks:
            continue
        lo, hi = max(0, i-5), min(len(insns), i+7)
        context = "\n".join(f"  {x.address:08X}  {x.mnemonic:<8} {x.op_str}" for x in insns[lo:hi])
        hits.append((ins.address, thunks[op.imm], context))

lines = ["# Delphi registry API import and call-site scan", "",
         f"- Input: `{src}`",
         "- Imports are selected by registry-related symbol names; call sites are direct CALL/JMP targets to import thunks.",
         "- Indirect calls and wrapper functions not represented by direct thunk references may be missed.", "",
         "## Registry-related imports", ""]
for va, name in sorted(imports.items()):
    lines.append(f"- `0x{va:08X}` — `{name}`")
lines += ["", "## Executable thunk addresses", ""]
for va, name in sorted(thunks.items()):
    lines.append(f"- `0x{va:08X}` → `{name}`")
lines += ["", "## Direct call sites", ""]
for va, name, context in sorted(hits):
    lines += [f"### `0x{va:08X}` → `{name}`", "", "```asm", context, "```", ""]
lines += [f"- Total direct call sites: {len(hits)}", ""]
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out}; registry imports={len(imports)}; thunk addresses={len(thunks)}; call sites={len(hits)}")
