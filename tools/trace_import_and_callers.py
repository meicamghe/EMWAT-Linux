#!/usr/bin/env python3
"""Resolve an absolute IAT slot and find direct x86 callers of selected VAs."""
import pathlib, sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

if len(sys.argv) < 3:
    raise SystemExit("usage: trace_import_and_callers.py <pe-file> <iat-va> [target-va ...]")
path = pathlib.Path(sys.argv[1])
iat_va = int(sys.argv[2], 0)
targets = [int(x, 0) for x in sys.argv[3:]]
pe = pefile.PE(str(path), fast_load=False)
base = pe.OPTIONAL_HEADER.ImageBase
imports = {}
for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
    dll = entry.dll.decode("ascii", "replace")
    for imp in entry.imports:
        name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
        imports[imp.address] = f"{dll}!{name}"

out = [
    "# EMWAT import-slot and direct-caller trace", "",
    f"- Input: `{path}`",
    f"- Image base: `0x{base:08X}`",
    f"- Requested IAT VA: `0x{iat_va:08X}`", "",
    "## Import slot lookup", ""
]
if iat_va in imports:
    out.append(f"- **Resolved:** `{imports[iat_va]}`")
else:
    out.append("- No import descriptor entry has this exact IAT address.")
    rva = iat_va - base
    for sec in pe.sections:
        lo, hi = sec.VirtualAddress, sec.VirtualAddress + max(sec.Misc_VirtualSize, sec.SizeOfRawData)
        if lo <= rva < hi:
            out.append(f"- Slot lies in section `{sec.Name.rstrip(bytes([0])).decode('ascii','replace')}` (RVA `0x{rva:08X}`).")
            break
    try:
        raw = pe.get_offset_from_rva(rva)
        value = int.from_bytes(path.read_bytes()[raw:raw+4], "little")
        out.append(f"- On-disk DWORD at slot: `0x{value:08X}` (may be unresolved/relocated).")
    except Exception as exc:
        out.append(f"- Could not read slot DWORD: {exc}")

out += ["", "## Direct CALL references", ""]
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True
hits = {t: [] for t in targets}
blob = path.read_bytes()
for sec in pe.sections:
    if not (sec.Characteristics & 0x20000000):
        continue
    code = sec.get_data()
    va = base + sec.VirtualAddress
    for ins in md.disasm(code, va):
        if ins.mnemonic != "call":
            continue
        for op in ins.operands:
            if op.type == 2 and op.imm in hits:
                hits[op.imm].append((ins.address, ins.op_str))
for target, callers in hits.items():
    out.append(f"### Target `0x{target:08X}`")
    if callers:
        out.extend(f"- Caller `0x{addr:08X}`: `call {operand}`" for addr, operand in callers)
    else:
        out.append("- No direct CALL references found in executable sections.")
    out.append("")
out += [
    "## Interpretation limits", "",
    "- Direct CALL scanning does not find virtual/interface dispatch, callbacks, computed jumps, or callers outside this PE module.",
    "- An IAT slot is identified only when its address exactly matches a parsed import thunk.",
]
dest = pathlib.Path("bpl-analysis/EmwatMethods-import-and-caller-trace.md")
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text("\n".join(out), encoding="utf-8")
print(f"Wrote {dest}")
