"""LibreOffice UNO adapter for close-driven EMWAT document sessions.

This is the first concrete office-engine adapter. It opens the captured
Word document in a visible LibreOffice instance, writes private periodic
recovery snapshots while it is open, snapshots a Word-compatible final copy
during close, and returns those bytes after close. Recovery snapshots use the
Linux-native owner-only store, not the Windows .easz archive format.

EMWAT-specific field IDs, signData, permissions, and cancellation semantics
are intentionally not guessed here. Those mappings require verified fixtures.
"""
from __future__ import annotations

import importlib
import math
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
from threading import Event, Lock, RLock, Thread
import time
from typing import Callable

from emwat_linux.close_trace import CloseLifecycleEvent, CloseLifecycleTrace
from emwat_linux.editword_request import EditWordDocumentRequest
from emwat_linux.office_adapter import CloseDisposition, OfficeCloseEvent
from emwat_linux.recovery_store import RecoverySnapshotStore
from emwat_linux.writer_fields import refresh_writer_text_fields
from emwat_linux.writer_inspector import WriterDocumentCatalog, inspect_writer_document
from emwat_linux.writer_properties import set_custom_document_properties
from emwat_linux.word_config import WordDocumentConfig
from emwat_linux.word_writer_evidence import (
    WordWriterEvidenceReport,
    build_word_writer_evidence_report,
)


_CFB_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_ZIP_SIGNATURES = (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")


def _file_url(path: Path) -> str:
    """Return a file URL without relying on platform-specific string joins."""
    return path.resolve().as_uri()


def _unused_loopback_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _stop_process(
    process: subprocess.Popen[bytes],
    *,
    terminate_timeout: float,
    kill_timeout: float,
) -> None:
    """Stop a child process and always attempt to reap it after SIGKILL."""
    if process.poll() is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=terminate_timeout)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        process.kill()
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=kill_timeout)
    except subprocess.TimeoutExpired:
        # The OS still owns the process; don't block bridge shutdown forever.
        return


def _source_extension(data: bytes) -> str:
    """Recognize the two common Word containers; retain .doc fallback for CFB."""
    if data.startswith(_CFB_SIGNATURE):
        return ".doc"
    if data.startswith(_ZIP_SIGNATURES):
        return ".docx"
    raise ValueError("unsupported_word_document_container")


def _uno_listener_proxy(
    delegate: object,
    *,
    uno_module: object,
    interface_name: str,
    methods: tuple[str, ...],
) -> object:
    """Wrap a Python delegate in a real PyUNO interface implementation."""
    unohelper = importlib.import_module("unohelper")
    interface = uno_module.getClass(interface_name)

    def initialize(self: object) -> None:
        unohelper.Base.__init__(self)
        self._delegate = delegate

    namespace: dict[str, object] = {"__init__": initialize}
    for method_name in methods:
        def make_dispatch(name: str) -> Callable[..., object]:
            def dispatch(self: object, *args: object) -> object:
                return getattr(self._delegate, name)(*args)
            return dispatch
        namespace[method_name] = make_dispatch(method_name)

    proxy_type = type(
        f"EMWAT_{interface_name}_Proxy",
        (unohelper.Base, interface),
        namespace,
    )
    return proxy_type()


class _ModifyListener:
    def __init__(self, callback: Callable[[], int]) -> None:
        self._callback = callback

    def modified(self, _event: object) -> None:
        self._callback()

    def disposing(self, _event: object) -> None:
        return


class _DocumentCloseListener:
    """Snapshot the final document before close and stop periodic recovery after close."""

    def __init__(
        self,
        document: object,
        output_url: str,
        on_closed: Callable[[], None],
        snapshot_properties: tuple[object, ...],
        snapshot_lock: Lock,
        recovery_stop: Event,
        trace: CloseLifecycleTrace | None = None,
    ) -> None:
        self._document = document
        self._output_url = output_url
        self._on_closed = on_closed
        self._snapshot_properties = snapshot_properties
        self._snapshot_lock = snapshot_lock
        self._recovery_stop = recovery_stop
        self._trace = trace
        # The native Save / Don't Save choice is not resolved at queryClosing.
        # Never export the live document here: that could capture edits discarded
        # by the user's subsequent Don't Save choice.
        self.snapshot_error: Exception | None = None
        self.snapshot_ready = Event()

    def queryClosing(self, _event: object, _gets_ownership: bool) -> None:
        if self._trace is not None:
            self._trace.record("query_closing")

    def notifyClosing(self, _event: object) -> None:
        if self._trace is not None:
            self._trace.record("notify_closing")

    def notifyClosed(self, _event: object) -> None:
        if self._trace is not None:
            self._trace.record("notify_closed")
        self._recovery_stop.set()
        self._on_closed()

    def disposing(self, _event: object) -> None:
        if self._trace is not None:
            self._trace.record("disposing")
        self._recovery_stop.set()
        self._on_closed()


