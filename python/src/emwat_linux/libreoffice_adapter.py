"""LibreOffice UNO adapter for close-driven EMWAT document sessions.

This is the first concrete office-engine adapter. It opens the captured
Word document in a visible LibreOffice instance, snapshots a Word-compatible
copy during the document close callback, and returns those bytes after close.

EMWAT-specific field IDs, signData, permissions, and cancellation semantics
are intentionally not guessed here. Those mappings require verified fixtures.
"""
from __future__ import annotations

import importlib
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from threading import Event
import time
from typing import Callable
from urllib.parse import quote

from emwat_linux.document_coordinator import OfficeCoordinationError
from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.office_adapter import CloseDisposition, OfficeCloseEvent


_CFB_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def _file_url(path: Path) -> str:
    """Return a file URL without relying on platform-specific string joins."""
    return path.resolve().as_uri()


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _source_extension(data: bytes) -> str:
    """Recognize the two common Word containers; retain .doc fallback for CFB."""
    if data.startswith(_CFB_SIGNATURE):
        return ".doc"
    if data.startswith(_ZIP_SIGNATURES):
        return ".docx"
    raise ValueError("unsupported_word_document_container")


class _ModifyListener:
    def __init__(self, callback: Callable[[], int]) -> None:
        self._callback = callback

    def modified(self, _event: object) -> None:
        self._callback()

    def disposing(self, _event: object) -> None:
        return


class _DocumentCloseListener:
    """Snapshot the current document from UNO's close callback."""

    def __init__(
        self,
        document: object,
        output_url: str,
        on_closed: Callable[[], None],
        uno_module: object,
    ) -> None:
        self._document = document
        self._output_url = output_url
        self._on_closed = on_closed
        self._uno = uno_module
        self.snapshot_error: Exception | None = None
        self.snapshot_ready = Event()

    def queryClosing(self, _event: object, _gets_ownership: bool) -> None:
        try:
            # storeToURL writes a copy and does not change the document's URL.
            self._document.storeToURL(
                self._output_url,
                (
                    self._property("FilterName", "MS Word 97"),
                    self._property("Overwrite", True),
                ),
            )
        except Exception as exc:  # retained internally; never returned to browser
            self.snapshot_error = exc
        finally:
            self.snapshot_ready.set()

    def notifyClosing(self, _event: object) -> None:
        return

    def notifyClosed(self, _event: object) -> None:
        self._on_closed()

    def disposing(self, _event: object) -> None:
        self._on_closed()

    def _property(self, name: str, value: object) -> object:
        try:
            prop = self._uno.createUnoStruct("com.sun.star.beans.PropertyValue")
            prop.Name = name
            prop.Value = value
            return prop
        except Exception as exc:
            raise RuntimeError("libreoffice_uno_property_unavailable") from exc


class _OfficeHandle:
    def __init__(
        self,
        *,
        process: subprocess.Popen[bytes],
        document: object,
        close_listener: _DocumentCloseListener,
        work_dir: Path,
    ) -> None:
        self.process = process
        self.document = document
        self.close_listener = close_listener
        self.work_dir = work_dir
        self.closed = Event()
        self._closed_once = False

    def mark_closed(self) -> None:
        if not self._closed_once:
            self._closed_once = True
            self.closed.set()


