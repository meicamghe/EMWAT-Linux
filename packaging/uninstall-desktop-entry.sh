#!/bin/sh
set -eu

applications_dir="${XDG_DATA_HOME:-"$HOME/.local/share"}/applications"
desktop_path="$applications_dir/org.emwat.Linux.desktop"

if [ -e "$desktop_path" ]; then
    rm -f -- "$desktop_path"
fi

if command -v update-desktop-database >/dev/null 2>&1 && [ -d "$applications_dir" ]; then
    update-desktop-database "$applications_dir" || true
fi

printf 'Removed desktop launcher: %s\n' "$desktop_path"
