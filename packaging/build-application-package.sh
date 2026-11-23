#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
version=${1:-0.1.0}
output_dir=${2:-"$repo_root/dist"}
case "$version" in
    ''|*[!0-9A-Za-z.+:~_-]*)
        echo "Invalid Debian package version: $version" >&2
        exit 2
        ;;
esac

command -v dpkg-deb >/dev/null 2>&1 || {
    echo "dpkg-deb is required to build the application package." >&2
    exit 1
}

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT HUP INT TERM
root="$stage/root"
mkdir -p \
    "$root/usr/lib/python3/dist-packages" \
    "$root/usr/lib/emwat-linux/packaging" \
    "$root/usr/bin" \
    "$root/usr/share/doc/emwat-linux" \
    "$root/DEBIAN"

cp -a "$repo_root/python/src/emwat_linux" "$root/usr/lib/python3/dist-packages/"
cp "$repo_root/packaging/install-desktop-entry.sh" \
   "$repo_root/packaging/uninstall-desktop-entry.sh" \
   "$repo_root/packaging/org.emwat.Linux.desktop" \
   "$root/usr/lib/emwat-linux/packaging/"
cp "$repo_root/packaging/README.md" "$root/usr/share/doc/emwat-linux/README.md"

write_python_command() {
    command_name=$1
    module_name=$2
    cat > "$root/usr/bin/$command_name" <<EOF
#!/bin/sh
exec /usr/bin/python3 -m $module_name "\$@"
EOF
    chmod 0755 "$root/usr/bin/$command_name"
}

write_shell_command() {
    command_name=$1
    script_name=$2
    cat > "$root/usr/bin/$command_name" <<EOF
#!/bin/sh
exec /bin/sh /usr/lib/emwat-linux/packaging/$script_name "\$@"
EOF
    chmod 0755 "$root/usr/bin/$command_name"
}

write_python_command emwat-linux emwat_linux.gtk_desktop
write_python_command emwat-linux-doctor emwat_linux.doctor
write_python_command emwat-linux-desktop-entry emwat_linux.desktop_entry
write_shell_command emwat-linux-install-desktop-entry install-desktop-entry.sh
write_shell_command emwat-linux-uninstall-desktop-entry uninstall-desktop-entry.sh

cat > "$root/DEBIAN/control" <<EOF
Package: emwat-linux
Version: $version
Section: office
Priority: optional
Architecture: all
Maintainer: EMWAT Linux contributors
Depends: python3 (>= 3.10), python3-gi, gir1.2-gtk-4.0, libreoffice-writer, python3-uno
Recommends: python3-cryptography, python3-keyring
Description: EMWAT Linux desktop control shell and Writer bridge
 Native Linux control shell, recovery interface, diagnostics, and LibreOffice
 Writer integration components. Production Almas bridge startup remains
 disabled until deployment-specific protocol configuration is supplied.
EOF

mkdir -p "$output_dir"
dpkg-deb --build --root-owner-group "$root" "$output_dir/emwat-linux_${version}_all.deb"
printf 'Built application package: %s\n' "$output_dir/emwat-linux_${version}_all.deb"
