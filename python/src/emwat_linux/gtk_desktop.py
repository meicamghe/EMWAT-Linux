"""GTK 4 desktop shell for EMWAT Linux diagnostics, recovery, and bridge control.

The normal entry point injects the captured loopback deployment configuration.
Explicit operation discard remains fail-closed with a local 409 response; this
is a safety policy, not a claim of Windows wire compatibility.
"""
from __future__ import annotations

import argparse
import threading
from typing import Any, Sequence


APPLICATION_ID = "org.emwat.Linux"
BRIDGE_STATUS_POLL_SECONDS = 1



def _stop_bridge_supervisor_on_shutdown(bridge_supervisor: Any | None) -> None:
    """Stop an injected bridge before GTK exits, including after a failed run."""
    if bridge_supervisor is None:
        return
    state = bridge_supervisor.state
    if getattr(state, "value", state) in ("running", "failed"):
        bridge_supervisor.stop()


def create_default_recovery_controller() -> Any:
    """Connect the desktop picker to the default per-user recovery store."""
    from emwat_linux.recovery_controller import RecoveryPickerController
    from emwat_linux.recovery_service import RecoverySnapshotService
    from emwat_linux.recovery_store import RecoverySnapshotStore

    return RecoveryPickerController(
        RecoverySnapshotService(RecoverySnapshotStore())
    )


