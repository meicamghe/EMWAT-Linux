#!/usr/bin/env python3
"""Extract only EmwatAgent.exe from the repository's installer archive for CI analysis."""
import pathlib
import sys
import zipfile

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: extract_emwat_agent.py <installer-archive.zip> <output-exe>")
    archive = pathlib.Path(sys.argv[1])
    output = pathlib.Path(sys.argv[2])
    member = "EmwatAgent.exe"
    if not archive.is_file():
        raise SystemExit(f"installer archive not found: {archive}")
    with zipfile.ZipFile(archive) as zf:
        matches = [name for name in zf.namelist() if name.replace("\\\\", "/").lower() == member.lower()]
        if len(matches) != 1:
            raise SystemExit(f"expected exactly one {member} in archive; found {matches}")
        data = zf.read(matches[0])
    if len(data) < 2 or data[:2] != b"MZ":
        raise SystemExit("extracted EmwatAgent.exe does not have a PE MZ signature")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    print(f"Extracted {member}: {len(data):,} bytes to {output}")

if __name__ == "__main__":
    main()
