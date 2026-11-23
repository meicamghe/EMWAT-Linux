import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from emwat_linux import doctor


class DoctorTests(unittest.TestCase):
    def test_collect_checks_reports_required_and_optional_components(self):
        with (
            patch.object(doctor.shutil, "which", side_effect=lambda name: "/usr/bin/soffice" if name == "soffice" else None),
            patch.object(doctor, "_module_available", return_value=True),
            patch.object(doctor, "_gtk4_available", return_value=False),
        ):
            checks = doctor.collect_checks()

        by_name = {check.name: check for check in checks}
        self.assertTrue(by_name["libreoffice"].available)
        self.assertTrue(by_name["uno"].available)
        self.assertFalse(by_name["gtk4"].available)
        self.assertFalse(by_name["gtk4"].required)

    def test_missing_required_dependency_returns_failure(self):
        with (
            patch.object(doctor.shutil, "which", return_value=None),
            patch.object(doctor, "_module_available", return_value=False),
            patch.object(doctor, "_gtk4_available", return_value=False),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                result = doctor.main([])

        self.assertEqual(result, 1)
        self.assertIn("libreoffice", output.getvalue())
        self.assertIn("uno", output.getvalue())

    def test_optional_gtk_absence_does_not_fail_diagnostics(self):
        with (
            patch.object(doctor.shutil, "which", return_value="/usr/bin/libreoffice"),
            patch.object(doctor, "_module_available", return_value=True),
            patch.object(doctor, "_gtk4_available", return_value=False),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                result = doctor.main([])

        self.assertEqual(result, 0)
        self.assertIn("OPTIONAL", output.getvalue())

    def test_json_output_is_machine_readable(self):
        import json

        with (
            patch.object(doctor.shutil, "which", return_value="/usr/bin/libreoffice"),
            patch.object(doctor, "_module_available", return_value=True),
            patch.object(doctor, "_gtk4_available", return_value=True),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                result = doctor.main(["--json"])

        self.assertEqual(result, 0)
        parsed = json.loads(output.getvalue())
        self.assertEqual({item["name"] for item in parsed}, {"python", "libreoffice", "uno", "gtk4"})


    def test_python_below_minimum_version_is_required_failure(self):
        with (
            patch.object(doctor.sys, "version_info", doctor.sys.version_info._replace(major=3, minor=9, micro=18)),
            patch.object(doctor.shutil, "which", return_value="/usr/bin/libreoffice"),
            patch.object(doctor, "_module_available", return_value=True),
            patch.object(doctor, "_gtk4_available", return_value=True),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                result = doctor.main([])

        self.assertEqual(result, 1)
        self.assertIn("MISSING   python: 3.9.18", output.getvalue())
        self.assertIn("Required runtime dependencies are missing: python", output.getvalue())

    def test_json_reports_missing_required_runtime_with_failure_exit_code(self):
        import json

        with (
            patch.object(doctor.sys, "version_info", doctor.sys.version_info._replace(major=3, minor=12, micro=0)),
            patch.object(doctor.shutil, "which", return_value=None),
            patch.object(doctor, "_module_available", return_value=False),
            patch.object(doctor, "_gtk4_available", return_value=False),
        ):
            output = io.StringIO()
            with redirect_stdout(output):
                result = doctor.main(["--json"])

        self.assertEqual(result, 1)
        parsed = json.loads(output.getvalue())
        by_name = {item["name"]: item for item in parsed}
        self.assertFalse(by_name["libreoffice"]["available"])
        self.assertTrue(by_name["libreoffice"]["required"])
        self.assertFalse(by_name["gtk4"]["available"])
        self.assertFalse(by_name["gtk4"]["required"])

if __name__ == "__main__":
    unittest.main()
