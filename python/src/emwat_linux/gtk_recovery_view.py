"""GTK 4 recovery picker view over the toolkit-neutral controller.

PyGObject is imported only when a window is built, so protocol, recovery,
and headless test processes do not need GTK installed.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any


def _show_error(Gtk: Any, parent: Any, message: str) -> None:
    dialog = Gtk.MessageDialog(
        transient_for=parent,
        modal=True,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        text=message,
    )
    dialog.connect("response", lambda widget, _response: widget.destroy())
    dialog.show()


def build_recovery_picker(application: Any, controller: Any) -> Any:
    """Build a GTK 4 recovery window using RecoveryPickerController.

    The controller remains responsible for catalog validation, restore safety,
    and destructive-action authorization. This view never reads store paths or
    document contents.
    """
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk
    except (ImportError, ValueError) as exc:
        raise RuntimeError("GTK 4 and PyGObject are required for the desktop UI") from exc

    window = Gtk.ApplicationWindow(application=application)
    window.set_title("EMWAT — Recovery")
    window.set_default_size(680, 420)

    outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
    outer.set_margin_top(18)
    outer.set_margin_bottom(18)
    outer.set_margin_start(18)
    outer.set_margin_end(18)
    window.set_child(outer)

    heading = Gtk.Label(label="بازیابی اسناد")
    heading.set_xalign(0)
    outer.append(heading)

    status = Gtk.Label(label="")
    status.set_xalign(0)
    outer.append(status)

    scroller = Gtk.ScrolledWindow()
    scroller.set_vexpand(True)
    outer.append(scroller)

    listing = Gtk.ListBox()
    listing.set_selection_mode(Gtk.SelectionMode.SINGLE)
    scroller.set_child(listing)

    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    outer.append(actions)
    refresh_button = Gtk.Button(label="بروزرسانی")
    restore_button = Gtk.Button(label="بازیابی…")
    discard_button = Gtk.Button(label="حذف نسخه پشتیبان…")
    actions.append(refresh_button)
    actions.append(restore_button)
    actions.append(discard_button)

    selected_session: str | None = None

    def selected_id() -> str | None:
        row = listing.get_selected_row()
        return getattr(row, "emwat_session_id", None) if row is not None else None

    def update_actions() -> None:
        has_selection = selected_id() is not None
        restore_button.set_sensitive(has_selection)
        discard_button.set_sensitive(has_selection)

    def refresh(_button: Any = None) -> None:
        nonlocal selected_session
        previous = selected_id() or selected_session
        try:
            state = controller.state(previous)
        except Exception:
            status.set_text("خواندن فهرست بازیابی ناموفق بود.")
            _show_error(Gtk, window, "فهرست نسخه‌های بازیابی قابل خواندن نیست.")
            return

        child = listing.get_first_child()
        while child is not None:
            following = child.get_next_sibling()
            listing.remove(child)
            child = following

        selected_session = state.selected_session_id
        for entry in state.entries:
            stamp = datetime.fromtimestamp(entry.updated_at).astimezone()
            details = (
                f"{entry.document_name}  ·  {entry.size_bytes:,} bytes  ·  "
                f"{stamp:%Y-%m-%d %H:%M}"
            )
            row = Gtk.ListBoxRow()
            label = Gtk.Label(label=details)
            label.set_xalign(0)
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            row.set_child(label)
            row.emwat_session_id = entry.session_id
            listing.append(row)
            if entry.session_id == selected_session:
                listing.select_row(row)

        status.set_text(
            "نسخه بازیابی موجود نیست." if state.is_empty
            else f"{len(state.entries)} نسخه بازیابی"
        )
        update_actions()

    def restore(_button: Any) -> None:
        session_id = selected_id()
        state = controller.state(session_id)
        entry = state.selected_entry
        if entry is None:
            update_actions()
            return
        chooser = Gtk.FileChooserNative.new(
            "ذخیره سند بازیابی‌شده",
            window,
            Gtk.FileChooserAction.SAVE,
            "_ذخیره",
            "_لغو",
        )
        chooser.set_current_name(Path(entry.document_name).name or "recovered-document")
        def on_file_response(dialog: Any, response: Any) -> None:
            try:
                if response == Gtk.ResponseType.ACCEPT:
                    target = dialog.get_file()
                    destination = target.get_path() if target is not None else None
                    if not destination:
                        raise ValueError("invalid_restore_destination")
                    controller.restore(session_id, destination)
                    status.set_text("سند بازیابی شد.")
            except FileExistsError:
                _show_error(Gtk, window, "فایل مقصد از قبل وجود دارد؛ نام دیگری انتخاب کنید.")
            except Exception:
                _show_error(Gtk, window, "بازیابی انجام نشد. مقصد و نسخه انتخاب‌شده را بررسی کنید.")
            finally:
                dialog.destroy()
        chooser.connect("response", on_file_response)
        chooser.show()

    def discard(_button: Any) -> None:
        session_id = selected_id()
        state = controller.state(session_id)
        entry = state.selected_entry
        if entry is None:
            update_actions()
            return
        dialog = Gtk.MessageDialog(
            transient_for=window,
            modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"نسخه بازیابی «{entry.document_name}» حذف شود؟",
        )
        def on_confirm(widget: Any, response: Any) -> None:
            try:
                if response == Gtk.ResponseType.OK:
                    controller.discard(session_id, confirmed=True)
                    selected_session = None
                    refresh()
            except Exception:
                _show_error(Gtk, window, "حذف نسخه بازیابی انجام نشد.")
            finally:
                widget.destroy()
        dialog.connect("response", on_confirm)
        dialog.show()

    listing.connect("row-selected", lambda *_args: update_actions())
    refresh_button.connect("clicked", refresh)
    restore_button.connect("clicked", restore)
    discard_button.connect("clicked", discard)
    refresh()
    return window


__all__ = ["build_recovery_picker"]
