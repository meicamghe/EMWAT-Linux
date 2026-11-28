# Parallel reverse-engineering follow-up — 2026-11-28 (Run 30)

## Scope and evidence

Run 30 advances the three requested proof tracks using existing GitHub artifacts and public Embarcadero interface documentation. No new workflow was dispatched and no vendor binary was executed.

Artifacts reviewed:
- Scanner/XML: `15253432241`, `15253908265`, `15252222043`.
- TIFF/GDI+: `15254911990`, `15255092521`, `15253721199`, `15253761384`, `15252962538`.
- Hidden print worker: `15253702066`.

## 1. XMLRTL: core helper semantics now identified

`0x0044B498` is the `IXMLNode.HasAttribute` wrapper; `0x0044B488` is the `IXMLNode.GetAttribute` wrapper; and `0x0044B4C0` is the `IXMLNode.SetAttribute` wrapper. The setter/getter direction was established from actual register and value flow, not TD32 labels. Public XMLRTL method contracts corroborate the argument semantics.

`0x0044B4D8` is the child-node collection/navigation path: the caller obtains the child-node interface and then resolves the literal child name `constraints` through the returned list interface. The exact helper-internal split and `0x0044B508` ForceSinglePageFiles default helper remain open.

TD32 symbol direction is unreliable in this generated accessor block: `0x004EA94C` reads the `constraints` child despite its ColorDepth getter label; `0x004EAA08`, `0x004EAB58`, `0x004EACB0`, and `0x004EAE08` are numeric attribute getters despite `Set_*` labels; `0x004EAAD8`, `0x004EAC2C`, and `0x004EAD84` are attribute setter-shaped paths despite `Get_*` labels. The exact property names are taken from UTF-16 literals.

Numeric absent-value semantics remain confirmed: HasAttribute false returns zero without GetAttribute/conversion; present values proceed through Variant-to-integer conversion. `MaxFileSize` remains KiB (`<<10`) before comparison with stream size in bytes.

## 2. THidePrintingThread: file appearance is the completion predicate

`0x004032C0` is called with a UnicodeString path and `DL=1`, matching `System.SysUtils.FileExists(FileName, FollowLink=True)`. The worker first checks a constructed path and deletes a stale pre-existing file through helper `0x004026B4`; it then polls a subsequently constructed path with 10 ms sleeps and a computed time threshold. A later FileExists true branch sets the worker success byte.

Thus the Worker is waiting for generated filesystem output, not merely queue disappearance. Exact path strings, delete API identity, and the producer component are still open. The 3,000 ms / 50 ms retry and status-query path remains distinct from the 10 ms file poll.

## 3. GDI+: functional Save/SaveAdd cycle resolved

PE imports and GNU `objdump -p` confirm the four relevant thunks: `0x00481C64` SaveImageToFile, `0x00481C6C` SaveImageToStream, `0x00481C74` SaveAdd, `0x00481C7C` SaveAddImage. Direct wrapper callers at `0x00490ABF` and `0x00490AFE` prove the two SaveAdd variants.

`SeparteImages` interface calls map by ABI and control flow: `+0x48` at `0x004A0470` is initial SaveImageToFile; `+0x5C` at `0x004A0507` is SaveAddImage inside the page loop; `+0x58` at `0x004A0568` is SaveAdd after the loop, with Flush value 20. The initial Save writes the first frame; subsequent page images are appended; final Flush closes the multipage encoder sequence.

The raw TGPImage RTTI/interface metadata is still not a flat VMT. The live dispatch mapping above is high-confidence from arguments, import targets and loop/finalization position; it is not a claim that every raw VMT dword has been reconstructed.

## Next proof gates

1. Recover exact Worker path literals and identify the producer/writer of the awaited file.
2. Resolve `0x004026B4`, `0x00404494`, and the complete status structure/API used in retry handling.
3. Disassemble XMLRTL helpers directly, especially `0x0044B4D8` and `0x0044B508`, and close ForceSinglePageFiles default semantics.
4. Obtain a runtime multipage TIFF fixture and validate the final frame/flush behavior and Almas acceptance.

## Change boundary

No production code, runtime behavior, build, release, merge, rebase, or new GitHub Actions run was performed.