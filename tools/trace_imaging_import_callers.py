#!/usr/bin/env python3
"""Map x86 PE code references to ImageGear/ImageEn imports.

This deliberately scans raw executable-section bytes for the canonical x86
forms (FF 25 absolute indirect JMP, E8 rel32 CALL, FF 15 absolute indirect
CALL). Linear disassembly can miss Delphi thunks when code/data or alignment
causes the decoder to lose instruction synchronization.
"""
import pathlib
import struct
import sys

import pefile


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "analysis-input/EmwatMethods.bpl1")
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "bpl-analysis/EmwatMethods-imaging-import-callers.md")
    pe = pefile.PE(data=src.read_bytes(), fast_load=False)
    base = pe.OPTIONAL_HEADER.ImageBase

    imports = {}
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("ascii", "replace")
        if "GEAR32PD" not in dll.upper() and "PKIECTRL23" not in dll.upper():
            continue
        for imp in entry.imports:
            if not imp.address:
                continue
            name = imp.name.decode("ascii", "replace") if imp.name else f"ordinal_{imp.ordinal}"
            imports[imp.address] = (dll, name)

    executable = []
    for sec in pe.sections:
        if sec.Characteristics & 0x20000000:
            executable.append((base + sec.VirtualAddress, sec.get_data()))

    # IAT slot -> imported symbol; thunk VA -> imported symbol.
    thunks = {}
    direct_iat = {slot: [] for slot in imports}
    call_xrefs = {}

    for start, code in executable:
        n = len(code)
        for i in range(max(0, n - 5)):
            va = start + i
            op = code[i]
            if op == 0xFF and code[i + 1] in (0x15, 0x25):
                slot = struct.unpack_from("<I", code, i + 2)[0]
                if slot not in imports:
                    continue
                if code[i + 1] == 0x25:
                    thunks[va] = imports[slot]
                else:
                    direct_iat[slot].append(va)
            elif op == 0xE8:
                rel = struct.unpack_from("<i", code, i + 1)[0]
                target = (va + 5 + rel) & 0xFFFFFFFF
                if target in thunks:
                    call_xrefs.setdefault(target, []).append(va)

    lines = [
        "# Imaging import call-site map", "",
        f"- Input: {src}",
        f"- ImageGear/ImageEn import slots: {len(imports)}",
        f"- Executable sections scanned: {len(executable)}",
        f"- Import thunks resolved (raw FF 25 patterns): {len(thunks)}",
        "- Detection method: raw x86 opcode scan; candidate references should be validated against disassembly.", "",
        "Call sites are static byte-pattern references; they do not prove runtime execution. Raw scans can include false positives, so verify candidate instructions in context.", "",
        "| DLL | Imported API | IAT slot | Thunk VA | Call-site VAs |",
        "|---|---|---:|---:|---|",
    ]
    for slot, (dll, name) in sorted(imports.items(), key=lambda x: (x[1][0].lower(), x[1][1].lower())):
        matches = [(addr, api) for addr, api in thunks.items() if api == (dll, name)]
        if matches:
            for thunk, api in matches:
                sites = call_xrefs.get(thunk, [])
                lines.append(f"| {dll} | {name} | 0x{slot:08X} | 0x{thunk:08X} | " +
                             (", ".join(f"0x{x:08X}" for x in sites) if sites else "—") + " |")
        else:
            sites = direct_iat.get(slot, [])
            lines.append(f"| {dll} | {name} | 0x{slot:08X} | — | " +
                         (", ".join(f"0x{x:08X}" for x in sites) if sites else "—") + " |")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out}: {len(imports)} imports, {len(thunks)} thunks, "
          f"{sum(map(len, direct_iat.values()))} direct IAT calls, "
          f"{sum(map(len, call_xrefs.values()))} thunk call references")


if __name__ == "__main__":
    main()