class _DocumentEventListener:
    """Forward confirmed UNO save-complete document events."""

    _SAVE_EVENTS = frozenset({"OnSaveDone", "OnSaveAsDone"})

    def __init__(
        self,
        callback: Callable[[], None],
        trace: CloseLifecycleTrace | None = None,
    ) -> None:
        self._callback = callback
        self._trace = trace

    def documentEventOccured(self, event: object) -> None:
        event_name = getattr(event, "EventName", "")
        if event_name in self._SAVE_EVENTS:
            if self._trace is not None:
                self._trace.record(
                    "save_done" if event_name == "OnSaveDone" else "save_as_done"
                )
            self._callback()

    def disposing(self, _event: object) -> None:
        return


class _OfficeHandle:
    def __init__(
        self,
        *,
        process: subprocess.Popen[bytes],
        document: object,
        close_listener: _DocumentCloseListener | None,
        work_dir: Path,
        recovery_session_id: str,
    ) -> None:
        self.process = process
        self.document = document
        self.close_listener = close_listener
        self.work_dir = work_dir
        self.recovery_session_id = recovery_session_id
        self.closed = Event()
        self.recovery_stop = Event()
        self.snapshot_lock = RLock()
        self.recovery_thread: Thread | None = None
        self.recovery_error: Exception | None = None
        self.snapshot_properties: tuple[object, ...] = ()
        self.saved_document_path: Path | None = None
        self.saved_snapshot_error: Exception | None = None
        self.saved_snapshot_in_progress = False
        self._closed_once = False
        self.close_trace = CloseLifecycleTrace()

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
        headless: bool = False,
        close_timeout_seconds: float | None = None,
        recovery_store: RecoverySnapshotStore | None = None,
        recovery_interval_seconds: float = 10.0,
    ) -> None:
        def positive_finite_seconds(value: object) -> bool:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return False
            try:
                finite = math.isfinite(float(value))
            except (OverflowError, ValueError):
                return False
            return finite and value > 0

        if not positive_finite_seconds(connect_timeout_seconds) or not positive_finite_seconds(poll_interval_seconds):
            raise ValueError("connection and polling timeouts must be finite positive numbers")
        if close_timeout_seconds is not None and not positive_finite_seconds(close_timeout_seconds):
            raise ValueError("close timeout must be a finite positive number when configured")
        if not positive_finite_seconds(recovery_interval_seconds):
            raise ValueError("recovery interval must be a finite positive number")
        self._soffice_path = soffice_path
        self._connect_timeout = connect_timeout_seconds
        self._poll_interval = poll_interval_seconds
        self._process_factory = process_factory
        self._uno = uno_module
        self._headless = headless
        self._close_timeout = close_timeout_seconds
        self._recovery_store = recovery_store if recovery_store is not None else RecoverySnapshotStore()
        self._recovery_interval = recovery_interval_seconds

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
        """Open the captured Word payload and attach isolated UNO listeners.

        The parsed request config is retained on ``request`` but is not applied
        here: EMWAT field IDs, twin-field rules, image anchors, and print-time
        substitutions still require verified native mappings. Call the explicit
        property-update API only with an externally verified property map.
        """
        work_dir = Path(tempfile.mkdtemp(prefix="emwat-lo-"))
        process: subprocess.Popen[bytes] | None = None
        recovery_session_id: str | None = None
        handle: _OfficeHandle | None = None
        try:
            recovery_session_id = self._recovery_store.create_session()
            extension = _source_extension(request.document_bytes)
            source_path = work_dir / ("incoming" + extension)
            saved_state_path = work_dir / "last-saved.doc"
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
                    *(["--headless"] if self._headless else []),
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
                self._property(uno, "Hidden", self._headless),
                self._property(uno, "ReadOnly", False),
                self._property(uno, "MacroExecutionMode", 4),  # NEVER_EXECUTE
                self._property(uno, "UpdateDocMode", 3),  # NO_UPDATE
            )
            document = desktop.loadComponentFromURL(
                _file_url(source_path), "_blank", 0, properties
            )
            if document is None:
                raise RuntimeError("libreoffice_failed_to_open_document")

            snapshot_properties = (
                self._property(uno, "FilterName", "MS Word 97"),
                self._property(uno, "Overwrite", True),
            )
            # Capture a known-good baseline before the user can make edits.
            document.storeToURL(_file_url(saved_state_path), snapshot_properties)
            if not saved_state_path.is_file():
                raise RuntimeError("libreoffice_initial_saved_state_missing")
            if not saved_state_path.read_bytes().startswith(_CFB_SIGNATURE):
                raise RuntimeError("libreoffice_initial_saved_state_invalid")
            handle = _OfficeHandle(
                process=process,
                document=document,
                close_listener=None,  # attached below once callback is available
                work_dir=work_dir,
                recovery_session_id=recovery_session_id,
            )
            handle.snapshot_properties = snapshot_properties
            handle.saved_document_path = saved_state_path
            close_listener = _DocumentCloseListener(
                document,
                _file_url(saved_state_path),
                handle.mark_closed,
                snapshot_properties,
                handle.snapshot_lock,
                handle.recovery_stop,
                handle.close_trace,
            )
            handle.close_listener = close_listener
            modify_listener = _ModifyListener(on_modified)
            save_listener = _DocumentEventListener(
                lambda: self._capture_confirmed_saved_state(handle, on_saved),
                handle.close_trace,
            )
            modify_proxy = _uno_listener_proxy(
                modify_listener,
                uno_module=uno,
                interface_name="com.sun.star.util.XModifyListener",
                methods=("modified", "disposing"),
            )
            save_proxy = _uno_listener_proxy(
                save_listener,
                uno_module=uno,
                interface_name="com.sun.star.document.XDocumentEventListener",
                methods=("documentEventOccured", "disposing"),
            )
            close_proxy = _uno_listener_proxy(
                close_listener,
                uno_module=uno,
                interface_name="com.sun.star.util.XCloseListener",
                methods=("queryClosing", "notifyClosing", "notifyClosed", "disposing"),
            )
            document.addModifyListener(modify_proxy)
            document.addDocumentEventListener(save_proxy)
            document.addCloseListener(close_proxy)
            # Keep strong references: PyUNO listeners must outlive their registrations.
            handle.modify_listener = modify_listener
            handle.modify_proxy = modify_proxy
            handle.save_listener = save_listener
            handle.save_proxy = save_proxy
            handle.close_proxy = close_proxy
            handle.desktop = desktop
            handle.source_path = source_path
            handle.profile_path = profile_path
            handle.context = context
            handle.recovery_thread = Thread(
                target=self._recovery_loop,
                args=(handle,),
                name=f"emwat-recovery-{recovery_session_id[:8]}",
                daemon=True,
            )
            handle.recovery_thread.start()
            return handle
        except Exception:
            if handle is not None:
                handle.recovery_stop.set()
                if handle.recovery_thread is not None and handle.recovery_thread.is_alive():
                    handle.recovery_thread.join(timeout=2)
            if process is not None:
                _stop_process(process, terminate_timeout=3, kill_timeout=2)
            shutil.rmtree(work_dir, ignore_errors=True)
            if recovery_session_id is not None:
                try:
                    self._recovery_store.remove_session(recovery_session_id)
                except Exception:
                    pass
            raise

    def _capture_confirmed_saved_state(
        self,
        handle: _OfficeHandle,
        on_saved: Callable[[], None],
    ) -> None:
        """Atomically retain the document bytes after a confirmed Writer save."""
        destination = handle.saved_document_path
        if destination is None:
            handle.saved_snapshot_error = RuntimeError("saved_state_path_missing")
            return
        temporary = destination.with_name("last-saved.pending.doc")
        try:
            with handle.snapshot_lock:
                if handle.saved_snapshot_in_progress:
                    return
                handle.saved_snapshot_in_progress = True
                try:
                    handle.document.storeToURL(_file_url(temporary), handle.snapshot_properties)
                    if not temporary.is_file():
                        raise RuntimeError("confirmed_saved_state_export_missing")
                    if not temporary.read_bytes().startswith(_CFB_SIGNATURE):
                        raise RuntimeError("confirmed_saved_state_export_invalid")
                    temporary.replace(destination)
                    handle.saved_snapshot_error = None
                finally:
                    handle.saved_snapshot_in_progress = False
            handle.close_trace.record("saved_state_succeeded")
        except Exception as exc:
            handle.saved_snapshot_error = exc
            handle.close_trace.record("saved_state_failed")
            return
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
        on_saved()

    def _recovery_loop(self, handle: _OfficeHandle) -> None:
        """Persist an owner-only snapshot every interval while the document is open."""
        temporary_path = handle.work_dir / "recovery-snapshot.doc"
        while not handle.recovery_stop.wait(self._recovery_interval):
            try:
                with handle.snapshot_lock:
                    if handle.recovery_stop.is_set():
                        break
                    handle.document.storeToURL(
                        _file_url(temporary_path),
                        handle.snapshot_properties,
                    )
                    payload = temporary_path.read_bytes()
                    self._recovery_store.save_snapshot(handle.recovery_session_id, payload)
                    handle.recovery_error = None
            except Exception as exc:
                # A transient snapshot failure must not close or fail the live Word session.
                handle.recovery_error = exc
            finally:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass

    @staticmethod
    def _property(uno: object, name: str, value: object) -> object:
        prop = uno.createUnoStruct("com.sun.star.beans.PropertyValue")
        prop.Name = name
        prop.Value = value
        return prop

    def inspect_close_lifecycle_trace(
        self,
        handle: object,
    ) -> tuple[CloseLifecycleEvent, ...]:
        """Return fixed-name close/save callback metadata without document data."""
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        return handle.close_trace.snapshot()

    def inspect_document(self, handle: object) -> WriterDocumentCatalog:
        """Inventory Writer structure without exposing document text or values."""
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        with handle.snapshot_lock:
            return inspect_writer_document(handle.document)

    def audit_word_writer_evidence(
        self,
        handle: object,
        config: WordDocumentConfig,
    ) -> WordWriterEvidenceReport:
        """Compare request metadata with Writer structure without mutation."""
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        if not isinstance(config, WordDocumentConfig):
            raise TypeError("invalid_word_document_config")
        with handle.snapshot_lock:
            catalog = inspect_writer_document(handle.document)
            return build_word_writer_evidence_report(config, catalog)

    def apply_custom_property_updates(
        self,
        handle: object,
        updates: object,
    ) -> None:
        """Apply verified existing custom-property values and refresh fields once.

        The caller owns the EMWAT-field-to-property mapping. This adapter only
        applies exact names already present in the document and refreshes
        imported DOCPROPERTY results after the batch succeeds.
        """
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        with handle.snapshot_lock:
            set_custom_document_properties(handle.document, updates)
            if updates:
                refresh_writer_text_fields(handle.document)

    def wait_for_close(self, handle: object) -> OfficeCloseEvent:
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        deadline = (
            time.monotonic() + self._close_timeout
            if self._close_timeout is not None
            else None
        )
        while not handle.closed.wait(self._poll_interval):
            if handle.process.poll() is not None:
                self._cleanup(handle)
                raise RuntimeError("libreoffice_exited_without_document_close")
            if deadline is not None and time.monotonic() >= deadline:
                self._cleanup(handle)
                raise RuntimeError("libreoffice_close_timeout")
        handle.recovery_stop.set()
        if handle.recovery_thread is not None:
            handle.recovery_thread.join(timeout=self._connect_timeout)
            if handle.recovery_thread.is_alive():
                self._cleanup(handle)
                raise RuntimeError("libreoffice_recovery_thread_timeout")
        if handle.close_listener is None:
            self._cleanup(handle)
            raise RuntimeError("libreoffice_close_listener_missing")
        if not handle.close_listener.snapshot_ready.wait(self._connect_timeout):
            self._cleanup(handle)
            raise RuntimeError("libreoffice_final_snapshot_timeout")
        if handle.close_listener.snapshot_error is not None:
            error = handle.close_listener.snapshot_error
            self._cleanup(handle)
            raise RuntimeError("libreoffice_final_snapshot_failed") from error
        if handle.saved_snapshot_error is not None:
            error = handle.saved_snapshot_error
            self._cleanup(handle)
            raise RuntimeError("libreoffice_confirmed_saved_state_failed") from error
        if handle.saved_document_path is None or not handle.saved_document_path.is_file():
            self._cleanup(handle)
            raise RuntimeError("libreoffice_confirmed_saved_state_missing")
        return OfficeCloseEvent(CloseDisposition.CLOSED)

    def export_final_document(self, handle: object) -> bytes:
        if not isinstance(handle, _OfficeHandle):
            raise TypeError("invalid_libreoffice_handle")
        output_path = handle.saved_document_path
        if output_path is None:
            raise RuntimeError("libreoffice_confirmed_saved_state_missing")
        try:
            payload = output_path.read_bytes()
            if not payload.startswith(_CFB_SIGNATURE):
                raise RuntimeError("libreoffice_export_not_legacy_word_format")
            try:
                self._recovery_store.remove_session(handle.recovery_session_id)
            except Exception as exc:
                # A cleanup failure must not suppress a valid final document response.
                handle.recovery_error = exc
            return payload
        finally:
            self._cleanup(handle)

    def _cleanup(self, handle: _OfficeHandle) -> None:
        handle.recovery_stop.set()
        if handle.recovery_thread is not None:
            handle.recovery_thread.join(timeout=2)
        process = handle.process
        _stop_process(process, terminate_timeout=5, kill_timeout=2)
        shutil.rmtree(handle.work_dir, ignore_errors=True)
        try:
            if not self._recovery_store.has_snapshot(handle.recovery_session_id):
                self._recovery_store.remove_session(handle.recovery_session_id)
        except Exception as exc:
            handle.recovery_error = exc


__all__ = ["LibreOfficeAdapter"]
