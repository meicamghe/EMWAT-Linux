"""Gap-aware HTTP body extraction from a reassembled TCP byte stream."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class HttpBodyExtraction:
    header: bytes | None
    body: bytes
    content_length: int | None
    transfer_encoding: str | None
    header_complete: bool
    body_complete: bool
    body_start: int | None
    body_end: int | None
    body_gap_ranges: tuple[tuple[int, int], ...]
    errors: tuple[str, ...]


def _intersections(gaps: Iterable[tuple[int, int]], start: int, end: int):
    return tuple(
        (max(gap_start, start) - start, min(gap_end, end) - start)
        for gap_start, gap_end in gaps
        if gap_start < end and gap_end > start
    )


def _chunked_end(data: bytes, start: int) -> int | None:
    pos = start
    while True:
        line_end = data.find(b"\r\n", pos)
        if line_end < 0:
            return None
        size_token = data[pos:line_end].split(b";", 1)[0].strip()
        try:
            size = int(size_token, 16)
        except ValueError:
            return None
        chunk_start = line_end + 2
        if size == 0:
            if data[chunk_start:chunk_start + 2] == b"\r\n":
                return chunk_start + 2
            trailer_end = data.find(b"\r\n\r\n", chunk_start)
            return None if trailer_end < 0 else trailer_end + 4
        chunk_end = chunk_start + size
        if len(data) < chunk_end + 2 or data[chunk_end:chunk_end + 2] != b"\r\n":
            return None
        pos = chunk_end + 2


def extract_http_body(
    stream: bytes,
    gap_ranges: Iterable[tuple[int, int]] = (),
) -> HttpBodyExtraction:
    """Extract one HTTP message body; gaps are offsets into stream."""
    gaps = tuple(sorted((int(a), int(b)) for a, b in gap_ranges if b > a))
    split = stream.find(b"\r\n\r\n")
    if split < 0:
        return HttpBodyExtraction(
            None, b"", None, None, False, False, None, None, (),
            ("HTTP header terminator missing",),
        )

    header_end = split + 4
    header = stream[:header_end]
    lines = header[:-4].split(b"\r\n")
    content_lengths: list[int] = []
    transfer_encoding = None
    errors: list[str] = []
    for line in lines[1:]:
        if b":" not in line:
            continue
        name, value = line.split(b":", 1)
        key, value = name.strip().lower(), value.strip()
        if key == b"content-length":
            try:
                content_lengths.append(int(value))
            except ValueError:
                errors.append("invalid Content-Length")
        elif key == b"transfer-encoding":
            transfer_encoding = value.decode("ascii", errors="replace").lower()

    if content_lengths and len(set(content_lengths)) != 1:
        errors.append("conflicting Content-Length headers")
    content_length = content_lengths[0] if content_lengths and len(set(content_lengths)) == 1 else None
    header_complete = not _intersections(gaps, 0, header_end)

    if transfer_encoding and "chunked" in transfer_encoding:
        body_end = _chunked_end(stream, header_end)
        if body_end is None:
            body = stream[header_end:]
            body_gaps = _intersections(gaps, header_end, len(stream))
            return HttpBodyExtraction(
                header, body, content_length, transfer_encoding, header_complete,
                False, header_end, None, body_gaps,
                tuple(errors + ["chunked body incomplete or malformed"]),
            )
    elif content_length is not None and content_length >= 0:
        body_end = header_end + content_length
        if len(stream) < body_end:
            body = stream[header_end:]
            body_gaps = _intersections(gaps, header_end, len(stream))
            return HttpBodyExtraction(
                header, body, content_length, transfer_encoding, header_complete,
                False, header_end, body_end, body_gaps,
                tuple(errors + ["Content-Length body truncated"]),
            )
    else:
        body = stream[header_end:]
        body_gaps = _intersections(gaps, header_end, len(stream))
        errors.append("no supported HTTP body boundary (Content-Length or chunked)")
        return HttpBodyExtraction(
            header, body, content_length, transfer_encoding, header_complete,
            False, header_end, None, body_gaps, tuple(errors),
        )

    body = stream[header_end:body_end]
    body_gaps = _intersections(gaps, header_end, body_end)
    complete = header_complete and not body_gaps and not errors
    return HttpBodyExtraction(
        header, body, content_length, transfer_encoding, header_complete,
        complete, header_end, body_end, body_gaps, tuple(errors),
    )
