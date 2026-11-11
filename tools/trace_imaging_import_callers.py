#!/usr/bin/env python3
"""Map code call sites to ImageGear/ImageEn imports in a Delphi PE/BPL."""
import pathlib
import re
import sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "analysis-input/EmwatMethods.bpl1")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-imaging-import-callers.md")
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
            if "GEAR32PD" in dll.upper() or "PKIECTRL23" in dll.upper():
                imports[imp.address] = (dll, name)

    md = Cs(CS_ARCH_X86, CS_MODE_32)
    thunks = {}
    executable = []
    for sec in pe.sections:
        if not (sec.Characteristics & 0x20000000):
            continue
        start = base + sec.VirtualAddress
        code = sec.get_data()
        executable.append((start, code))
        for ins in md.disasm(code, start):
            if ins.mnemonic != "jmp":
                continue
            m = re.search(r"\[(0x[0-9a-fA-F]+)\]", ins.op_str)
            if m:
                slot = int(m.group(1), 16)
                if slot in imports:
                    thunks[ins.address] = imports[slot]

    callers = {addr: [] for addr in thunks}
    direct_iat = {addr: [] for addr in imports}
    for start, code in executable:
        for ins in md.disasm(code, start):
            if ins.mnemonic != "call":
                continue
            operand = ins.op_str.strip()
            m = re.fullmatch(r"(?:0x)?([0-9a-fA-F]{6,8})", operand)
            if m:
                target = int(m.group(1), 16) & 0xFFFFFFFF
                if target in callers:
                    callers[target].append(ins.address)
            m = re.search(r"\[(0x[0-9a-fA-F]+)\]", operand)
            if m:
                slot = int(m.group(1), 16)
                if slot in direct_iat:
                    direct_iat[slot].append(ins.address)

    lines = [
        "# Imaging import call-site map", "",
        f"- Input: {src}",
        f"- ImageGear/ImageEn import slots: {len(imports)}",
        f"- Import thunks resolved: {len(thunks)}", "",
        "Call sites are static x86 references; they do not prove runtime execution.", "",
        "| DLL | Imported API | IAT slot | Thunk VA | Call-site VAs |",
        "|---|---|---:|---:|---|",
    ]
    for slot, (dll, name) in sorted(imports.items(), key=lambda x: (x[1][0].lower(), x[1][1].lower())):
        thunk_list = [(addr, api) for addr, api in thunks.items() if api == (dll, name)]
        if thunk_list:
            for thunk, api in thunk_list:
                sites = callers.get(thunk, [])
                lines.append(f"| {dll} | {name} | 0x{slot:08X} | 0x{thunk:08X} | " + (", ".join(f"0x{x:08X}" for x in sites) if sites else "—") + " |")
        else:
            sites = direct_iat.get(slot, [])
            lines.append(f"| {dll} | {name} | 0x{slot:08X} | — | " + (", ".join(f"0x{x:08X}" for x in sites) if sites else "—") + " |")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}: {len(imports)} imports, {len(thunks)} thunks")

if __name__ == "__main__":
    main()
