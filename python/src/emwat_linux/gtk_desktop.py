"""Minimal GTK 4 control shell for EMWAT Linux.

This is deliberately a diagnostics/recovery shell, not a bridge launcher:
the Almas Origin allowlist and Cancel wire response must be supplied by a
deployment-specific, evidence-backed configuration before a bridge can start.
"""
from __future__ import annotations

import argparse
from typing import Any, Sequence


APPLICATION_ID = "org.emwat.Linux"


def create_desktop_application(*, recovery_controller: Any | None = None) -> Any:
    """Create the GTK application; import GTK only when the desktop is launched."""
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
                "راه‌اندازی Bridge تا زمان ارائه تنظیمات معتبر Origin و قرارداد "
                "پاسخ Cancel فعال نمی‌شود."
            )
        )
        note.set_xalign(0)
        note.set_wrap(True)
        note.add_css_class("dim-label")
        root.append(note)

        window.present()

    application.connect("activate", activate)
    return application


def main(argv: Sequence[str] | None = None) -> int:
    """Launch the local GTK control shell without starting the Almas bridge."""
    parser = argparse.ArgumentParser(
        prog="emwat-linux",
        description="Open EMWAT Linux diagnostics and recovery controls.",
    )
    parser.parse_args(argv)
    application = create_desktop_application()
    return int(application.run([]))


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["APPLICATION_ID", "create_desktop_application", "main"]
