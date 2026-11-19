import unittest


class GtkRecoveryViewImportTests(unittest.TestCase):
    def test_module_import_does_not_require_py_gobject(self):
        # GTK is loaded lazily by build_recovery_picker, keeping the bridge
        # and its headless test suite independent of a graphical session.
        from emwat_linux.gtk_recovery_view import build_recovery_picker

        self.assertTrue(callable(build_recovery_picker))

    def test_extreme_timestamp_does_not_crash_view_rendering(self):
        from emwat_linux.gtk_recovery_view import _format_timestamp

        self.assertEqual(_format_timestamp(1e300), "زمان نامعتبر")


if __name__ == "__main__":
    unittest.main()
