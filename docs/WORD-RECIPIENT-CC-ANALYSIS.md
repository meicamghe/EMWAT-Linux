# EMWAT Word recipient and CC print-handler analysis

Date: 2026-11-24  
Source: TD32 traces of analysis-input/EmwatMethods.bpl1 plus decoded UTF-16LE constants. Static evidence only.

## 1. Exact field identifiers

The print-handler routines contain these exact Word/config field identifiers:

| Identifier | Meaning indicated by name | Confidence |
|---|---|---|
| Receivers | Main recipient values | High |
| ReceiverDeps | Recipient department values | High |
| ccReceivers | CC recipient values | High |
| ccReceiverDeps | CC department values | High |

These are literal identifiers found in the code paths for the recipient/CC handler. They should be preserved exactly, including case, when mapping the Windows behavior to Linux.

## 2. Relevant methods and responsibilities

| Method | Address | Observed role |
|---|---:|---|
| TEmwatDocPrintHandler.PrepareDoc | 0x004A8FCC | Common document/field preparation helper used by the recipient and CC paths |
| SetCCValueForMain | 0x004A90D4 | Main-document CC preparation; reads recipient/department metadata and builds CC text |
| SetCCValueForArchive | 0x004A9464 | Archive-document CC preparation |
| SetCCValueForSelected | 0x004A9884 | Applies CC values to selected fields/documents |
| SetReceiversValueForSelected | 0x004A9A08 | Applies recipient values to selected fields/documents |
| TWordViwer.CostumizeRecAndCC | 0x004D281C | Controller-side recipient/CC customization invoked from OnControlerNotify |

The main/archive paths use the Persian prefix "رونوشت: " followed by CRLF. The selected-item path also uses "رونوشت: ", with a separate decoded literal that has no trailing CRLF. Do not normalize these strings until output parity is tested.

## 3. Controller-notify ordering

The current OnControlerNotify trace invokes CostumizeRecAndCC before the Content-related COM call mapped to TWordDocument.Get_Content. This ordering matters: recipient/CC customization may mutate the Word document before the content/recovery snapshot is taken.

The call is guarded by controller state and is followed by the Content call and the local AutoSave/SevenZip path. This is static ordering evidence; it does not prove that the same values are returned to the Almas HTTP caller.

## 4. Remaining details to resolve

1. Decode the exact separators, ordering and deduplication rules for recipient and department lists.
2. Trace how Receivers and ReceiverDeps pair with ccReceivers and ccReceiverDeps.
3. Determine whether selected recipients are inserted as text, custom document properties, fields, or a mixture.
4. Compare main, archive and selected-item outputs using a sanitized synthetic document.
5. Determine whether CostumizeRecAndCC runs for every document type or only selected workflows.

## 5. Linux implementation guidance

Keep recipient/department selection separate from Word field serialization. Preserve the four identifiers and the Persian CC prefix, but do not invent ordering or list separators. Implement only after the synthetic fixture establishes exact output and round-trip behavior.
