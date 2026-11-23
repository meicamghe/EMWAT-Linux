# Visible Writer close acceptance probe

Date: 2026-11-23
Branch: `feature/recovery-retention-policy`

## Purpose

This is a focused diagnostic probe for the unresolved Save / Don't Save / Cancel
behavior. It launches a visible LibreOffice Writer document through the actual
`LibreOfficeAdapter`, records the adapter's UNO close/save event trace, and
writes the bytes returned by the adapter to a local `.doc` file.

It is **not** a complete EMWAT application, installer, or Almas end-to-end
build. It does not contact Almas or change the production close behavior.

## Requirements

- Ubuntu/Linux with LibreOffice Writer installed.
- The distro Python interpreter with PyUNO available (commonly
  `python3-uno` from the distribution package manager).
- Repository source checked out at the branch containing this probe.

## Run

From the repository root:

```bash
PYTHONPATH=python/src /usr/bin/python3 scripts/writer_close_acceptance.py --output /tmp/emwat-save.doc
```

Use a different output path for each run, for example `/tmp/emwat-discard.doc`
and `/tmp/emwat-cancel-then-save.doc`. If your system's UNO-capable Python is
not `/usr/bin/python3`, substitute its path.

The script creates a disposable DOCX containing the baseline marker
`EMWAT_BASELINE_KEEP_20261123`, opens it in visible Writer, and waits for the
document to close. In Writer, add a distinct unsaved marker such as
`EMWAT_UNSAVED_TEST_001` before closing.

## Required manual runs

Perform these as separate script invocations:

1. **Save:** add the unsaved marker, close Writer, choose Save, and wait for the
   script to write its returned `.doc` file.
2. **Don't Save:** add a different unsaved marker, close Writer, choose Don't
   Save, and wait for the returned `.doc` file.
3. **Cancel:** add a third marker, close Writer, choose Cancel. Confirm Writer
   remains open and the terminal remains waiting (no returned file and no
   terminal close result). Then close again and choose Save or Don't Save so
   this diagnostic run can finish. Record which final choice you made.

After each run, open the returned `.doc` in Writer and inspect whether the
baseline marker and that run's unsaved marker are present. Do not use a real
Almas document; this probe uses only generated disposable content.

## Send back

For each run, provide:

- The terminal output, including the UNO event trace.
- Which prompt choice you made (including the intermediate Cancel).
- Whether Writer stayed open after Cancel.
- Whether the baseline marker is present in the returned file.
- Whether the unsaved marker is present in the returned file.

If practical, attach the returned `.doc` files too. The marker comparison is
the key evidence for whether a discarded edit leaked into the returned output.

## Current known limitation

The current adapter snapshots `final.doc` from `XCloseListener.queryClosing`
and later accepts that snapshot after terminal close. The visible Writer prompt
ordering is not yet established. Therefore the **Don't Save** result may expose
the known bug: an unsaved marker can be present in the returned file even after
choosing Don't Save. This probe is diagnostic; do not treat its output as a
safe production build or send real documents through it.

A Cancel choice should leave the Writer document and bridge-side wait pending.
This standalone probe has no Almas HTTP request, so it can only demonstrate
that the adapter's close wait remains pending while Writer stays open.

## Acceptance criteria

- Save: baseline and saved marker both appear in the returned document.
- Don't Save: baseline appears; the unsaved marker is absent.
- Cancel: Writer remains open and no terminal close result is produced until a
  later accepted close choice.

A failure of any criterion blocks release. Do not infer the user's choice from
`notifyClosed`, `disposing`, or absence of a save callback.
