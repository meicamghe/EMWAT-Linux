#!/usr/bin/env python3
"""Map registry-related PE imports, IAT-indirect calls, and direct thunk calls."""
import pathlib
import struct
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
        if not imp.address:
            continue
        name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
        if any(x.lower() in name.lower() for x in ("Registry", "TRegistry", "RegOpenKey", "RegQueryValue", "RegSetValue", "RegCloseKey")):
            imports[imp.address] = f"{dll}!{name}"

decoder = Cs(CS_ARCH_X86, CS_MODE_32)
decoder.detail = True
sections = []
thunks = {}
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

hits = []
for sec, start, data in sections:
    if not (sec.Characteristics & 0x20000000):
        continue
    insns = list(decoder.disasm(data, start))
    for i, ins in enumerate(insns):
        if ins.mnemonic not in ("call", "jmp") or not ins.operands:
            continue
        op = ins.operands[0]
        target = None
        kind = None
        if op.type == x86_const.X86_OP_IMM and op.imm in thunks:
            target, kind = thunks[op.imm], "direct thunk"
        elif op.type == x86_const.X86_OP_MEM:
            mem = op.mem
            if mem.base == 0 and mem.index == 0 and mem.disp in imports:
                target, kind = imports[mem.disp], "indirect through IAT"
        if target:
            lo, hi = max(0, i - 7), min(len(insns), i + 9)
            context = "\n".join(f"  {x.address:08X}  {x.mnemonic:<8} {x.op_str}" for x in insns[lo:hi])
            hits.append((ins.address, kind, target, context))

# Also list raw pointer references to registry IAT slots, including non-code/data references.
pointer_refs = []
for va, name in sorted(imports.items()):
    needle = struct.pack("<I", va)
    pos = 0
    while True:
        pos = blob.find(needle, pos)
        if pos < 0:
            break
        try:
            ref_va = pe.get_rva_from_offset(pos) + base
        except Exception:
            ref_va = None
        if ref_va is not None:
            pointer_refs.append((ref_va, va, name))
        pos += 1

lines = [
    "# Delphi registry API import and call-site scan", "",
    f"- Input: `{src}`",
    "- Scans direct calls to import thunks and x86 indirect CALL/JMP instructions whose absolute memory operand is a registry-related IAT slot.",
    "- Raw pointer-reference hits are listed separately; they are not proof of execution.",
    "- Register-based indirect calls, dynamically resolved APIs, and external modules may remain unresolved.", "",
    "## Registry-related imports", ""
]
for va, name in sorted(imports.items()):
    lines.append(f"- `0x{va:08X}` — `{name}`")
lines += ["", "## Executable thunk addresses", ""]
for va, name in sorted(thunks.items()):
    lines.append(f"- `0x{va:08X}` → `{name}`")
lines += ["", "## Direct and IAT-indirect call sites", ""]
for va, kind, name, context in sorted(hits):
    lines += [f"### `0x{va:08X}` — {kind} → `{name}`", "", "```asm", context, "```", ""]
lines += [f"- Total call sites: {len(hits)}", "", "## Raw pointer references to IAT slots", ""]
for ref_va, target_va, name in pointer_refs:
    lines.append(f"- `0x{ref_va:08X}` contains pointer to IAT `0x{target_va:08X}` — `{name}`")
lines += [f"- Total raw pointer references: {len(pointer_refs)}", ""]
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {out}; registry imports={len(imports)}; thunks={len(thunks)}; call sites={len(hits)}; pointer refs={len(pointer_refs)}")
