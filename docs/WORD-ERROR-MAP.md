# EMWAT Word / Office error-string map

Date: 2026-11-15  
Source: workflow `analyze-word-event-sink.yml`, run #11 (`43717625474`), artifact `14162998865`  
Input: `analysis-input/EmwatMethods.bpl1`  
Scope: string pointers referenced by the server metadata block near `0x00627B74`. This is an error-message/string table, not a Word COM event callback table.

## Error code/message pairs

The table stores adjacent Delphi string references. The following pairings are based on their adjacency in the table; they are not inferred from function names.

| Code label | Message |
|---|---|
| `Err_0` | Sentinel/default code label; no message pointer is stored in the following slot. |
| `Err_20000` | `Exception: ` (generic exception prefix). |
| `Err_20001` | Request XML is invalid. |
| `Err_20002` | Request Doc is Empty. |
| `Err_20003` | Error on connect to MS-Word. Exception: |
| `Err_20004` | Can not open document. |
| `Err_20005` | Error on insert sign to word document. Exception: |
| `Err_20006` | Field "%s" of Twin fields not found in Doc. |
| `Err_20007` | Temp path not Found. |
| `Err_20008` | Scan failed on %s. The error code(s)= %s\r%s |
| `Err_Ignore` | The operation was canceled by user. |
| `Err_20010` | Loading image failed. The image may be corrupted or invalid. |
| `Err_20016` | Error on connect to MS-Excel. Exception: |
| `Err_20017` | Can not open WorkBook. |
| `Err_20018` | User local folder not Found. |

The table includes a standalone `Exception: ` string associated with the generic error region. Preserve the distinction between the code label and message text when reproducing UI/log behavior.

## Other settings strings in the same metadata region

The expanded string-pointer scan also found these values:

- Log levels: `None`, `Info`, `Debug`.
- Auto-save interval labels: `10 ثانیه`, `30 ثانیه`, `1 دقیقه`, `3 دقیقه`, `5 دقیقه`, `15 دقیقه`.

These strings corroborate the AutoSave interval choices in the settings subsystem. The actual timer mapping is separately documented: values 1–5 map through a lookup table in 1,000 ms increments, with the fallback at 10,000 ms; do not infer a direct one-to-one mapping from the UI labels alone without the setting read/write trace.

## Implementation notes

- These are useful stable error identifiers/messages for the Linux bridge and Writer adapter.
- The current Python bridge intentionally returns sanitized protocol errors; production UI/log translation can map internal error categories to these user-facing messages without exposing exception details.
- Do not treat this data block as a COM event map. The live `BeforeSave` callback registration is independently established at `0x004CD154`.
