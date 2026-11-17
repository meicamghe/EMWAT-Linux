# BPL VMT method-target reconciliation — 2026-11-17

## Scope and evidence

This note records a cross-check between the BPL's TD32 procedure inventory, Delphi VMT metadata, and the bounded machine-code trace. It is static analysis of the repository's exact `analysis-input/EmwatMethods.bpl1`; it does not claim runtime execution.

Successful evidence-producing GitHub Actions:
- `Analyze EMWAT service and BPL dispatch crosswalk`, run `44053390563`, commit `9060bb725a69f0a457934a65c1923084ae998d2b`.
- `Analyze EMWAT Methods BPL`, run `44053390613`, same commit.
- `Analyze EMWAT Word automation surface`, run `44053390585`, same commit.
- `Analyze EMWAT Word close and response chain`, run `44053390566`, same commit.
- `Analyze EMWAT Word event sink`, run `44053390597`, same commit.
- `Analyze EMWAT recovery callback contracts`, run `44053390608`, same commit.
- `Analyze EMWAT recovery SevenZip plugin`, run `44053390551`, same commit.
- `Analyze EMWAT controller content unpacking`, run `44053390505`, same commit.

All listed jobs completed successfully and uploaded their analysis artifacts. The ZIP artifact names and disassemblies are preserved in the corresponding workflow runs.

## Confirmed TEditWordDocument VMT entry

The VMT inspector artifact reports:

- Class VMT: `0x005ED764`.
- Published method-table pointer: `0x005ED778`.
- Published method-table entry count: `1`.
- Published method name: `PerformMethod`.
- Published method target: `0x005EE82C`.
- Class-name shortstring: `TEditWordDocument`.
- Leading VMT slot `+0x10`: `0x005EE82C`.

This is the decisive class-to-code relationship: the class name and its own published method table identify `0x005EE82C` as `TEditWordDocument.PerformMethod`.

## TD32 naming discrepancy — keep metadata and VMT evidence separate

The TD32 procedure inventory labels the same address `0x005EE82C` as:

`@Emwatconnector@TScanDocument@PerformMethod...`

That decorated label conflicts with the class identity recovered from the `TEditWordDocument` VMT and published method table. The method's VMT target address is stronger evidence for which class dispatches to the code at runtime; the TD32 label remains a separate symbol-table observation. Do not rename the VMT method to `TScanDocument`, nor silently rewrite the TD32 label. Keep both facts in analysis records until the compiler/linker reason for the alias or naming mismatch is resolved.

This also reinforces the general rule already used by the dispatcher analysis: resolve XML class names through the service's `GetClass("T"+className)` behavior, and use concrete VMT slot targets to establish the actual implementation. A decorated procedure name alone is not a safe runtime dispatch map.

## Method body: recovered input contract

The bounded code range `0x005EE82C–0x005EE9E4` reads the following dictionary keys:

| Parameter key | Evidence |
|---|---|
| `wordConfig` | lookup using string at `0x005EE9F4` |
| `wordBody` | lookup using string at `0x005EEA88` |
| `letterImages` | lookup using string at `0x005EEAA0` |
| `signData` | lookup using string at `0x005EEABC` |

It then calls `TWordViwer.LoadDocument` at `0x004B7724` with those four values, the `TEmwatInvokeParam*` held in the connector instance's field `+4`, and an output-string reference. The call site is `0x005EE961`.

After the helper returns, the method copies the output string into the caller-provided output and sets byte `+0x04` of the referenced invoke record to `1` (`bUnloadPkg`) at `0x005EE982–0x005EE988`. This method body does not itself set the record's `bResultSet` byte.

The adjacent constants include:
- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`
- `CoInitializing thread`
- `CoUnInitializing thread. ok.`

The method also creates/uses a worker-thread path around the call. This is evidence of the method's input and call contract, not proof that all four inputs are always present or that the helper succeeds for every request.

## Consequences for the Linux implementation

1. Preserve the four parameter names exactly and keep their payload decoding separate. In particular, do not collapse `letterImages` and `signData` into generic text fields.
2. Keep the `EditWordDocument` XML class key mapped to an explicit handler; do not expose arbitrary Delphi class lookup or infer a class from a TD32 decorated label.
3. Model the method's output string and invoke-record flags independently. The method sets `bUnloadPkg`; do not infer `bResultSet` from it.
4. Keep the worker-thread/COM initialization behavior as an open lifecycle requirement until the complete thread and callback contract is translated.
5. Do not claim that the document commit/response is complete at this method boundary. The downstream `LoadDocument`, Word event callbacks, close path, and HTTP response writer remain distinct stages.

## Remaining questions

- Why TD32 decorates `0x005EE82C` with `TScanDocument` while `TEditWordDocument` publishes that address as its `PerformMethod`.
- Whether the duplicate pointer-looking data following the published method table is additional RTTI or unrelated metadata; do not treat it as extra VMT slots without a structure-aware decode.
- Exact worker-thread ownership, COM apartment lifetime, cancellation, and exception propagation.
- Whether `wordConfig`, `wordBody`, `letterImages`, and `signData` are required, optional, or conditionally interpreted.
- Exact relationship between helper output, `bUnloadPkg`, `bResultSet`, the close callback, and final HTTP response serialization.

