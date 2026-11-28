#!/usr/bin/env python3
"""Build validated TD32 and combined Ghidra function seeds for the EMWAT BPL."""

from __future__ import annotations

import argparse
import hashlib
import re
from collections import defaultdict
from pathlib import Path

import pefile

from analyze_emwat_td32 import find_td32, parse_td32


def safe_label(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]", "_", name)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if len(cleaned) > 180:
        suffix = hashlib.sha1(name.encode("utf-8", "replace")).hexdigest()[:10]
        cleaned = cleaned[:165] + "_" + suffix
    return "td32_" + (cleaned or "unnamed")


def read_seed_file(path: Path) -> dict[int, set[str]]:
    result: dict[int, set[str]] = defaultdict(set)
    if not path.exists():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        try:
            address = int(parts[0], 0)
        except ValueError:
            continue
        if parts[1] == "function" and parts[2]:
            result[address].add(parts[2])
    return result


def write_seed_file(path: Path, entries: dict[int, str], header: str) -> None:
    lines = [f"# {header}: address<TAB>kind<TAB>name"]
    lines.extend(f"0x{address:08X}\tfunction\t{name}" for address, name in sorted(entries.items()))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("rtti_seeds", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    blob = args.input.read_bytes()
    sha256 = hashlib.sha256(blob).hexdigest()
    summary_path = args.output_dir / "td32-seed-summary.md"
    td32_path = args.output_dir / "rea-td32-seeds.tsv"
    combined_path = args.output_dir / "rea-combined-seeds.tsv"
    index_path = args.output_dir / "td32-wordviewer-procedure-index.md"

    hit = find_td32(blob)
    if not hit:
        summary_path.write_text(
            f"# TD32 seed generation\n\n- Input SHA-256: `{sha256}`\n- Result: no TD32 stream found.\n",
            encoding="utf-8",
        )
        write_seed_file(td32_path, {}, "No TD32 seeds")
        write_seed_file(combined_path, {}, "No combined seeds")
        return 2

    base, end, directory_offset, signature = hit
    entries, names, modules, procedures = parse_td32(blob, base, end, directory_offset)
    pe = pefile.PE(data=blob, fast_load=True)
    image_base = pe.OPTIONAL_HEADER.ImageBase

    candidates: dict[int, set[str]] = defaultdict(set)
    relevant_rows: list[tuple[int, int, str, str]] = []
    rejected = defaultdict(int)

    for procedure in procedures:
        segment_id = int(procedure.get("segment", 0))
        code_offset = int(procedure.get("offset", -1))
        code_size = int(procedure.get("size", 0))
        original_name = str(procedure.get("name", "")).strip()
        module_id = int(procedure.get("module", -1))

        if not original_name:
            rejected["unnamed"] += 1
            continue
        if segment_id < 1 or segment_id > len(pe.sections):
            rejected["invalid_segment"] += 1
            continue
        section = pe.sections[segment_id - 1]
        if not (int(section.Characteristics) & 0x20000000):
            rejected["non_executable_section"] += 1
            continue
        if code_offset < 0 or code_size <= 0 or code_offset + code_size > int(section.SizeOfRawData):
            rejected["invalid_code_range"] += 1
            continue

        address = int(image_base + section.VirtualAddress + code_offset)
        label = safe_label(original_name)
        candidates[address].add(label)

        module_name = "<unknown>"
        module = modules.get(module_id)
        if module and 0 <= int(module[0]) < len(names):
            module_name = str(names[int(module[0])])
        if any(token.lower() in original_name.lower() for token in (
            "TWordViwer", "TWordDocument", "TWordApplication", "TScanCommand"
        )):
            relevant_rows.append((address, code_size, module_name, original_name))

    td32_entries: dict[int, str] = {}
    ambiguous_td32 = 0
    for address, labels in candidates.items():
        if len(labels) == 1:
            td32_entries[address] = next(iter(labels))
        else:
            ambiguous_td32 += 1
    write_seed_file(td32_path, td32_entries, "TD32-derived Ghidra seeds")

    rtti = read_seed_file(args.rtti_seeds)
    combined: dict[int, str] = {}
    ambiguous_combined = 0
    for address in sorted(set(rtti) | set(candidates)):
        td32_labels = candidates.get(address, set())
        rtti_labels = rtti.get(address, set())
        if len(td32_labels) == 1:
            combined[address] = next(iter(td32_labels))
        elif len(rtti_labels) == 1:
            combined[address] = next(iter(rtti_labels))
        elif td32_labels or rtti_labels:
            ambiguous_combined += 1
    # Make symbol names unique without changing their address identity.
    by_label: dict[str, list[int]] = defaultdict(list)
    for address, label in combined.items():
        by_label[label].append(address)
    for label, addresses in by_label.items():
        if len(addresses) > 1:
            for address in addresses:
                combined[address] = f"{label}_{address:08X}"
    write_seed_file(combined_path, combined, "Combined TD32 and undelphi Ghidra seeds")

    relevant_rows.sort()
    index_lines = [
        "# TD32 procedure index — Word/scan classes",
        "",
        "| VA | Size | Module | TD32 procedure |",
        "|---:|---:|---|---|",
    ]
    for address, size, module_name, name in relevant_rows:
        escaped = name.replace("|", "\\|")
        index_lines.append(f"| `0x{address:08X}` | `0x{size:X}` | {module_name} | `{escaped}` |")
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")

    summary = [
        "# TD32 and combined Ghidra seed summary",
        "",
        f"- Input: `{args.input}`",
        f"- Input SHA-256: `{sha256}`",
        f"- TD32 signature: `{signature!r}`",
        f"- TD32 directory entries: {len(entries)}",
        f"- TD32 procedures parsed: {len(procedures)}",
        f"- Valid executable procedure addresses: {len(candidates)}",
        f"- Unique TD32 seeds emitted: {len(td32_entries)}",
        f"- Ambiguous TD32 addresses omitted from TD32-only file: {ambiguous_td32}",
        f"- undelphi RTTI seed addresses: {len(rtti)}",
        f"- Combined unique addresses emitted: {len(combined)}",
        f"- Ambiguous combined addresses omitted: {ambiguous_combined}",
        f"- Relevant Word/scan procedure rows: {len(relevant_rows)}",
        "",
        "## Rejected TD32 records",
        "",
    ]
    summary.extend(f"- {reason}: {count}" for reason, count in sorted(rejected.items()))
    summary.extend([
        "",
        "TD32 labels are preserved in a sanitized form with a `td32_` prefix. Combined seeds prefer a unique TD32 label at an address and fall back to a unique undelphi RTTI label. Ambiguous aliases are omitted rather than guessed.",
        "",
        "The seed files are static-analysis inputs for REA/Ghidra; they are not runtime dependencies.",
    ])
    summary_path.write_text("\n".join(summary) + "\n", encoding="utf-8")

    print(
        f"TD32 procedures={len(procedures)} executable-addresses={len(candidates)} "
        f"TD32-seeds={len(td32_entries)} RTTI-seeds={len(rtti)} combined={len(combined)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
