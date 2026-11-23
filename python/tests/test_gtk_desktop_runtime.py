import unittest


class GtkDesktopRuntimeTests(unittest.TestCase):
    def test_application_creates_control_window(self):
        try:
            import gi
            gi.require_version("Gtk", "4.0")
            from gi.repository import Gtk
        except (ImportError, ValueError):
            self.skipTest("GTK 4 / PyGObject is not installed")

        from emwat_linux.gtk_desktop import create_desktop_application

        application = create_desktop_application()
        application.register(None)
        application.activate()
        window = application.get_active_window()
        self.assertIsNotNone(window)
        self.assertIsInstance(window, Gtk.ApplicationWindow)
        self.assertEqual(window.get_title(), "EMWAT Linux")
        application.quit()
        window.close()


if __name__ == "__main__":
    unittest.main()
