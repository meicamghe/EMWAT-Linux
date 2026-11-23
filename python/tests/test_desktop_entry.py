import tempfile
import unittest
from pathlib import Path

from emwat_linux.desktop_entry import render_desktop_entry, write_desktop_entry


class DesktopEntryTests(unittest.TestCase):
    def test_quotes_paths_with_spaces(self):
        rendered = render_desktop_entry(
            "[Desktop Entry]\nType=Application\nExec=emwat-linux\nTerminal=false\n",
            "/opt/EMWAT Linux/bin/emwat-linux",
        )
        self.assertIn('Exec="/opt/EMWAT Linux/bin/emwat-linux"\n', rendered)

    def test_escapes_desktop_entry_reserved_characters(self):
        rendered = render_desktop_entry(
            "[Desktop Entry]\nExec=emwat-linux\n",
            '/opt/EMWAT\\tools/"quoted"$50%/emwat-linux',
        )
        self.assertIn(
            'Exec="/opt/EMWAT\\\\tools/\\"quoted\\"\\$50%%/emwat-linux"',
            rendered,
        )

    def test_rejects_control_characters(self):
        for path in ("/opt/emwat\n--bad", "/opt/emwat\tbad", "/opt/emwat\x7f"):
            with self.subTest(path=repr(path)):
                with self.assertRaisesRegex(ValueError, "invalid_desktop_executable_path"):
                    render_desktop_entry("[Desktop Entry]\nExec=emwat-linux\n", path)

    def test_requires_exactly_one_exec_key(self):
        for template in ("[Desktop Entry]\nName=EMWAT\n", "[Desktop Entry]\nExec=a\nExec=b\n"):
            with self.subTest(template=template):
                with self.assertRaisesRegex(ValueError, "exactly_one_exec_key"):
                    render_desktop_entry(template, "/usr/bin/emwat-linux")

    def test_write_desktop_entry_uses_utf8_and_replaces_exec(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "template.desktop"
            target = Path(directory) / "installed.desktop"
            source.write_text("[Desktop Entry]\nName=EMWAT Linux\nExec=emwat-linux\n", encoding="utf-8")
            write_desktop_entry(source, target, "/home/user/bin/emwat-linux")
            self.assertEqual(
                target.read_text(encoding="utf-8"),
                '[Desktop Entry]\nName=EMWAT Linux\nExec="/home/user/bin/emwat-linux"\n',
            )


if __name__ == "__main__":
    unittest.main()
