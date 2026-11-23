# Per-user desktop launcher

These scripts install or remove only the EMWAT .desktop launcher in the current user's applications directory. They do not install the Python package, LibreOffice, GTK, SANE, start the bridge, or configure Almas endpoints.

After installing the Python package and ensuring emwat-linux is on PATH:

```sh
sh packaging/install-desktop-entry.sh
```

Remove the launcher with:

```sh
sh packaging/uninstall-desktop-entry.sh
```

Both operations are per-user and do not require root. The installer quotes the executable path according to Desktop Entry Exec rules, including spaces, quotes, backslashes and literal percent characters.

The current desktop application is a diagnostics/recovery shell. Its production main() intentionally does not start a bridge without verified deployment configuration. These scripts are not a complete EMWAT desktop package or service installer.