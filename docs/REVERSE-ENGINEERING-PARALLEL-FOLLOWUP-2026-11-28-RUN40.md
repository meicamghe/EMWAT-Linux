# Reverse-engineering parallel follow-up — 2026-11-28 Run 40

## Connector class-name occurrences versus VMT resolution

The completed Run-67 `image-ui-and-vmt` artifact `15260427307` includes `image-ui/image-scanner-vmt-slots.md`, produced by `tools/resolve_delphi_vmt_slots.py`.

For the connector-related classes it reports:

| Class | Shortstring occurrences | Standard VMT candidate |
|---|---:|---|
| `TEmwatMethod` | 2 | None |
| `TEditWordDocument` | 2 | None |
| `TScanDocument` | 2 | None |
| `TWordViwer` | 2 | One unverified candidate at `0x004B10A4` |

The `TWordViwer` candidate is not safe to accept as a VMT: its first 32 dwords profile has only four executable pointers, and its parent pointer `0x0062EEA4` resolves to a `System@PVariant`-style type name rather than a credible parent class. It is explicitly marked unverified by the resolver.

This does not prove the classes are absent. It proves the current standard Delphi VMT heuristic cannot resolve these particular class structures. Combined with Run 39's TD32 name/key mismatch, the next useful target is the custom RTTI/interface/registration data that associates the two occurrences of `TEditWordDocument` with a handler instance and its method table.

## Impact

- `TEditWordDocument` class name is present in the BPL twice.
- No standard-layout VMT candidate was accepted.
- No `TEditWordDocument.PerformMethod` TD32 symbol was found in the selected connector symbol scan.
- The runtime handler remains unresolved; do not equate a missing method symbol with a missing handler.
- The exact Almas HTTP request/response remains the authoritative external protocol fixture.

Evidence:
- Run-67 artifact `15260427307`, `image-ui/image-scanner-vmt-slots.md`.
- Run-67 artifact `15260640277`, `connector-handlers/selected-symbols.txt` and `symbol-index.md`.

No source code or workflow was modified.
