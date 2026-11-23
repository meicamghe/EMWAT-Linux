# Visible Writer close acceptance probe and results

Date: 2026-11-23
Branch: `feature/recovery-retention-policy`
Probe: `scripts/writer_close_acceptance.py`

## Purpose and boundary

This probe launches a disposable DOCX through the real `LibreOfficeAdapter`,
records UNO save/close callbacks, waits for the interactive Writer close
decision, and writes the Word-compatible bytes returned by the adapter.

It does **not** contact Almas, run the complete desktop application, or prove
the Windows/Almas HTTP response contract. It validates the Writer adapter's
visible close/save behavior only.

## Environment and run command

Requirements:

- Ubuntu/Linux with LibreOffice Writer.
- The distro Python interpreter with PyUNO available.
- The repository checked out at this branch.

Run from the repository root:

```bash
PYTHONPATH=python/src /usr/bin/python3 scripts/writer_close_acceptance.py --output /tmp/emwat-save.doc
```

Use a distinct output path for each run. The generated document contains the
baseline marker `EMWAT_BASELINE_KEEP_20261123`. Add a separate unsaved marker
in Writer before closing so the returned file can be checked without using a
real letter or customer data.

## Manual acceptance results — 2026-11-23

All three interactive cases were run by the operator against the branch code.

### Save

- Operator selected **Save** in Writer.
- Observed callback trace:
  `save_done -> saved_state_succeeded -> query_closing -> notify_closing -> disposing`.
- Returned document contained the test marker `EMWAT_SAVE_FIXED_004`.
- Result: **passed**. The saved content was present in the returned Word file.

### Don't Save

- Operator selected **Don't Save** in Writer after adding a distinct unsaved marker.
- Observed close trace:
  `query_closing -> notify_closing -> disposing`.
- Returned document retained `EMWAT_BASELINE_KEEP_20261123`.
- The unsaved marker was absent from the returned document.
- Result: **passed**. Unsaved edits did not leak into the returned Word file.

### Cancel, then Don't Save

- Operator selected **Cancel** in the Writer prompt.
- Writer remained open and the terminal continued waiting; no terminal close
  result was produced for the cancelled attempt.
- Operator then closed Writer again and selected **Don't Save**.
- Final trace:
  `query_closing -> notify_closing -> disposing`.
- The returned file contained no newly added test information.
- Result: **passed** for the observed retry behavior. Cancel itself did not
  complete the session; the later accepted close did.

## Implementation behavior now under test

The adapter keeps the last confirmed saved Word document separately from its
recovery snapshots and from the live Writer document:

- A baseline Word-compatible file is established before editing.
- Only successful UNO `OnSaveDone` / `OnSaveAsDone` callbacks replace the
  confirmed saved-state file.
- The replacement is staged and validated before atomic publication.
- `queryClosing` records lifecycle evidence only; it does not snapshot live,
  potentially dirty edits.
- After terminal close, the adapter returns the last confirmed saved-state
  file. A cancelled close attempt remains pending.
- Periodic recovery data is not used as the final Almas response payload.

This is why Save returns the newly saved marker, while Don't Save returns the
baseline/last saved version without the discarded marker.

## Acceptance status and remaining boundary

| Case | Observed result | Status |
|---|---|---|
| Save | Confirmed saved marker returned | Passed |
| Don't Save | Baseline retained; unsaved marker absent | Passed |
| Cancel | Writer stayed open; wait remained pending until a later accepted close | Passed |

Do not infer the user's choice from `notifyClosed`, `disposing`, or the
absence of a save callback alone. The behavior above is established by the
interactive marker checks together with the saved-state implementation.

Still **not validated** by this probe:

- live Almas browser/HTTP request and response;
- the exact Windows Save/Don't Save/Cancel wire envelopes;
- the full installed GTK application lifecycle;
- automatic WordConfig field mapping or full Word/Writer semantic parity.

A successful Writer acceptance run is not a production-readiness or Almas
end-to-end claim.
