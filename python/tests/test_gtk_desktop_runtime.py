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
        window.present()


if __name__ == "__main__":
    unittest.main()
