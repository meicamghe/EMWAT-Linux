import unittest


class GtkDesktopRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            raise unittest.SkipTest("GTK 4 / PyGObject is not installed")

        from emwat_linux.gtk_desktop import create_desktop_application

        cls.Gtk = Gtk
        cls.application = create_desktop_application()
        cls.application.register(None)
        cls.application.activate()
        cls.main_window = cls.application.get_active_window()
        if cls.main_window is None:
            raise AssertionError("GTK application did not create its main window")
        cls.extra_windows = []

    @classmethod
    def tearDownClass(cls):
        for window in cls.extra_windows:
            window.close()
        cls.main_window.close()
        cls.application.quit()

    def test_application_creates_control_window(self):
        self.assertIsInstance(self.main_window, self.Gtk.ApplicationWindow)
        self.assertEqual(self.main_window.get_title(), "EMWAT Linux")

    def test_recovery_picker_selects_newest_metadata_row(self):
        from types import SimpleNamespace
        from emwat_linux.gtk_recovery_view import build_recovery_picker

        entry = SimpleNamespace(
            session_id="session-newest",
            document_name="letter.doc",
            size_bytes=128,
            updated_at=1_800_000_000.0,
        )
        state = SimpleNamespace(
            entries=(entry,),
            selected_session_id=entry.session_id,
            selected_entry=entry,
            is_empty=False,
        )
        controller = SimpleNamespace(state=lambda _selected=None: state)
        window = build_recovery_picker(self.application, controller)
        self.extra_windows.append(window)

        root = window.get_child()
        status = root.get_first_child().get_next_sibling().get_next_sibling()
        scroller = status.get_next_sibling()
        listing = scroller.get_child()
        # Gtk.ScrolledWindow may insert a Gtk.Viewport around a non-scrollable
        # child. Unwrap it rather than assuming get_child() is always ListBox.
        if isinstance(listing, self.Gtk.Viewport):
            listing = listing.get_child()
        self.assertIsInstance(listing, self.Gtk.ListBox)
        selected = listing.get_selected_row()
        self.assertIsNotNone(selected)
        self.assertEqual(selected.get_name(), "session-newest")
        actions = root.get_last_child()
        restore_button = actions.get_first_child().get_next_sibling()
        discard_button = restore_button.get_next_sibling()
        self.assertTrue(restore_button.get_sensitive())
        self.assertTrue(discard_button.get_sensitive())

    def test_z_main_window_can_reopen_while_recovery_window_is_open(self):
        self.assertTrue(self.extra_windows)
        self.main_window.close()
        self.application.activate()
        reopened = self.application.get_active_window()
        self.assertIsNotNone(reopened)
        self.assertEqual(reopened.get_title(), "EMWAT Linux")
        self.extra_windows.append(reopened)

    def test_recovery_picker_builds_with_empty_catalog(self):
        from types import SimpleNamespace
        from emwat_linux.gtk_recovery_view import build_recovery_picker

        state = SimpleNamespace(
            entries=(),
            selected_session_id=None,
            selected_entry=None,
            is_empty=True,
        )
        controller = SimpleNamespace(state=lambda _selected=None: state)
        window = build_recovery_picker(self.application, controller)
        self.extra_windows.append(window)
        self.assertEqual(window.get_title(), "EMWAT — Recovery")
        actions = window.get_child().get_last_child()
        restore_button = actions.get_first_child().get_next_sibling()
        discard_button = restore_button.get_next_sibling()
        self.assertFalse(restore_button.get_sensitive())
        self.assertFalse(discard_button.get_sensitive())
        window.present()


if __name__ == "__main__":
    unittest.main()
