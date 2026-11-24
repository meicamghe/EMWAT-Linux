#!/usr/bin/env python3
"""Visible Writer close/discard acceptance probe for EMWAT-Linux.

Run from the repository root with the distro Python that can import UNO:
  PYTHONPATH=python/src /usr/bin/python3 scripts/writer_close_acceptance.py

The probe creates a disposable DOCX containing a baseline marker, opens it
through the real LibreOfficeAdapter, waits for a title-bar close, and exports
the adapter's returned legacy Word document. It does not contact Almas.
"""
from __future__ import annotations

import argparse
import base64
from pathlib import Path
import sys
import tempfile
import zipfile

from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.libreoffice_adapter import LibreOfficeAdapter
from emwat_linux.word_config import parse_word_config


BASELINE = "EMWAT_BASELINE_KEEP_20261123"


def make_docx() -> bytes:
    """Create a minimal, valid DOCX with a stable baseline marker."""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    relationships = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body>
<w:p><w:r><w:t>EMWAT Writer close acceptance probe</w:t></w:r></w:p>
<w:p><w:r><w:t>{BASELINE}</w:t></w:r></w:p>
<w:p><w:r><w:t>After Writer opens, add a separate unsaved marker here.</w:t></w:r></w:p>
<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>
</w:body></w:document>"""
    from io import BytesIO
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", relationships)
        archive.writestr("word/document.xml", document)
    return buffer.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--soffice", default="soffice", help="LibreOffice executable")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("writer-close-probe-returned.doc"),
        help="where to save the document returned by the adapter",
    )
    args = parser.parse_args()

    if sys.platform != "linux":
        parser.error("this acceptance probe is Linux-only")
    try:
        document_bytes = make_docx()
        config_xml = b"<word-document/>"
        request = EditWordDocumentRequest(
            config=parse_word_config(base64.b64encode(config_xml).decode("ascii")),
            document_bytes=document_bytes,
            sign_data_text="",
            extra_parameters={},
        )
        adapter = LibreOfficeAdapter(soffice_path=args.soffice, headless=False)
        handle = adapter.open_document(
            request,
            on_modified=lambda: 0,
            on_saved=lambda: None,
        )
    except Exception as exc:
        print(f"FAILED to open visible Writer probe: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2

    print("\nWriter is open with a disposable document.")
    print(f"Baseline marker (must always remain): {BASELINE}")
    print("1. Add a unique marker, e.g. EMWAT_UNSAVED_TEST_001, in Writer.")
    print("2. Close Writer using its window close button.")
    print("3. Choose Save, Don't Save, or Cancel in the native prompt.")
    print("   For Cancel, verify Writer stays open and this terminal keeps waiting.")
    print("   Then choose Save or Don't Save to finish this probe run.")
    print("\nWaiting for the document's terminal close; do not close this terminal.")
    try:
        close_event = adapter.wait_for_close(handle)
        returned = adapter.export_final_document(handle)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_bytes(returned)
    except KeyboardInterrupt:
        adapter._cleanup(handle)
        print("\nProbe interrupted; Writer session was asked to stop.", file=sys.stderr)
        return 130
    except Exception as exc:
        adapter._cleanup(handle)
        print(f"FAILED during close/export: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 3

    trace = adapter.inspect_close_lifecycle_trace(handle)
    print(f"Close disposition: {close_event.disposition.value}")
    print("UNO event trace: " + " -> ".join(event.name for event in trace))
    print(f"Returned Word document: {args.output.resolve()}")
    print("Next: open the returned file in Writer and check the baseline and unsaved markers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
