#!/usr/bin/env python3
"""Inventory packaged Office templates without exposing document contents."""
from __future__ import annotations

import argparse
from collections import Counter
from io import BytesIO
from pathlib import PurePosixPath
import zipfile
import xml.etree.ElementTree as ET


WORD_EXTENSIONS = {".doc", ".docx", ".dot", ".dotx", ".dotm", ".rtf"}
OOXML_EXTENSIONS = {".docx", ".dotx", ".dotm"}
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def inspect_ooxml(data: bytes) -> dict[str, object]:
    result: dict[str, object] = {
        "bookmark_names": [],
        "content_control_tags": [],
        "content_control_aliases": [],
        "field_instruction_count": 0,
        "paragraph_count": 0,
        "table_count": 0,
        "drawing_count": 0,
        "header_footer_parts": 0,
        "image_parts": 0,
        "styles_present": False,
    }
    try:
        with zipfile.ZipFile(BytesIO(data)) as package:
            names = package.namelist()
            result["header_footer_parts"] = sum(
                1 for name in names
                if name.startswith("word/header") or name.startswith("word/footer")
            )
            result["image_parts"] = sum(
                1 for name in names if name.startswith("word/media/")
            )
            result["styles_present"] = "word/styles.xml" in names
            xml_name = "word/document.xml"
            if xml_name not in names:
                return result
            root = ET.fromstring(package.read(xml_name))
            result["bookmark_names"] = sorted({
                node.attrib.get(f"{{{WORD_NS['w']}}}name", "")
                for node in root.findall(".//w:bookmarkStart", WORD_NS)
                if node.attrib.get(f"{{{WORD_NS['w']}}}name")
            })
            result["content_control_tags"] = sorted({
                node.attrib.get(f"{{{WORD_NS['w']}}}val", "")
                for node in root.findall(".//w:sdtPr/w:tag", WORD_NS)
                if node.attrib.get(f"{{{WORD_NS['w']}}}val")
            })
            result["content_control_aliases"] = sorted({
                node.attrib.get(f"{{{WORD_NS['w']}}}val", "")
                for node in root.findall(".//w:sdtPr/w:alias", WORD_NS)
                if node.attrib.get(f"{{{WORD_NS['w']}}}val")
            })
            result["field_instruction_count"] = len(root.findall(".//w:instrText", WORD_NS))
            result["paragraph_count"] = len(root.findall(".//w:p", WORD_NS))
            result["table_count"] = len(root.findall(".//w:tbl", WORD_NS))
            result["drawing_count"] = len(root.findall(".//w:drawing", WORD_NS))
    except (zipfile.BadZipFile, ET.ParseError, KeyError):
        result["ooxml_parse_error"] = True
    return result


def inspect_archive(path: str) -> str:
    rows: list[dict[str, object]] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            suffix = PurePosixPath(info.filename).suffix.lower()
            if suffix not in WORD_EXTENSIONS or info.is_dir():
                continue
            if info.file_size > 100 * 1024 * 1024:
                rows.append({
                    "path": info.filename,
                    "size": info.file_size,
                    "note": "skipped: entry exceeds 100 MiB inspection limit",
                })
                continue
            data = archive.read(info)
            row: dict[str, object] = {
                "path": info.filename,
                "extension": suffix,
                "size": info.file_size,
                "compressed_size": info.compress_size,
                "signature": data[:8].hex(),
            }
            if suffix in OOXML_EXTENSIONS:
                row.update(inspect_ooxml(data))
            rows.append(row)

    lines = [
        "# Packaged Word asset inventory",
        "",
        f"Archive: {path}",
        f"Word-family assets found: {len(rows)}",
        "",
        "No document text, field values, images, or embedded binary payloads are included.",
        "",
    ]
    if not rows:
        lines.append("No Word-family documents or templates were found.")
        return "\n".join(lines) + "\n"

    for index, row in enumerate(rows, 1):
        lines.extend([
            f"## {index}. {row['path']}",
            f"- Extension: {row.get('extension', 'unknown')}",
            f"- Size: {row['size']} bytes",
            f"- ZIP compressed size: {row.get('compressed_size', 'n/a')}",
            f"- Signature: {row.get('signature', 'n/a')}",
        ])
        if "bookmark_names" in row:
            lines.extend([
                f"- Bookmarks: {row.get('bookmark_names')}",
                f"- Content-control tags: {row.get('content_control_tags')}",
                f"- Content-control aliases: {row.get('content_control_aliases')}",
                f"- Word field instructions: {row.get('field_instruction_count')}",
                f"- Paragraphs / tables / drawings: {row.get('paragraph_count')} / {row.get('table_count')} / {row.get('drawing_count')}",
                f"- Header/footer parts / images: {row.get('header_footer_parts')} / {row.get('image_parts')}",
                f"- Styles part present: {row.get('styles_present')}",
            ])
        if row.get("ooxml_parse_error"):
            lines.append("- OOXML metadata parse: failed")
        if row.get("note"):
            lines.append(f"- Note: {row['note']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive")
    parser.add_argument("--output", default="-")
    args = parser.parse_args()
    report = inspect_archive(args.archive)
    if args.output == "-":
        print(report, end="")
    else:
        with open(args.output, "w", encoding="utf-8") as output:
            output.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