def create_desktop_application(
    *,
    recovery_controller: Any | None = None,
    bridge_supervisor: Any | None = None,
    auto_start_bridge: bool = False,
) -> Any:
    """Create GTK with optional, explicitly configured bridge auto-start."""
    if type(auto_start_bridge) is not bool:
        raise ValueError("auto_start_bridge must be a boolean")
    if auto_start_bridge and bridge_supervisor is None:
        raise ValueError("auto_start_bridge_requires_bridge_supervisor")
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gio, Gtk
    except (ImportError, ValueError) as exc:
        raise RuntimeError(
            "GTK 4 and PyGObject are required; install python3-gi and gir1.2-gtk-4.0"
        ) from exc

    from emwat_linux.doctor import collect_checks

    application = Gtk.Application(
        application_id=APPLICATION_ID,
        flags=Gio.ApplicationFlags.NON_UNIQUE,
    )
    windows: dict[str, Any] = {"main": None, "recovery": None}
    bridge_operation_lock = threading.RLock()
    shutting_down = False
    close_worker_active = False
    close_approved = False

    def shutdown_bridge(_app: Any) -> None:
        nonlocal shutting_down
        if bridge_supervisor is None:
            return
        # Serialize shutdown with button-triggered start/stop workers. Mark
        # shutdown first so a worker not yet scheduled cannot start afterward.
        with bridge_operation_lock:
            shutting_down = True
            _stop_bridge_supervisor_on_shutdown(bridge_supervisor)

    application.connect("shutdown", shutdown_bridge)

    def activate(app: Any) -> None:
        if windows["main"] is not None:
            windows["main"].present()
            return

        window = Gtk.ApplicationWindow(application=app)
        windows["main"] = window
        window.set_title("EMWAT Linux")
        window.set_default_size(620, 460)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)
        window.set_child(root)

        title = Gtk.Label(label="EMWAT — کنترل و عیب‌یابی")
        title.set_xalign(0)
        title.add_css_class("title-1")
        root.append(title)

        description = Gtk.Label(
            label="پل محلی الماس گام و LibreOffice Writer برای Linux"
        )
        description.set_xalign(0)
        description.set_wrap(True)
        root.append(description)

        heading = Gtk.Label(label="وضعیت وابستگی‌های سیستم")
        heading.set_xalign(0)
        heading.add_css_class("heading")
        root.append(heading)

        checks_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        root.append(checks_box)
        checks = collect_checks()
        for check in checks:
            if check.available:
                state = "آماده"
            elif check.required:
                state = "نیازمند نصب"
            else:
                state = "اختیاری / نصب‌نشده"
            line = Gtk.Label(label=f"{state} — {check.name}: {check.detail}")
            line.set_xalign(0)
            line.set_wrap(True)
            checks_box.append(line)

        missing = [item.name for item in checks if item.required and not item.available]
        summary = Gtk.Label(
            label=(
                "وابستگی‌های اصلی نصب هستند."
                if not missing
                else "برای اجرای هسته، وابستگی‌های ضروری بالا را نصب کنید."
            )
        )
        summary.set_xalign(0)
        summary.set_wrap(True)
        root.append(summary)

        bridge_heading = Gtk.Label(label="سرویس ارتباط با الماس گام")
        bridge_heading.set_xalign(0)
        bridge_heading.add_css_class("heading")
        root.append(bridge_heading)

        bridge_status = Gtk.Label(
            label=(
                f"وضعیت: {bridge_supervisor.state.value}"
                if bridge_supervisor is not None
                else "وضعیت: پیکربندی نشده؛ سرویس اجرا نمی‌شود"
            )
        )
        bridge_status.set_xalign(0)
        bridge_status.set_wrap(True)
        root.append(bridge_status)

        bridge_actions = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL, spacing=8
        )
        root.append(bridge_actions)
        bridge_start = Gtk.Button(label="شروع سرویس")
        bridge_stop = Gtk.Button(label="توقف سرویس")
        bridge_actions.append(bridge_start)
        bridge_actions.append(bridge_stop)
        bridge_start.set_sensitive(bridge_supervisor is not None)
        bridge_stop.set_sensitive(
            bridge_supervisor is not None
            and bridge_supervisor.state.value in ("running", "failed")
        )

        if bridge_supervisor is not None:
            from gi.repository import GLib

            def refresh_bridge_controls() -> bool:
                if not window.get_visible():
                    return GLib.SOURCE_REMOVE
                state = bridge_supervisor.state
                failure = bridge_supervisor.failure
                bridge_status.set_text(
                    f"وضعیت: {state.value}"
                    + (f" — خطا: {failure}" if failure is not None else "")
                )
                busy = state.value in ("starting", "stopping")
                bridge_start.set_sensitive(
                    not busy and state.value in ("idle", "stopped")
                )
                bridge_stop.set_sensitive(
                    not busy and state.value in ("running", "failed")
                )
                return GLib.SOURCE_REMOVE

            def poll_bridge_state() -> bool:
                if not window.get_visible():
                    return GLib.SOURCE_REMOVE
                refresh_bridge_controls()
                return GLib.SOURCE_CONTINUE

            # A serving thread can fail without a button action. Poll the
            # supervisor on GTK's main context so the failure is visible.
            GLib.timeout_add_seconds(BRIDGE_STATUS_POLL_SECONDS, poll_bridge_state)

            def run_bridge_operation(operation: Any) -> None:
                bridge_start.set_sensitive(False)
                bridge_stop.set_sensitive(False)

                def worker() -> None:
                    try:
                        with bridge_operation_lock:
                            if shutting_down:
                                return
                            operation()
                    except BaseException:
                        # The supervisor retains the authoritative exception.
                        pass
                    GLib.idle_add(refresh_bridge_controls)

                threading.Thread(
                    target=worker,
                    name="emwat-bridge-ui-operation",
                    daemon=True,
                ).start()

            bridge_start.connect(
                "clicked", lambda _button: run_bridge_operation(bridge_supervisor.start)
            )
            bridge_stop.connect(
                "clicked", lambda _button: run_bridge_operation(bridge_supervisor.stop)
            )

            def request_window_close(_window: Any) -> bool:
                nonlocal close_worker_active, close_approved, shutting_down
                if close_approved:
                    windows["main"] = None
                    return False

                state = bridge_supervisor.state
                if state.value in ("idle", "stopped"):
                    windows["main"] = None
                    return False
                if close_worker_active:
                    return True

                close_worker_active = True
                bridge_start.set_sensitive(False)
                bridge_stop.set_sensitive(False)
                bridge_status.set_text(
                    "در حال توقف سرویس؛ اگر سندی در Writer باز باشد، ابتدا باید بسته شود…"
                )

                def stop_before_close() -> None:
                    nonlocal shutting_down
                    failure: BaseException | None = None
                    try:
                        # Wait for any button-triggered operation to finish,
                        # then stop the bridge away from GTK's main thread.
                        with bridge_operation_lock:
                            shutting_down = True
                            _stop_bridge_supervisor_on_shutdown(bridge_supervisor)
                    except BaseException as exc:
                        failure = exc
                        with bridge_operation_lock:
                            shutting_down = False

                    def finish_close() -> bool:
                        nonlocal close_worker_active, close_approved
                        close_worker_active = False
                        current_state = bridge_supervisor.state
                        if (
                            failure is None
                            and current_state.value in ("idle", "stopped")
                        ):
                            close_approved = True
                            window.close()
                        else:
                            # Refresh button sensitivity first; then preserve the
                            # actionable drain failure instead of overwriting it
                            # with the generic FAILED state label.
                            refresh_bridge_controls()
                            bridge_status.set_text(
                                "توقف کامل نشد؛ اگر سند Writer باز است آن را ببندید، "
                                "سپس دوباره پنجره را ببندید. "
                                + f"جزئیات: {failure or bridge_supervisor.failure}"
                            )
                        return GLib.SOURCE_REMOVE

                    GLib.idle_add(finish_close)

                threading.Thread(
                    target=stop_before_close,
                    name="emwat-bridge-window-close",
                    daemon=False,
                ).start()
                return True

            window.connect("close-request", request_window_close)
        else:
            window.connect(
                "close-request",
                lambda *_args: windows.__setitem__("main", None) or False,
            )

        if recovery_controller is None:
            recovery = Gtk.Button(label="بازیابی اسناد — هنوز پیکربندی نشده")
            recovery.set_sensitive(False)
        else:
            recovery = Gtk.Button(label="بازیابی اسناد…")

            def open_recovery(_button: Any) -> None:
                current = windows["recovery"]
                if current is None:
                    from emwat_linux.gtk_recovery_view import build_recovery_picker

                    current = build_recovery_picker(app, recovery_controller)
                    windows["recovery"] = current
                    current.connect(
                        "close-request",
                        lambda *_args: windows.__setitem__("recovery", None) or False,
                    )
                current.present()

            recovery.connect("clicked", open_recovery)
        root.append(recovery)

        note = Gtk.Label(
            label=(
                "Bridge فقط روی 127.0.0.1:1984 و با Origin ثبت‌شده الماس گام اجرا می‌شود. "
                "Discard صریح تا زمان بازیابی پاسخ ویندوز با خطای محلی 409 متوقف می‌شود."
                if bridge_supervisor is not None
                else "بدون Supervisor پیکربندی‌شده، سرویس غیرفعال است."
            )
        )
        note.set_xalign(0)
        note.set_wrap(True)
        note.add_css_class("dim-label")
        root.append(note)

        window.present()
        if auto_start_bridge and bridge_supervisor is not None and not missing:
            run_bridge_operation(bridge_supervisor.start)

    application.connect("activate", activate)
    return application


def main(argv: Sequence[str] | None = None) -> int:
    """Launch GTK and auto-start the evidence-configured loopback bridge."""
    parser = argparse.ArgumentParser(
        prog="emwat-linux",
        description="Open EMWAT Linux diagnostics and recovery controls.",
    )
    parser.parse_args(argv)
    from emwat_linux.deployment import create_default_bridge_supervisor

    application = create_desktop_application(
        recovery_controller=create_default_recovery_controller(),
        bridge_supervisor=create_default_bridge_supervisor(),
        auto_start_bridge=True,
    )
    return int(application.run([]))


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["APPLICATION_ID", "create_desktop_application", "main"]
