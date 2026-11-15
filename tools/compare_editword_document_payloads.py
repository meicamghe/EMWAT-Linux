#!/usr/bin/env python3
"""Compare captured wordBody and response-word payloads, tolerating pcap truncation gaps."""

from __future__ import annotations

import argparse
import base64
import hashlib
import re
import xml.etree.ElementTree as ET

from analyze_pcap_http_timing import collect_segments, reassemble


def extract_http_body(segments, label):
    data, base_sequence, _end, gaps = reassemble(segments)
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
    return header, body, base_sequence, split + 4, gaps


def decode_b64(text, label):
    compact = "".join(text.split())
    compact += "=" * ((-len(compact)) % 4)
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


def parse_document_nodes(request_body, response_body):
    request_xml = ET.fromstring(request_body)
    # Large TCP offload frames in this capture have 4-byte snaplen gaps.
    # Those gaps are zero-filled by the timing reassembler; they are only
    # removed from the XML response copy, never from the request.
    clean_response = response_body.replace(b"\x00", b"")
    response_xml = ET.fromstring(clean_response)
    word_body_node = request_xml.find(".//param[@name='wordBody']")
    response_node = response_xml.find(".//type[@mimetype='application/msword']")
    if word_body_node is None or word_body_node.text is None:
        raise SystemExit("Request XML has no non-empty wordBody param.")
    if response_node is None or response_node.text is None:
        raise SystemExit("Response XML has no non-empty application/msword type.")
    return word_body_node.text, response_node.text, clean_response


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
    request_header, request_body, _req_base, _req_body_offset, request_gaps = extract_http_body(
        directions["request"], "request"
    )
    response_header, response_body, response_base, response_body_offset, response_gaps = extract_http_body(
        directions["response"], "response"
    )

    print("# EditWordDocument document payload comparison")
    print()
    print(f"- Request: {request_header.splitlines()[0]}")
    print(f"- Response: {response_header.splitlines()[0]}")
    print(f"- Request sequence gaps: {len(request_gaps)}")
    print(f"- Response sequence gaps: {len(response_gaps)}")
    print(f"- Missing response capture bytes indicated by sequence gaps: {sum(end-start for start, end in response_gaps)}")
    print()

    try:
        request_b64, response_b64, clean_response = parse_document_nodes(request_body, response_body)
        request_file = decode_b64(request_b64, "wordBody")
        response_file = decode_b64(response_b64, "response-word")
    except (ET.ParseError, SystemExit) as exc:
        print(f"- Full comparison unavailable: {exc}")
        print("- The response capture contains sequence gaps; no full-file equality claim is made.")
        return

    describe("Request wordBody", request_file)
    describe("Response application/msword (partial capture)", response_file)

    print("### Comparison")
    print(f"- Full byte-identical: {request_file == response_file}")
    print(f"- Length delta (response - request): {len(response_file) - len(request_file)}")

    first_gap_prefix_bytes = None
    if response_gaps:
        type_match = re.search(
            rb"<type\b[^>]*mimetype=[\"']application/msword[\"'][^>]*>(.*?)</type>",
            response_body,
            re.S,
        )
        if type_match:
            value_start_in_stream = response_body_offset + type_match.start(1)
            first_gap_stream_offset = response_gaps[0][0] - response_base
            prefix_chars = max(0, first_gap_stream_offset - value_start_in_stream)
            first_gap_prefix_bytes = (prefix_chars // 4) * 3
            print(f"- Intact Base64 prefix before first capture gap: {prefix_chars} characters (~{first_gap_prefix_bytes} decoded bytes)")
            limit = min(first_gap_prefix_bytes, len(request_file), len(response_file))
            prefix_equal = request_file[:limit] == response_file[:limit]
            print(f"- Request/response decoded prefix equal before first gap: {prefix_equal}")
            if not prefix_equal:
                first_diff = next((i for i in range(limit) if request_file[i] != response_file[i]), None)
                print(f"- First differing decoded byte before capture gap: {first_diff}")
    if not response_gaps:
        print(f"- Complete files byte-identical: {request_file == response_file}")
    else:
        print("- Full-file comparison is not authoritative because the pcap response contains truncated sequence ranges.")


if __name__ == "__main__":
    main()
