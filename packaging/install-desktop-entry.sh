#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
desktop_file="$repo_root/packaging/org.emwat.Linux.desktop"
applications_dir="${XDG_DATA_HOME:-"$HOME/.local/share"}/applications"
launcher=$(command -v emwat-linux) || {
    echo "emwat-linux is not installed or is not on PATH." >&2
    exit 1
}

mkdir -p "$applications_dir"
temporary_file=$(mktemp)
trap 'rm -f "$temporary_file"' EXIT HUP INT TERM
python3 - "$desktop_file" "$temporary_file" "$launcher" <<'PY'
from pathlib import Path
import sys

source = Path(sys.argv[1])
destination = Path(sys.argv[2])
launcher = sys.argv[3]
if any(ord(character) < 32 for character in launcher):
    raise SystemExit("Launcher path contains a control character.")

# Desktop Entry Exec uses its own quoting rules; do not pass this path through
# sed or a shell command string where metacharacters can corrupt the entry.
escaped = (
    launcher.replace("\\", "\\\\")
    .replace('"', '\\"')
    .replace("`", "\\`")
    .replace("$", "\\$")
    .replace("%", "%%")
)
lines = source.read_text(encoding="utf-8").splitlines()
for index, line in enumerate(lines):
    if line.startswith("Exec="):
        lines[index] = f'Exec="{escaped}"'
        break
else:
    raise SystemExit("Desktop entry has no Exec key.")
destination.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
PY
install -m644 "$temporary_file" "$applications_dir/org.emwat.Linux.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$applications_dir" || true
fi
printf 'Installed desktop launcher: %s\n' "$applications_dir/org.emwat.Linux.desktop"
