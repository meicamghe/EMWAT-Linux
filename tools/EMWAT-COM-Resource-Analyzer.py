#!/usr/bin/env python3
# EMWAT COM / ProgID / PE Resource analyzer
# Usage: py -m pip install --user pefile
#        py D:\EMWAT-COM-Resource-Analyzer.py
from pathlib import Path
import re
import hashlib

ROOT = Path(r"D:\EmwatInstaller")
REPORT = Path(r"D:\EMWAT-COM-Resource-Report.txt")
RESOURCE_DIR = Path(r"D:\EMWAT-Resources")

GUID_RE = re.compile(
    r"(?i)\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b"
)
PROGID_RE = re.compile(
    r"(?i)\b[A-Z][A-Z0-9_]{1,30}\."
    r"(?:Application|Document|Workbook|Worksheet|Sheet|Browser|WebBrowser|"
    r"HTMLDocument|Explorer|[A-Z][A-Z0-9_]{1,20}\.\d+)\b"
)
KEYWORDS = re.compile(
    r"(?i)CLSID|ProgID|Word\.Application|Excel\.Application|"
    r"Outlook\.Application|InternetExplorer\.Application|Shell\.Explorer|"
    r"WebBrowser|IWebBrowser|SHDocVw|MSHTML|HTMLDocument|"
    r"TWord|TExcel|TOleServer|OfficeXP|OfficeDataSourceObject|"
    r"Emwat|\.mdb|\.accdb|\.sqlite|\.fdb|\.gdb"
)

RESOURCE_TYPES = {
    1: "CURSOR", 2: "BITMAP", 3: "ICON", 4: "MENU", 5: "DIALOG",
    6: "STRING", 7: "FONTDIR", 8: "FONT", 9: "ACCELERATOR",
    10: "RCDATA", 11: "MESSAGETABLE", 12: "GROUP_CURSOR",
    14: "GROUP_ICON", 16: "VERSION", 17: "DLGINCLUDE",
    19: "PLUGPLAY", 20: "VXD", 21: "ANICURSOR", 22: "ANIICON",
    23: "HTML", 24: "MANIFEST"
}

def entry_name(entry):
    if getattr(entry, "name", None) is not None:
        try:
            return str(entry.name.string, "utf-8", errors="replace")
        except Exception:
            return str(entry.name)
    return str(getattr(entry, "id", "?"))

def strings_from_bytes(data):
    found = []
    try:
        text = data.decode("latin-1", errors="ignore")
        found.extend(re.findall(r"[\x20-\x7e]{5,}", text))
    except Exception:
        pass
    try:
        text = data.decode("utf-16le", errors="ignore")
        found.extend(re.findall(r"[\x20-\x7e]{5,}", text))
    except Exception:
        pass
    return list(dict.fromkeys(found))

def scan_text(label, text, output):
    seen = set()
    for rx, kind in ((GUID_RE, "GUID"), (PROGID_RE, "ProgID")):
        for match in rx.finditer(text):
            value = match.group(0)
            key = (kind, value.lower())
            if key in seen:
                continue
            seen.add(key)
            start = max(0, match.start() - 90)
            end = min(len(text), match.end() + 90)
            context = text[start:end].replace("\r", " ").replace("\n", " ")
            output.append(f"  [{kind}] {value} | context: {context}")
    keyword_hits = []
    for line in text.splitlines():
        if KEYWORDS.search(line):
            line = line.strip()
            if line and line not in keyword_hits:
                keyword_hits.append(line)
    for line in keyword_hits[:300]:
        output.append(f"  [STRING] {line}")

def main():
    output = [
        "EMWAT COM / ProgID / PE Resource Analysis",
        f"Root: {ROOT}",
        "Static analysis only; no executable was launched.",
        "Review this report for private paths, tokens, customer data before upload.",
        ""
    ]
    if not ROOT.exists():
        raise SystemExit(f"Input folder not found: {ROOT}")

    files = [p for p in ROOT.rglob("*") if p.is_file()]
    output.append(f"Files discovered: {len(files)}")

    try:
        import pefile
    except ImportError:
        pefile = None
        output.append("WARNING: pefile is not installed; PE resource extraction skipped.")

    RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

    for path in sorted(files):
        try:
            size = path.stat().st_size
            if size > 250 * 1024 * 1024:
                output.append(f"\n[SKIPPED oversized] {path} ({size} bytes)")
                continue
            data = path.read_bytes()
        except Exception as exc:
            output.append(f"\n[READ ERROR] {path}: {exc}")
            continue

        rel = path.relative_to(ROOT)
        output.append(f"\n{'=' * 72}\nFILE: {rel}\nSIZE: {len(data)}\nSHA256: {hashlib.sha256(data).hexdigest()}")

        combined = "\n".join(strings_from_bytes(data))
        scan_text(str(rel), combined, output)

        if pefile is None:
            continue
        try:
            pe = pefile.PE(data=data, fast_load=False)
            if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
                output.append("  [RESOURCES] none")
                continue

            resource_count = 0
            for type_entry in pe.DIRECTORY_ENTRY_RESOURCE.entries:
                type_id = getattr(type_entry, "id", None)
                type_label = RESOURCE_TYPES.get(type_id, entry_name(type_entry))
                if not hasattr(type_entry, "directory"):
                    continue
                for name_entry in type_entry.directory.entries:
                    resource_name = entry_name(name_entry)
                    if not hasattr(name_entry, "directory"):
                        continue
                    for lang_entry in name_entry.directory.entries:
                        if not hasattr(lang_entry, "data"):
                            continue
                        rsrc = lang_entry.data.struct
                        blob = pe.get_data(rsrc.OffsetToData, rsrc.Size)
                        resource_count += 1
                        output.append(
                            f"  [RESOURCE] type={type_label} name={resource_name} "
                            f"lang={getattr(lang_entry, 'id', '?')} "
                            f"size={len(blob)} rva=0x{rsrc.OffsetToData:x}"
                        )
                        safe_type = re.sub(r"[^A-Za-z0-9_.-]", "_", str(type_label))
                        safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", str(resource_name))
                        out_dir = RESOURCE_DIR / path.name
                        out_dir.mkdir(parents=True, exist_ok=True)
                        out_file = out_dir / f"{safe_type}_{safe_name}_{resource_count}.bin"
                        out_file.write_bytes(blob)

                        # Scan textual content embedded in each resource.
                        resource_text = "\n".join(strings_from_bytes(blob))
                        if resource_text.strip():
                            scan_text(f"{rel}::{safe_type}/{safe_name}", resource_text, output)

            output.append(f"  [RESOURCE TOTAL] {resource_count}")
            pe.close()
        except Exception as exc:
            output.append(f"  [PE PARSE] not a PE or parse error: {exc}")

    REPORT.write_text("\n".join(output), encoding="utf-8")
    print(f"Report created: {REPORT}")
    print(f"Resource extraction folder: {RESOURCE_DIR}")
    print(f"Report size: {REPORT.stat().st_size:,} bytes")
    print("Do not upload extracted resource binaries; inspect them locally first.")

if __name__ == "__main__":
    main()
