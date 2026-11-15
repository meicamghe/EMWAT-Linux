#!/usr/bin/env python3
"""Compare wordBody in an EditWordDocument POST with the returned response-word file."""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import xml.etree.ElementTree as ET

from analyze_pcap_http_timing import collect_segments, reassemble


def extract_http_body(segments, label):
    data, _base, _end, gaps = reassemble(segments)
    if not data:
        raise SystemExit(f"{label}: no TCP payload")
    split = data.find(b"\r\n\r\n")
    if split < 0:
        raise SystemExit(f"{label}: HTTP header terminator not found")
    header = data[:split].decode("iso-8859-1", errors="replace")
    match = re.search(r"(?im)^Content-Length:\s*(\d+)\s*$", header)
    if not match:
        raise SystemExit(f"{label}: Content-Length not found")
    length = int(match.group(1))
    body = data[split + 4:split + 4 + length]
    if len(body) != length:
        raise SystemExit(f"{label}: expected {length} body bytes, got {len(body)}")
    if gaps:
        raise SystemExit(f"{label}: TCP sequence gaps detected: {gaps}")
    return header, body


def decode_b64(text, label):
    compact = "".join(text.split())
    try:
        return base64.b64decode(compact, validate=False)
    except Exception as exc:
        raise SystemExit(f"{label}: Base64 decode failed: {exc}")


def describe(label, data):
    print(f"### {label}")
    print(f"- Decoded bytes: {len(data)}")
    print(f"- SHA-256: {hashlib.sha256(data).hexdigest()}")
    print(f"- First 32 bytes: {data[:32].hex(' ')}")
    if data.startswith(bytes.fromhex("D0 CF 11 E0 A1 B1 1A E1")):
        kind = "OLE Compound File (legacy DOC container)"
    elif data.startswith(b"PK\x03\x04"):
        kind = "ZIP container (possibly DOCX)"
    else:
        kind = "unknown/other"
    print(f"- Signature: {kind}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pcapng")
    parser.add_argument("--client-ip", default="127.0.0.1")
    parser.add_argument("--client-port", type=int, default=61189)
    parser.add_argument("--server-ip", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=1984)
    args = parser.parse_args()

    directions, _capture_start, _count = collect_segments(
        args.pcapng, args.client_ip, args.client_port, args.server_ip, args.server_port
    )
    request_header, request_body = extract_http_body(directions["request"], "request")
    response_header, response_body = extract_http_body(directions["response"], "response")

    request_xml = ET.fromstring(request_body)
    response_xml = ET.fromstring(response_body)
    word_body_node = request_xml.find(".//param[@name='wordBody']")
    response_node = response_xml.find(".//type[@mimetype='application/msword']")
    if word_body_node is None or word_body_node.text is None:
        raise SystemExit("Request XML has no non-empty wordBody param.")
    if response_node is None or response_node.text is None:
        raise SystemExit("Response XML has no non-empty application/msword type.")

    request_file = decode_b64(word_body_node.text, "wordBody")
    response_file = decode_b64(response_node.text, "response-word")

    print("# EditWordDocument document payload comparison")
    print()
    print(f"- Request: {request_header.splitlines()[0]}")
    print(f"- Response: {response_header.splitlines()[0]}")
    print()
    describe("Request wordBody", request_file)
    describe("Response application/msword", response_file)

    print("### Comparison")
    print(f"- Byte-identical: {request_file == response_file}")
    print(f"- Length delta (response - request): {len(response_file) - len(request_file)}")
    limit = min(len(request_file), len(response_file))
    first_diff = next((i for i in range(limit) if request_file[i] != response_file[i]), None)
    print(f"- First differing byte offset: {first_diff if first_diff is not None else 'none in shared range'}")
    differing = sum(1 for a, b in zip(request_file, response_file) if a != b)
    print(f"- Differing bytes in shared range: {differing}")


if __name__ == "__main__":
    main()
