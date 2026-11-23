"""Read-only diagnostics for an EMWAT Linux desktop runtime.

This command does not start the bridge, alter configuration, or inspect documents.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from typing import Sequence


@dataclass(frozen=True)
class Check:
    name: str
    required: bool
    available: bool
    detail: str


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _gtk4_available() -> bool:
    try:
        import gi

        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk

        return Gtk.get_major_version() == 4
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def collect_checks() -> list[Check]:
    """Return local runtime checks without starting services or touching user data."""
    python_ok = sys.version_info >= (3, 10)
    office = shutil.which("libreoffice") or shutil.which("soffice")
    uno_ok = _module_available("uno")
    gtk_ok = _gtk4_available()
    return [
        Check(
            "python",
            True,
            python_ok,
            f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        ),
        Check(
            "libreoffice",
            True,
            office is not None,
            office or "not found (install the LibreOffice Writer package)",
        ),
        Check(
            "uno",
            True,
            uno_ok,
            "Python UNO bindings available" if uno_ok
            else "not importable by this Python interpreter (check distro python3-uno binding)",
        ),
        Check(
            "gtk4",
            False,
            gtk_ok,
            "GTK 4 / PyGObject available" if gtk_ok
            else "optional recovery UI unavailable (install gir1.2-gtk-4.0 and python3-gi)",
        ),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="emwat-linux-doctor",
        description="Check local EMWAT Linux runtime dependencies (read-only).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print machine-readable diagnostic results",
    )
    args = parser.parse_args(argv)
    checks = collect_checks()
    if args.json:
        print(json.dumps([asdict(check) for check in checks], ensure_ascii=False, indent=2))
    else:
        for check in checks:
            level = "OK" if check.available else ("MISSING" if check.required else "OPTIONAL")
            print(f"{level:8} {check.name}: {check.detail}")
        missing = [check.name for check in checks if check.required and not check.available]
        if missing:
            print("Required runtime dependencies are missing: " + ", ".join(missing))
        else:
            print("Required local runtime dependencies are present.")
    return 1 if any(check.required and not check.available for check in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
