#!/usr/bin/env python3
"""Extract printable strings from one named PE resource (useful for Delphi DFM event bindings)."""
import hashlib
import pathlib
import re
import sys

import pefile


def entry_name(entry):
    if getattr(entry, "name", None) is not None:
        try:
            return entry.name.string.decode("utf-8", "replace")
        except Exception:
            return str(entry.name)
    return str(getattr(entry, "id", "?"))


def main():
    if len(sys.argv) < 4:
        raise SystemExit("usage: scan_named_pe_resource.py <pe-file> <resource-name> <output.md>")
    src = pathlib.Path(sys.argv[1])
    wanted = sys.argv[2].casefold()
    out = pathlib.Path(sys.argv[3])
    pe = pefile.PE(str(src), fast_load=False)
    matches = []
    resource_root = getattr(pe, "DIRECTORY_ENTRY_RESOURCE", None)
    if resource_root is None:
        raise SystemExit("PE has no resource directory")
    for type_entry in resource_root.entries:
        type_id = getattr(type_entry, "id", None)
        if type_id != 10 or not hasattr(type_entry, "directory"):
            continue
        for name_entry in type_entry.directory.entries:
            name = entry_name(name_entry)
            if (wanted != "*" and name.casefold() != wanted) or not hasattr(name_entry, "directory"):
                continue
            for lang_entry in name_entry.directory.entries:
                if not hasattr(lang_entry, "data"):
                    continue
                rsrc = lang_entry.data.struct
                blob = pe.get_data(rsrc.OffsetToData, rsrc.Size)
                matches.append((type_id, name, getattr(lang_entry, "id", "?"), blob))

    lines = [
        "# Named PE resource string scan",
        "",
        f"- Input: `{src}`",
        f"- Requested resource: `{sys.argv[2]}`",
        f"- Resource instances found: {len(matches)}",
        "",
    ]
    for idx, (type_id, name, lang, blob) in enumerate(matches, 1):
        lines += [
            f"## Resource instance {idx}",
            "",
            f"- Type ID: `{type_id}`",
            f"- Name: `{name}`",
            f"- Language ID: `{lang}`",
            f"- Size: {len(blob)} bytes",
            f"- SHA256: `{hashlib.sha256(blob).hexdigest()}`",
            f"- First 32 bytes: `{blob[:32].hex(' ')}`",
            "",
            "### Printable strings (ASCII / UTF-16LE)",
            "",
        ]
        found = set()
        patterns = [
            ("ASCII", re.compile(rb"[ -~]{4,}")),
            ("UTF-16LE", re.compile(rb"(?:[ -~]\x00){4,}")),
        ]
        for encoding, rx in patterns:
            for m in rx.finditer(blob):
                raw = m.group(0)
                try:
                    value = raw.decode("ascii" if encoding == "ASCII" else "utf-16le", "replace")
                except Exception:
                    continue
                value = value.strip()
                if len(value) < 4 or (encoding, value) in found:
                    continue
                found.add((encoding, value))
                if any(k in value.casefold() for k in (
                    "close", "before", "wordapp", "document", "autosave",
                    "save", "onclose", "oncreate", "onshow", "onclick", "onbefore",
                    "application", "event", "sendlog", "wordconfig", "editworddocument",
                    "invoke", "localhost", "127.0.0.1", "1984"
                )):
                    lo = max(0, m.start() - 24)
                    hi = min(len(blob), m.end() + 32)
                    lines.append(f"- `0x{m.start():04X}` {encoding}: `{value}`")
                    lines.append(f"  - Context bytes: `{blob[lo:hi].hex(' ')}`")
        lines.append("")
    if not matches:
        lines.append("No matching named resource found.")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out}; resource instances={len(matches)}")


if __name__ == "__main__":
    main()
