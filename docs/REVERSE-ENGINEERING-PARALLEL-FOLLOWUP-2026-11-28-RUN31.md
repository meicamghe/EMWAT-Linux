# Reverse-engineering parallel follow-up — 2026-11-28 Run 31

## Scope

Cross-correlate the existing scanner XML, hidden print worker, printer import, and GDI+ interface artifacts. No new GitHub Actions workflow was started and no source binary was available for a fresh disassembly pass.

## 1. XMLRTL: named child lookup is now functionally closed

The Get_ColorDepth path at 0x004EA94C:
- calls 0x0044B4D8 with the current XML node and an output interface slot;
- calls the returned interface's first custom-method slot with the literal node name "constraints";
- receives another XML-node interface.

This matches the documented XMLRTL chain IXMLNode.ChildNodes -> IXMLNodeList.FindNode("constraints"). ChildNodes returns an IXMLNodeList; FindNode(NodeName) returns the named IXMLNode. This identifies the call sequence at high confidence, though it does not split the internal implementation of 0x0044B4D8 beyond its ChildNodes-return role.

References:
- https://docwiki.embarcadero.com/Libraries/Alexandria/en/Xml.XMLIntf.IXMLNode.ChildNodes
- https://docwiki.embarcadero.com/Libraries/Athens/en/Xml.XMLIntf.IXMLNodeList.FindNode

The 0x0044B508 helper used by Get_ForceSinglePageFiles remains open. The accessor supplies forceSinglePageFiles, a global interface/context argument, and a zero-valued stack argument before a Boolean conversion helper. That call shape does not prove what happens when the attribute is absent.

## 2. THidePrintingThread: ShellExecuteW and OS-version branch resolved

Cross-artifact correlation of procedure-004A0E88.md with the printer import/thunk artifact resolves two previously ambiguous calls:

- 0x00402818 is the GetVersionEx thunk (TD32's decorated signature names OSVERSIONINFOEXW).
- 0x00404494 is a six-argument thunk to shell32.dll!ShellExecuteW through IAT 0x0062F9CC.

At 0x004A1236, the worker writes 0x114 (276) to the structure size before calling GetVersionEx. That is the size of the basic wide OSVERSIONINFOW layout, not the 284-byte OSVERSIONINFOEXW layout. The decorated TD32 suffix and caller's actual size disagree; runtime evidence favors the basic OSVERSIONINFOW structure. The worker reads dwMajorVersion at offset +0x04 and branches when it is greater than 5.

The two branches use different operation-string pointers (0x004A18B0 and 0x004A18FC). Each branch contains up to three staged ShellExecuteW calls. Later stages are gated on the preceding return being greater than 32; the observed delays include 3,000 ms and 50 ms. Microsoft documents that ShellExecuteW returns a value greater than 32 on success: https://learn.microsoft.com/en-us/windows/win32/api/shellapi/nf-shellapi-shellexecutew.

This does not identify the actual launch targets or arguments. The string data at 0x004A1864, 0x004A1894, 0x004A18B0, 0x004A18BC, 0x004A18D8, 0x004A18E0, and 0x004A18FC is not present in the downloaded artifacts. Also, ShellExecuteW success is not the worker completion signal: the worker sets its success byte at 0x004A1370 only after the final FileExists check at 0x004A121B succeeds.

The operational completion chain is therefore:
1. Build output path and delete a stale output if it exists.
2. Poll the relevant output condition with 10 ms sleeps and calculated deadlines.
3. If the file is still absent, execute the OS-version-specific ShellExecuteW stage sequence.
4. Check final output-file existence.
5. Set the worker success byte only when that final check succeeds.

This is distinct from the Word spooler EnumJobsW queue-disappearance condition and from the JobFinishes.GAM sentinel.

## 3. GDI+: distinguish functional interface-slot mapping from raw VMT recovery

The functional SeparteImages sequence remains mapped with high confidence:
- interface +0x48 at 0x004A0470: initial SaveImageToFile;
- interface +0x5C at 0x004A0507: SaveAddImage for subsequent pages inside the loop;
- interface +0x58 at 0x004A0568: final SaveAdd with EncoderValueFlush=20.

The first frame is written by the initial Save; the loop skips re-adding that first frame; later images are appended; the final Flush terminates the multipage encoder sequence. The PE import and wrapper crosswalk independently identifies GdipSaveImageToFile, GdipSaveAddImage, and GdipSaveAdd.

The metadata dump around 0x0047DD84 contains Delphi interface/type RTTI (including NativeHandle / TGdiPlusBase names), not a flat implementation-pointer array. The TGPImage class slot points into interface metadata at 0x0047DD2C. Consequently, the functional slot map is grounded in call ABI, wrapper bodies, import targets, and control flow; the raw interface VTable pointer table is not fully reconstructed from the current artifacts. Do not present the RTTI dwords as VMT entries or infer unobserved slot targets.

## Remaining exact blockers

1. Recover raw data for the string addresses used by the ShellExecuteW stages and resolve 0x004026B4 precisely.
2. Disassemble 0x0044B508 to establish the ForceSinglePageFiles missing-attribute default.
3. Obtain the actual GDI+ interface method-table bytes if a raw slot-to-code-VA map is required; current artifacts support the operation-level Save/SaveAdd map only.
4. Obtain a real multipage TIFF fixture before accepting Linux TIFF output behavior. This remains lower priority per the current project direction.

## Evidence and execution status

- Existing artifact crosswalk: hidden worker artifact 15253702066; printer import/queue artifact 15254533525; GDI+ interface metadata artifact 15255092521; GDI+ method-detail artifact 15253761384; scanner XML artifacts 15252222043 and 15253908265.
- Public API contracts used only to validate interface/API semantics are linked inline above.
- No tests were run, no new CI workflow was started, and no Windows or Linux release was built.
