"""Safe rendering of a per-user Desktop Entry launcher."""
from __future__ import annotations

import argparse
from pathlib import Path


def render_desktop_entry(template: str, executable_path: str) -> str:
    """Replace exactly one Exec key using Desktop Entry argument quoting."""
    if not isinstance(template, str) or not isinstance(executable_path, str):
        raise TypeError("desktop_entry_text_and_executable_must_be_strings")
    if not executable_path or any(ord(character) < 32 or ord(character) == 127
                                  for character in executable_path):
        raise ValueError("invalid_desktop_executable_path")

    escaped = (
        executable_path.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace(chr(96), "\\" + chr(96))
        .replace("$", "\\$")
        .replace("%", "%%")
    )
    lines = template.splitlines()
    exec_indexes = [index for index, line in enumerate(lines) if line.startswith("Exec=")]
    if len(exec_indexes) != 1:
        raise ValueError("desktop_entry_must_contain_exactly_one_exec_key")
    lines[exec_indexes[0]] = f'Exec="{escaped}"'
    return "\n".join(lines) + "\n"


def write_desktop_entry(
    template_path: str | Path,
    destination_path: str | Path,
    executable_path: str,
) -> None:
    template = Path(template_path).read_text(encoding="utf-8")
    rendered = render_desktop_entry(template, executable_path)
    Path(destination_path).write_text(rendered, encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="emwat-desktop-entry")
    parser.add_argument("template")
    parser.add_argument("destination")
    parser.add_argument("executable")
    args = parser.parse_args(argv)
    write_desktop_entry(args.template, args.destination, args.executable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["main", "render_desktop_entry", "write_desktop_entry"]
