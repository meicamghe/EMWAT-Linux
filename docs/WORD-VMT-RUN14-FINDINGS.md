# EMWAT Word lifecycle — workflow run 14 findings

Date: 2026-11-14  
Repository commit analyzed: `75e77e2d0e331626f19f9582acd3b39a85062012`  
GitHub Actions run: `43505827015` (run number 14, conclusion: success)  
Artifact: `14076925769` (`emwat-word-lifecycle-analysis`)

## Summary

The workflow completed all 14 analysis steps successfully. The PE section-name decoding correction is effective: section names are now reported without embedded NUL bytes, and the VMT resolver emits a first-32-dword profile for each candidate.

The new profile provides useful evidence for several UI/form classes, but it does **not** resolve the controller dispatch at VMT byte offset `+0x2BC`.

## VMT profile results

The report contains five candidates whose first 32 dwords all resolve to executable addresses:

| Class | Candidate VMT | First 32 dwords |
|---|---:|---:|
| `TfrmSimpleImageEditor` | `0x004F046C` | 32 executable pointers |
| `TfrmGScanPreview` | `0x0061C1EC` | 32 executable pointers |
| `TfrmImageTools` | `0x0050662C` | 32 executable pointers |
| `TfrmScanError` | `0x004ED73C` | 32 executable pointers |
| `TGearImgProc` | `0x004EE074` | 3 executable pointers, 1 IAT-slot value, 28 unmapped/zero |

The four form candidates have coherent executable-pointer prefixes and parent metadata resolving to the VCL `TCustomForm` VMT at `0x00630140`. This is substantially stronger structural evidence than the earlier class-name/self-pointer-only candidates. The resolver still labels them **Unverified VMT candidate**; retain that caution until constructor/class-reference cross-checks confirm the exact table boundaries.

Other candidates remain weak:
- `TWordViwer` at `0x004B10A4`: 4 executable pointers, 6 non-executable mapped values, 22 unmapped/zero.
- `TEDPController` at `0x004B0DFC`: 1 executable pointer, 31 unmapped/zero.
- `TEmwatDocPrintHandler` at `0x004A22F0`: 10 executable pointers, 5 non-executable mapped values, 17 unmapped/zero.
- `TScanCommand` at `0x004F1F94`: 1 executable pointer, 31 unmapped/zero.
- `TImageProcessor`, `TResultImage`, `TMultiPageImage`, `TSetOfMultiPageImages`, `TSetOfSinglePageImages`, `TProcessResult`, `TEmwatMethod`, and `TEditWordDocument` did not produce a candidate in this report.

A pointer profile is a heuristic, not proof of VMT identity. Executable pointers can occur in other tables, and the first 32 entries do not establish the complete Delphi VMT layout or ownership of a runtime object.

## Controller dispatch remains unresolved

The trace of `0x004D281C` confirms three calls through the same virtual slot:

```asm
mov eax, [this+0x48]
mov eax, [eax]
call dword ptr [eax+0x2BC]
```

The call is repeated in exception-handling paths. The current object at `[this+0x48]` is not identified with a specific class. The artifact's `VMT-2BC-candidates.md` explicitly reports:

`No mapped candidate target was emitted by the VMT resolver.`

Therefore:
- Do not attribute slot `+0x2BC` to `TWordViwer`, `TEDPController`, or `TEmwatDocPrintHandler`.
- Do not infer a concrete method from nearby valid procedures at other offsets.
- Do not treat this static trace as proof of HTTP, XML serialization, or the observed close-time request.

## Relevance to scanning and image workflows

The newly profiled class names `TfrmSimpleImageEditor`, `TfrmGScanPreview`, `TfrmImageTools`, and `TScanCommand`, together with `TGearImgProc`, reinforce that EMWAT contains distinct scan/image-processing UI and processing components. This supports retaining image editing, scan preview, and scanner/image-processing paths as first-class parts of the Linux architecture. It does not yet establish their complete API or device integration behavior.

## Runtime facts remain separate

The user-confirmed runtime behavior remains: closing the document applies/registers changes in Almas Gam regardless of whether Save was pressed. A local POST to `127.0.0.1:1984` with `invoke=5208` and an XML response containing `EditWordDocument` / `wordConfig` was observed at close. The static callback-to-dispatch chain has not yet been connected end-to-end to that request.

## Next analysis steps

1. Identify the runtime class of the object stored at `[this+0x48]` by tracing its constructor, assignment sites, and class references.
2. Reconstruct the exact Delphi VMT layout and distinguish virtual method slots from RTTI, dynamic method, and interface metadata.
3. Use the stronger form VMT candidates as positive controls for validating the resolver, then validate the EMWAT controller candidates.
4. Resolve slot `+0x2BC` only after the owning class and table base are independently confirmed.
5. Continue tracing the bridge invocation and response serialization separately; do not infer wire behavior from the VMT profile.
