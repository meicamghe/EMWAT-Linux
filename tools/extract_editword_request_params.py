#!/usr/bin/env python3
"""Extract redacted structural metadata from an EditWordDocument request."""

from __future__ import annotations

import argparse
import base64
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from analyze_pcap_http_timing import collect_segments, reassemble


def http_body(segments):
    data, _base, _end, gaps = reassemble(segments)
    if not data:
        raise SystemExit("No request TCP payload.")
    split = data.find(b"\r\n\r\n")
    if split < 0:
        raise SystemExit("HTTP header terminator not found.")
    header = data[:split].decode("iso-8859-1", errors="replace")
    match = re.search(r"(?im)^Content-Length:\s*(\d+)\s*$", header)
    if not match:
        raise SystemExit("Request Content-Length not found.")
    length = int(match.group(1))
    body = data[split + 4:split + 4 + length]
    if len(body) != length:
        raise SystemExit(f"Incomplete request body: expected {length}, got {len(body)}")
    if gaps:
        raise SystemExit(f"Request stream contains sequence gaps: {gaps}")
    return header, body


def describe_json(value):
    if isinstance(value, dict):
        return {
            "type": "object",
            "keys": {str(key): describe_json(item) for key, item in value.items()},
        }
    if isinstance(value, list):
        return {
            "type": "array",
            "length": len(value),
            "sample_item_shapes": [describe_json(item) for item in value[:3]],
        }
    if isinstance(value, str):
        return {"type": "string", "length": len(value)}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, (int, float)):
        return {"type": "number"}
    return {"type": type(value).__name__}


def describe_xml(data):
    root = ET.fromstring(data)

    def walk(node):
        return {
            "tag": node.tag,
            "attributes": sorted(node.attrib.keys()),
            "text_length": len(node.text or ""),
            "children": [walk(child) for child in list(node)],
        }

    return walk(root)


def inspect_value(text):
    raw = text.encode("utf-8")
    result = {
        "text_length": len(text),
        "text_prefix": text[:100] if len(text) <= 100 else text[:100] + "...",
        "base64": False,
        "decoded_length": None,
        "decoded_magic": None,
        "decoded_format": None,
        "json_shape": None,
        "xml_shape": None,
        "raw_json_shape": None,
        "raw_xml_shape": None,
    }

    compact = "".join(text.split())
    if len(compact) >= 16 and re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", compact):
        try:
            decoded = base64.b64decode(compact, validate=True)
            result["base64"] = True
            result["decoded_length"] = len(decoded)
            result["decoded_magic"] = decoded[:16].hex(" ")
            if decoded.startswith(bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1")):
                result["decoded_format"] = "OLE Compound File / legacy DOC"
            elif decoded.startswith(b"PK\x03\x04"):
                result["decoded_format"] = "ZIP container"
            elif decoded.startswith(b"\x89PNG\r\n\x1a\n"):
                result["decoded_format"] = "PNG"
            elif decoded.startswith(b"\xff\xd8\xff"):
                result["decoded_format"] = "JPEG"
            elif decoded.startswith(b"II*\x00") or decoded.startswith(b"MM\x00*"):
                result["decoded_format"] = "TIFF"
            else:
                try:
                    parsed = json.loads(decoded.decode("utf-8"))
                    result["json_shape"] = describe_json(parsed)
                    result["decoded_format"] = "JSON"
                except Exception:
                    try:
                        result["xml_shape"] = describe_xml(decoded)
                        result["decoded_format"] = "XML"
                    except Exception:
                        pass
        except Exception:
            pass

    if not result["base64"]:
        try:
            result["raw_json_shape"] = describe_json(json.loads(text))
            result["decoded_format"] = "raw JSON"
        except Exception:
            try:
                result["raw_xml_shape"] = describe_xml(raw)
                result["decoded_format"] = "raw XML"
            except Exception:
                pass
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pcapng")
    parser.add_argument("--client-ip", default="127.0.0.1")
    parser.add_argument("--client-port", type=int, default=61189)
    parser.add_argument("--server-ip", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=1984)
    parser.add_argument("--output-dir", default="editword-param-analysis")
    args = parser.parse_args()

    directions, _capture_start, _count = collect_segments(
        args.pcapng, args.client_ip, args.client_port, args.server_ip, args.server_port
    )
    header, body = http_body(directions["request"])
    root = ET.fromstring(body)
    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    report = [
        "# EditWordDocument request parameter structure (values redacted)",
        "",
        f"- HTTP request: {header.splitlines()[0]}",
        f"- Request body bytes: {len(body)}",
        "",
    ]
    structures = {}
    for node in root.findall(".//param"):
        name = node.attrib.get("name", "<unnamed>")
        value = node.text or ""
        info = inspect_value(value)
        structures[name] = info
        report.extend([
            f"## {name}",
            f"- Text length: {info['text_length']}",
            f"- Base64 encoded: {info['base64']}",
            f"- Decoded length: {info['decoded_length']}",
            f"- Decoded format: {info['decoded_format']}",
            f"- Decoded magic: {info['decoded_magic']}",
        ])
        shape = info["json_shape"] or info["raw_json_shape"]
        if shape is not None:
            report.append("- JSON shape (keys/types only):")
            report.extend("  " + line for line in json.dumps(shape, ensure_ascii=False, indent=2).splitlines())
        xml_shape = info["xml_shape"] or info["raw_xml_shape"]
        if xml_shape is not None:
            report.append("- XML shape (tag/attribute names and text lengths only):")
            report.extend("  " + line for line in json.dumps(xml_shape, ensure_ascii=False, indent=2).splitlines())
        report.append("")

    (outdir / "request-parameter-structure.md").write_text("\n".join(report), encoding="utf-8")
    (outdir / "request-parameter-structure.json").write_text(
        json.dumps(structures, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print("\n".join(report))


if __name__ == "__main__":
    main()
