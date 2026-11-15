#!/usr/bin/env python3
"""Summarize EMWAT HTTP traffic from a Wireshark TCP-payload export.

The report contains protocol metadata only. It never writes request or response
bodies, document text, Base64 payloads, cookies, or authorization values.
"""
from __future__ import annotations

import base64
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path


def read_streams(path: Path):
    streams = defaultdict(list)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="|")
        required = {
            "frame.number", "tcp.stream", "ip.src", "tcp.srcport",
            "ip.dst", "tcp.dstport", "tcp.payload",
        }
        if not required.issubset(reader.fieldnames or []):
            raise ValueError("Unexpected tcp-payloads export columns")
        for row in reader:
            payload_hex = (row.get("tcp.payload") or "").strip()
            if not payload_hex:
                continue
            try:
                payload = bytes.fromhex(payload_hex)
                frame = int(row["frame.number"])
                stream_id = row["tcp.stream"]
                src = (row["ip.src"], row["tcp.srcport"])
                dst = (row["ip.dst"], row["tcp.dstport"])
            except (ValueError, KeyError, TypeError):
                continue
            if src[1] != "1984" and dst[1] != "1984":
                continue
            streams[(stream_id, src, dst)].append((frame, payload))
    return streams


def parse_http_messages(data: bytes):
    messages = []
    offset = 0
    while offset < len(data):
        marker = data.find(b"\r\n\r\n", offset)
        if marker < 0:
            break
        header_block = data[offset:marker]
        lines = header_block.decode("latin-1", errors="replace").split("\r\n")
        if not lines:
            break
        headers = {}
        for line in lines[1:]:
            if ":" in line:
                name, value = line.split(":", 1)
                headers[name.strip().lower()] = value.strip()
        try:
            length = max(0, int(headers.get("content-length", "0")))
        except ValueError:
            length = 0
        body_start = marker + 4
        body_end = body_start + length
        if body_end > len(data):
            break
        messages.append({
            "first": lines[0],
            "headers": headers,
            "body": data[body_start:body_end],
        })
        offset = body_end
    return messages


def safe_path(value: str) -> str:
    value = re.sub(r"(invoke|init)=([^&\s]+)", r"\1=<nonce>", value)
    return value[:180]


def decode_base64_prefix(value: str) -> bytes:
    compact = re.sub(r"\s+", "", value)
    try:
        return base64.b64decode(compact[:256], validate=False)
    except (ValueError, base64.binascii.Error):
        return b""


