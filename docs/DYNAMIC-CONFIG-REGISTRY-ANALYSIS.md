# EMWAT Dynamic Config — Registry settings analysis

Date: 2026-11-24  
Source: static analysis of EmwatMethods.bpl1, TD32 procedures and the settings form. No registry from a live customer machine was exported.

## Registry location

The settings form uses:

`HKCU\Software\Emwat\Dynamic Config`

Observed value names (spellings preserved from the binary/resources):

| Value name | Evidence / current interpretation |
|---|---|
| `Background Priniting` | Boolean setting exposed by the settings form |
| `Dont Ask Save On Print` | Boolean setting exposed by the settings form |
| `Save Before Print` | Boolean setting exposed by the settings form |
| `Logging Level` | Logging configuration |
| `Save I/O Trace Files` | I/O trace output toggle |
| `AutoSaveInterval` | Numeric timer interval |
| `Created IO Trace Count` | I/O trace retention/count setting |

The typo in `Background Priniting` is intentional in this evidence record; it reflects the literal resource string.

## AutoSaveInterval

- The settings form converts its selected interval value by multiplying by 1000 before writing `AutoSaveInterval`; the registry value is therefore milliseconds, while the UI choice is seconds.
- The WordViewer lifecycle routine at `0x004D0D24` reads the interval into viewer field `+0x88`.
- `TWordViewer.OnTmrAutoSave` uses that field when setting the `TTimer.Interval` on the timer object at viewer offset `+0x7C`.
- The timer interval is clamped to a minimum of `10,000 ms` (10 seconds).
- The exact list of UI interval choices is stored in a global array near `0x0062A808`; its entries have not yet been decoded. Do not invent the selectable values.

## Boolean settings

The lifecycle routine reads three Boolean values into viewer flags at offsets `+0x3C`, `+0x3D` and `+0x3E`. The TWordViewer VMT confirms the exact flags: `+0x3C=fBG_Printing`, `+0x3D=fDontAskSaveBeforePrint`, and `+0x3E=fSaveBeforePrint`. These align respectively with the settings form values `Background Priniting`, `Dont Ask Save On Print`, and `Save Before Print`. This mapping is confirmed; preserve the three flags independently in Linux configuration.

## Timer callback behavior

- `OnTmrAutoSave` assigns `OnControlerNotify` at `0x004BB3B0` as the timer event handler using `TTimer.SetOnTimer`.
- It sets the timer interval and enables the timer.
- `OnControlerNotify` disables the timer during its callback, checks document state and a reentrancy guard, invokes `CostumizeRecAndCC`, calls Word `Get_Content(-1)`, prepares `.easd/.easz` path variants and invokes `euUnArchive`; it re-enables the timer at exit.
- `CostumizeRecAndCC` makes one normal call through the Word Document vtable slot used by `TWordDocument.PrintOutOld`; up to two further calls are exception-retry fallbacks, not three unconditional print jobs. It also sets/clears `IsSavingNow` during the operation.

## Implementation notes for Linux

1. Store the settings under a native configuration file/service, not the Windows Registry.
2. Preserve all three Boolean flags independently; do not collapse them into one print setting.
3. Store AutoSaveInterval in milliseconds internally and enforce the observed 10-second lower bound.
4. Keep logging level, I/O trace toggle and trace-count retention separate from AutoSave.
5. Do not reproduce the misspelled registry value name in a new Linux config schema unless import compatibility requires it.
6. The timer callback, print operations and archive extraction are separate behaviors even though they are invoked in one callback chain.

## Open questions

- Exact selectable AutoSaveInterval values in the array at `0x0062A808`.
- The Boolean registry-to-viewer mapping is confirmed: `Background Priniting` → `fBG_Printing`, `Dont Ask Save On Print` → `fDontAskSaveBeforePrint`, `Save Before Print` → `fSaveBeforePrint`.
- Whether the single successful timer-path `Document.PrintOutOld` call produces a GAM job whose document label can be matched to the spooler record and output artifact.
- Whether the archive extraction path is paired with an output writer in another module or process.


## ReadyToClose close gate

The TWordViewer VMT identifies `ReadyToClose` at offset `+0x5E`. `OnControlerNotify` clears it while the timer callback performs recipient/CC customization, Content retrieval and archive extraction, then restores it. `WordAppDocumentBeforeSave` cancels the close if `ReadyToClose` is false. This is a close-safety gate; it is not yet proven to be the condition that releases the HTTP request.


## 2026-11-24 correction — print retry semantics

The complete `CostumizeRecAndCC` trace shows that the Word Document `PrintOutOld` dispatch has one normal attempt and up to two additional attempts only when an exception is raised. It is incorrect to model these as three unconditional print jobs. The method also sets `IsSavingNow` (`TWordViewer+0x5C`) while active and clears it on exit. This behavior is separately recorded in `WORD-FIELD-SILENT-SAVE-ANALYSIS.md`.