class LibreOfficeAdapter:
    """Launch an isolated visible LibreOffice process for each document.

    A private profile and private loopback UNO port prevent cross-session
    document/profile collisions. The adapter expects python-uno to be available
    to the Python interpreter running this bridge (usually via distro packages).
    """

    def __init__(
        self,
        *,
        soffice_path: str = "soffice",
        connect_timeout_seconds: float = 20.0,
        poll_interval_seconds: float = 0.1,
        process_factory: Callable[..., subprocess.Popen[bytes]] = subprocess.Popen,
        uno_module: object | None = None,
    ) -> None:
        if connect_timeout_seconds <= 0 or poll_interval_seconds <= 0:
            raise ValueError("connection and polling timeouts must be positive")
        self._soffice_path = soffice_path
        self._connect_timeout = connect_timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._process_factory = process_factory
        self._uno = uno_module

    def _uno_runtime(self) -> object:
        if self._uno is None:
            try:
                self._uno = importlib.import_module("uno")
            except ImportError as exc:
                raise RuntimeError("python_uno_not_installed") from exc
        return self._uno

    def _connect(self, port: int, process: subprocess.Popen[bytes]) -> object:
        uno = self._uno_runtime()
        local_context = uno.getComponentContext()
        resolver = local_context.ServiceManager.createInstanceWithContext(
            "com.sun.star.bridge.UnoUrlResolver", local_context
        )
        target = (
            "uno:socket,host=127.0.0.1,port="
            + str(port)
            + ";urp;StarOffice.ComponentContext"
        )
        deadline = time.monotonic() + self._connect_timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError("libreoffice_process_exited_before_uno_ready")
            try:
                return resolver.resolve(target)
            except Exception as exc:
                last_error = exc
                time.sleep(self._poll_interval)
        raise RuntimeError("libreoffice_uno_connection_timeout") from last_error

    def open_document(
        self,
        request: EditWordDocumentRequest,
        *,
        on_modified: Callable[[], int],
        on_saved: Callable[[], None],
    ) -> object:
        del on_saved  # Save events are not yet mapped to a stable UNO event contract.
        work_dir = Path(tempfile.mkdtemp(prefix="emwat-lo-"))
        process: subprocess.Popen[bytes] | None = None
        try:
            extension = _source_extension(request.document_bytes)
            source_path = work_dir / ("incoming" + extension)
            output_path = work_dir / "final.doc"
            profile_path = work_dir / "profile"
            source_path.write_bytes(request.document_bytes)
            port = _unused_loopback_port()
            accept = (
                f"--accept=socket,host=127.0.0.1,port={port};urp;StarOffice.ServiceManager"
            )
            profile_url = _file_url(profile_path)
            process = self._process_factory(
                [
                    self._soffice_path,
                    accept,
                    "--norestore",
                    "--nodefault",
                    "--nofirststartwizard",
                    f"-env:UserInstallation={profile_url}",
                ],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            context = self._connect(port, process)
            manager = context.ServiceManager
            desktop = manager.createInstanceWithContext(
                "com.sun.star.frame.Desktop", context
            )
            uno = self._uno_runtime()
            properties = (
                self._property(uno, "Hidden", False),
                self._property(uno, "ReadOnly", False),
                self._property(uno, "MacroExecutionMode", 4),  # NEVER_EXECUTE
                self._property(uno, "UpdateDocMode", 3),  # NO_UPDATE
            )
            document = desktop.loadComponentFromURL(
                _file_url(source_path), "_blank", 0, properties
            )
            if document is None:
                raise RuntimeError("libreoffice_failed_to_open_document")

            handle = _OfficeHandle(
                process=process,
                document=document,
                close_listener=None,  # attached below once callback is available
                work_dir=work_dir,
            )
            close_listener = _DocumentCloseListener(
                document,
                _file_url(output_path),
                handle.mark_closed,
                uno,
            )
            handle.close_listener = close_listener
            modify_listener = _ModifyListener(on_modified)
            document.addModifyListener(modify_listener)
            document.addCloseListener(close_listener)
            # Keep strong references: PyUNO listeners must outlive their registrations.
            handle.modify_listener = modify_listener
            handle.desktop = desktop
            handle.output_path = output_path
            handle.source_path = source_path
            handle.profile_path = profile_path
            handle.context = context
            return handle
        except Exception:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
            shutil.rmtree(work_dir, ignore_errors=True)
            raise

    @staticmethod
    def _property(uno: object, name: str, value: object) -> object:
        prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        prop.Name = name
        prop.Value = value
        return prop

    def wait_for_close(self, handle: object) -> OfficeCloseEvent:
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        while not handle.closed.wait(self._poll_interval):
            if handle.process.poll() is not None:
                raise RuntimeError("libreoffice_exited_without_document_close")
        if not handle.close_listener.snapshot_ready.wait(self._connect_timeout):
            self._cleanup(handle)
            raise RuntimeError("libreoffice_final_snapshot_timeout")
        if handle.close_listener.snapshot_error is not None:
            error = handle.close_listener.snapshot_error
            self._cleanup(handle)
            raise RuntimeError("libreoffice_final_snapshot_failed") from error
        if not (handle.work_dir / "final.doc").is_file():
            self._cleanup(handle)
            raise RuntimeError("libreoffice_final_document_missing")
        return OfficeCloseEvent(CloseDisposition.CLOSED)

    def export_final_document(self, handle: object) -> bytes:
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        output_path = handle.work_dir / "final.doc"
        try:
            payload = output_path.read_bytes()
            if not payload.startswith(_CFB_SIGNATURE):
                raise RuntimeError("libreoffice_export_not_legacy_word_format")
            return payload
        finally:
            self._cleanup(handle)

    def _cleanup(self, handle: _OfficeHandle) -> None:
        process = handle.process
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        shutil.rmtree(handle.work_dir, ignore_errors=True)


__all__ = ["LibreOfficeAdapter"]
