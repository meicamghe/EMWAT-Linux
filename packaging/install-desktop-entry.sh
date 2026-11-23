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
desktop_entry_helper=$(command -v emwat-linux-desktop-entry) || {
    echo "emwat-linux-desktop-entry is not installed or is not on PATH." >&2
    exit 1
}
"$desktop_entry_helper" "$desktop_file" "$temporary_file" "$launcher"
install -m644 "$temporary_file" "$applications_dir/org.emwat.Linux.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$applications_dir" || true
fi
printf 'Installed desktop launcher: %s\n' "$applications_dir/org.emwat.Linux.desktop"
