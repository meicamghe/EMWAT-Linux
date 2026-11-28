#!/usr/bin/env python3
"""Report HTTP request/response timing for one TCP conversation in a pcapng."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python" / "src"))
from emwat_linux.http_capture import extract_http_body

from scapy.layers.inet import IP, TCP
from scapy.layers.inet6 import IPv6
from scapy.utils import PcapNgReader


@dataclass(frozen=True)
class Segment:
    timestamp: float
    sequence: int
    payload: bytes
    flags: str


def packet_ip_pair(packet):
    if IP in packet:
        return packet[IP].src, packet[IP].dst
    if IPv6 in packet:
        return packet[IPv6].src, packet[IPv6].dst
    return None, None


def collect_segments(path: str, client_ip: str, client_port: int,
                     server_ip: str, server_port: int):
    directions = {"request": [], "response": []}
    capture_start = None
    packet_count = 0

    with PcapNgReader(path) as reader:
        for packet in reader:
            if TCP not in packet:
                continue
            src_ip, dst_ip = packet_ip_pair(packet)
            tcp = packet[TCP]
            if (src_ip, int(tcp.sport), dst_ip, int(tcp.dport)) == (
                client_ip, client_port, server_ip, server_port
            ):
                direction = "request"
            elif (src_ip, int(tcp.sport), dst_ip, int(tcp.dport)) == (
                server_ip, server_port, client_ip, client_port
            ):
                direction = "response"
            else:
                continue

            timestamp = float(packet.time)
            capture_start = timestamp if capture_start is None else min(capture_start, timestamp)
            payload = bytes(tcp.payload)
            directions[direction].append(
                Segment(timestamp, int(tcp.seq), payload, str(tcp.flags))
            )
            packet_count += 1

    if capture_start is None:
        raise SystemExit("No packets found for the requested TCP tuple.")

    return directions, capture_start, packet_count


def reassemble(segments: Iterable[Segment]):
    payload_segments = sorted(
        (segment for segment in segments if segment.payload),
        key=lambda segment: (segment.sequence, segment.timestamp),
    )
    if not payload_segments:
        return b"", None, None, []

    base_sequence = payload_segments[0].sequence
    next_sequence = base_sequence
    assembled = bytearray()
    gaps = []

    for segment in payload_segments:
        start = segment.sequence
        end = start + len(segment.payload)
        if end <= next_sequence:
            continue
        if start > next_sequence:
            gaps.append((next_sequence, start))
            assembled.extend(b"\x00" * (start - next_sequence))
            next_sequence = start
        overlap = max(0, next_sequence - start)
        assembled.extend(segment.payload[overlap:])
        next_sequence = end

    return bytes(assembled), base_sequence, next_sequence, gaps


def http_message_info(segments: list[Segment], capture_start: float):
    payload_segments = [segment for segment in segments if segment.payload]
    data, base_sequence, end_sequence, gaps = reassemble(payload_segments)
    if not data:
        return {
            "bytes": 0,
            "header": None,
            "header_bytes": None,
            "content_length": None,
            "body": b"",
            "body_complete": False,
            "body_gap_ranges": (),
            "body_errors": (),
            "body_complete_time": None,
            "first_payload_time": None,
            "last_payload_time": None,
            "gaps": gaps,
        }

    first_payload_time = min(s.timestamp for s in payload_segments)
    last_payload_time = max(s.timestamp for s in payload_segments)
    gap_offsets = [
        (start - base_sequence, end - base_sequence)
        for start, end in gaps
    ] if base_sequence is not None else []
    extraction = extract_http_body(data, gap_offsets)
    header = (
        extraction.header.decode("iso-8859-1", errors="replace")
        if extraction.header is not None else None
    )
    content_length = extraction.content_length
    body_complete_time = None

    if extraction.header is not None and content_length is not None and base_sequence is not None:
        expected_end_sequence = base_sequence + len(extraction.header) + content_length
        candidates = [
            segment.timestamp
            for segment in payload_segments
            if segment.sequence < expected_end_sequence
            and segment.sequence + len(segment.payload) >= expected_end_sequence
        ]
        if candidates:
            body_complete_time = min(candidates)

    return {
        "bytes": len(data),
        "header": header,
        "header_bytes": extraction.header,
        "content_length": content_length,
        "body": extraction.body,
        "body_complete": extraction.body_complete,
        "body_gap_ranges": extraction.body_gap_ranges,
        "body_errors": extraction.errors,
        "body_complete_time": body_complete_time,
        "first_payload_time": first_payload_time,
        "last_payload_time": last_payload_time,
        "gaps": gaps,
    }


def fmt_time(value, capture_start):
    if value is None:
        return "unknown"
    return f"{value - capture_start:.6f}s"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("pcapng")
    parser.add_argument("--client-ip", default="127.0.0.1")
    parser.add_argument("--client-port", type=int, default=61189)
    parser.add_argument("--server-ip", default="127.0.0.1")
    parser.add_argument("--server-port", type=int, default=1984)
    parser.add_argument("--extract-dir", type=Path, help="write HTTP bodies and metadata; partial files are explicitly marked")
    args = parser.parse_args()

    directions, capture_start, packet_count = collect_segments(
        args.pcapng, args.client_ip, args.client_port, args.server_ip, args.server_port
    )
    request = http_message_info(directions["request"], capture_start)
    response = http_message_info(directions["response"], capture_start)

    print("# TCP/HTTP timing report")
    print()
    print(f"- Tuple: {args.client_ip}:{args.client_port} <-> {args.server_ip}:{args.server_port}")
    print(f"- Captured packets: {packet_count}")
    print()
    for name, info in (("Request", request), ("Response", response)):
        print(f"## {name}")
        print(f"- Reassembled payload bytes: {info['bytes']}")
        print(f"- Content-Length: {info['content_length']}")
        print(f"- First payload: {fmt_time(info['first_payload_time'], capture_start)}")
        print(f"- Last payload: {fmt_time(info['last_payload_time'], capture_start)}")
        print(f"- HTTP body completion packet: {fmt_time(info['body_complete_time'], capture_start)}")
        print(f"- Sequence gaps: {info['gaps']}")
        print(f"- Extracted body bytes: {len(info['body'])}")
        print(f"- Body exact/complete: {info['body_complete']}")
        if info["body_errors"]:
            print(f"- Body extraction notes: {info['body_errors']}")
        if info["header"]:
            print(info["header"])
        print()

    if args.extract_dir:
        args.extract_dir.mkdir(parents=True, exist_ok=True)
        metadata = {}
        for name, info in (("request", request), ("response", response)):
            if info["header_bytes"] is None:
                continue
            suffix = ".bin" if info["body_complete"] else ".partial.bin"
            body_path = args.extract_dir / f"{name}-body{suffix}"
            header_path = args.extract_dir / f"{name}-headers.bin"
            body_path.write_bytes(info["body"])
            header_path.write_bytes(info["header_bytes"])
            metadata[name] = {
                "body_file": body_path.name,
                "headers_file": header_path.name,
                "body_bytes": len(info["body"]),
                "body_complete": info["body_complete"],
                "content_length": info["content_length"],
                "sequence_gaps": info["gaps"],
                "body_gap_ranges": info["body_gap_ranges"],
                "extraction_notes": info["body_errors"],
            }
        (args.extract_dir / "http-extraction.json").write_text(
            json.dumps(metadata, indent=2, default=list) + "\n",
            encoding="utf-8",
        )
        print(f"- HTTP extraction written to: {args.extract_dir}")

    request_done = request["body_complete_time"]
    response_first = response["first_payload_time"]
    if request_done is not None and response_first is not None:
        print("## Request/response gap")
        print(f"- From final request body byte to first response payload: {response_first - request_done:.6f}s")
    else:
        print("## Request/response gap")
        print("- Could not calculate: missing Content-Length or payload boundary.")


if __name__ == "__main__":
    main()