def xml_metadata(body: bytes):
    result = {"root": None, "status": None, "method": None, "params": []}
    if not body or b"<!DOCTYPE" in body.upper() or b"<!ENTITY" in body.upper():
        return result
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return result
    result["root"] = root.tag
    result["status"] = root.attrib.get("status")
    method = root.find("method")
    if method is not None:
        result["method"] = method.attrib.get("class")
        for param in method.findall("param"):
            text = param.text or ""
            prefix = decode_base64_prefix(text)
            item = {
                "name": param.attrib.get("name", ""),
                "chars": len(text),
                "base64": bool(text) and bool(re.fullmatch(r"[A-Za-z0-9+/=\s]+", text)),
            }
            if item["base64"] and prefix:
                item["decoded_prefix_hex"] = prefix[:8].hex()
                if item["name"] == "wordConfig":
                    try:
                        config_bytes = base64.b64decode(re.sub(r"\s+", "", text))
                        config = ET.fromstring(config_bytes)
                        item["decoded_root"] = config.tag
                        item["document_status"] = config.attrib.get("status")
                        item["field_count"] = len(config.findall(".//field"))
                    except (ET.ParseError, ValueError, base64.binascii.Error):
                        item["decoded_root"] = "unparsed"
            result["params"].append(item)
    type_node = root.find(".//type")
    if type_node is not None:
        result["mime"] = type_node.attrib.get("mimetype")
        result["encryption"] = type_node.attrib.get("encryption")
        text = type_node.text or ""
        prefix = decode_base64_prefix(text)
        result["return_chars"] = len(text)
        if prefix:
            result["return_decoded_prefix_hex"] = prefix[:8].hex()
    return result


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: analyze_tcp_payloads.py <tcp-payloads.txt> <summary.md>")
    source = Path(sys.argv[1])
    output = Path(sys.argv[2])
    streams = read_streams(source)

    by_stream = defaultdict(lambda: defaultdict(list))
    for (stream_id, src, dst), packets in streams.items():
        packets.sort(key=lambda item: item[0])
        data = b"".join(payload for _, payload in packets)
        direction = "to-service" if dst[1] == "1984" else "from-service"
        by_stream[stream_id][direction].append((src, dst, data))

    lines = [
        "# EMWAT TCP capture — metadata-only analysis",
        "",
        f"- Source: {source.name}",
        f"- TCP streams touching port 1984: {len(by_stream)}",
        "- Payload bodies and document contents are intentionally omitted.",
        "- Reassembly uses frame order from the Wireshark export; the export has no TCP sequence column, so this is metadata triage, not byte-perfect TCP reassembly.",
        "",
    ]
    for stream_id in sorted(by_stream, key=lambda value: int(value) if value.isdigit() else value):
        directions = by_stream[stream_id]
        requests = []
        responses = []
        for _, _, data in directions.get("to-service", []):
            requests.extend(parse_http_messages(data))
        for _, _, data in directions.get("from-service", []):
            responses.extend(parse_http_messages(data))
        if not requests and not responses:
            continue
        lines += [f"## TCP stream {stream_id}", ""]
        for index, request in enumerate(requests):
            match = re.match(r"^(GET|POST|PUT|OPTIONS|HEAD|DELETE)\s+(\S+)\s+HTTP/(\d\.\d)$", request["first"])
            if not match:
                continue
            method, path, version = match.groups()
            headers = request["headers"]
            lines += [
                f"### Request {index + 1}",
                f"- Request: {method} {safe_path(path)} HTTP/{version}",
                f"- Content-Type: {headers.get('content-type', 'not present')}",
                f"- Content-Length: {headers.get('content-length', '0')}",
                f"- Origin: {headers.get('origin', 'not present')}",
                f"- Referer: {safe_path(headers.get('referer', 'not present'))}",
            ]
            meta = xml_metadata(request["body"])
            if meta["method"]:
                lines.append(f"- EMWAT method class: {meta['method']}")
                for param in meta["params"]:
                    details = f"{param['chars']} text characters"
                    if param["base64"]:
                        details += ", Base64-like"
                    if param.get("decoded_root"):
                        details += f", decoded XML root {param['decoded_root']}"
                        details += f", status {param.get('document_status')}"
                        details += f", fields {param.get('field_count')}"
                    if param.get("decoded_prefix_hex"):
                        details += f", decoded prefix {param['decoded_prefix_hex']}"
                    lines.append(f"  - {param['name']}: {details}")
            if index < len(responses):
                response = responses[index]
                status_match = re.match(r"^HTTP/\d\.\d\s+(\d{3})\s*(.*)$", response["first"])
                if status_match:
                    status, reason = status_match.groups()
                    lines.append(f"- Response: {status} {reason}")
                    lines.append(f"- Response Content-Type: {response['headers'].get('content-type', 'not present')}")
                    response_meta = xml_metadata(response["body"])
                    if response_meta["root"]:
                        lines.append(f"- Response XML root/status: {response_meta['root']} / {response_meta['status']}")
                    if response_meta.get("mime"):
                        lines.append(f"- Returned MIME/encryption: {response_meta['mime']} / {response_meta.get('encryption')}")
                        lines.append(f"- Returned Base64 text length: {response_meta.get('return_chars')}")
                        lines.append(f"- Decoded file prefix: {response_meta.get('return_decoded_prefix_hex')}")
            lines.append("")
        if not requests:
            for response in responses:
                lines.append(f"- Response-only message: {response['first']}")
            lines.append("")

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote metadata-only report: {output}")


if __name__ == "__main__":
    main()
