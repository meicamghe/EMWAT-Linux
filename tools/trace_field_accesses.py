#!/usr/bin/env python3
"""Find TD32-bounded x86 references to a selected object-field displacement."""
import pathlib, struct, sys
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, x86_const
from analyze_emwat_td32 import find_td32, parse_td32

def main():
    if len(sys.argv) < 3:
        raise SystemExit("usage: trace_field_accesses.py <pe-file> <offset-hex> [output.md]")
    src = pathlib.Path(sys.argv[1]); field = int(sys.argv[2], 0)
    out = pathlib.Path(sys.argv[3] if len(sys.argv) > 3 else "bpl-analysis/EmwatMethods-field-accesses.md")
    blob = src.read_bytes(); pe = pefile.PE(data=blob, fast_load=False)
    hit = find_td32(blob)
    if not hit: raise SystemExit("TD32 debug signature not found")
    base, end, directory, _ = hit
    _, _, modules, procedures = parse_td32(blob, base, end, directory)
    md = Cs(CS_ARCH_X86, CS_MODE_32); md.detail = True
    rows = []
    for p in procedures:
        if not (1 <= p['segment'] <= len(pe.sections)): continue
        sec = pe.sections[p['segment'] - 1]
        mod = modules.get(p['module'])
        seg = next((x for x in mod[1] if x[0] == p['segment']), None) if mod else None
        if not seg: continue
        _, _, segbase, segsize = seg
        if not (segbase <= p['offset'] < segbase + segsize): continue
        if p['offset'] >= sec.SizeOfRawData: continue
        size = min(p['size'], sec.SizeOfRawData - p['offset'])
        raw = sec.PointerToRawData + p['offset']
        va = pe.OPTIONAL_HEADER.ImageBase + sec.VirtualAddress + p['offset']
        for ins in md.disasm(blob[raw:raw+size], va):
            for i, op in enumerate(ins.operands):
                if op.type != x86_const.X86_OP_MEM or op.mem.disp != field: continue
                base_name = ins.reg_name(op.mem.base) if op.mem.base else 'none'
                index_name = ins.reg_name(op.mem.index) if op.mem.index else 'none'
                access = 'read/write' if ins.mnemonic in ('xchg', 'xadd', 'inc', 'dec', 'add', 'sub', 'and', 'or', 'xor', 'not', 'neg') and i == 0 else ('write' if i == 0 and ins.mnemonic.startswith(('mov', 'stos', 'pop')) else 'read/other')
                rows.append((p['name'], ins.address, ins.mnemonic, ins.op_str, base_name, index_name, access))
    lines = [f'# PE field-reference scan: displacement 0x{field:X}', '',
             '- References are restricted to TD32-bounded procedures and decoded x86 instructions.',
             '- A displacement match is a candidate object-field access; the base register is not assumed to be Self.',
             '', '| Procedure | VA | Instruction | Base | Index | Access |', '|---|---:|---|---|---|---|']
    for name, va, mnemonic, op_str, base_name, index_name, access in sorted(rows, key=lambda x:x[1]):
        lines.append(f'| `{name}` | `0x{va:08X}` | `{mnemonic} {op_str}` | `{base_name}` | `{index_name}` | {access} |')
    lines += ['', f'- Total displacement matches: {len(rows)}', '']
    out.parent.mkdir(parents=True, exist_ok=True); out.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {out} ({len(rows)} matches)')

if __name__ == '__main__': main()