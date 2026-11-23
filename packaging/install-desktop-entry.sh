#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
desktop_file="$repo_root/packaging/org.emwat.Linux.desktop"
applications_dir="${XDG_DATA_HOME:-"$HOME/.local/share"}/applications"

if ! command -v emwat-linux >/dev/null 2>&1; then
    echo "emwat-linux is not installed or is not on PATH." >&2
    exit 1
fi

install -Dm644 "$desktop_file" "$applications_dir/org.emwat.Linux.desktop"
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$applications_dir" || true
fi
printf 'Installed desktop launcher: %s\n' "$applications_dir/org.emwat.Linux.desktop"
