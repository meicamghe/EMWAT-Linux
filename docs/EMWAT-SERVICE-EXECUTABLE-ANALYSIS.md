# EmwatService.exe static analysis

Date: 2026-11-14

## Input provenance

The original `EmwatInstaller.exe` was available in the project's personal Library. It is a Wise-style installer with an embedded Microsoft Cabinet payload:

- Installer SHA-256: `c5d595dbb3ee45acba707356318f4294faac780db54619980cc8d8181579d21d`
- Embedded CAB signature: file offset `0x2C5F5`
- CAB declared size: `0x00EECDDE` bytes
- The CAB contains 21 files, including `EmwatService.exe`, `EmwatAgent.exe`, and `EmwatMethods.bpl1`.
- Extracted `EmwatService.exe`: 679,936 bytes, PE32 GUI executable, SHA-256 `9b07e270fa216095fe6648694a4896f6f8a190e69002c6742dc894c11a002659`.
- Extracted `EmwatMethods.bpl1`: 11,106,148 bytes. Its Git blob SHA-1 is exactly `9b1943c6f9bef982e93bb635f7db6ef732e56d36`, matching the repository's `analysis-input/EmwatMethods.bpl1`. This confirms that the repository BPL is byte-for-byte the package shipped in this installer.

The CAB was read with libarchive. No original user documents, letters, or personal data were present in the extracted file set.

## Service PE layout and dependencies

`EmwatService.exe` is a 32-bit Delphi PE with sections `.text`, `.itext`, `.data`, `.idata`, `.edata`, `.rdata`, `.reloc`, and `.rsrc`. It does not expose a TD32 debug section, so the service-side analysis currently uses PE imports, RTTI, string references and x86 disassembly rather than the BPL's full TD32 procedure symbols.

Its import table includes Indy packages `IndyCore230.bpl`, `IndyProtocols230.bpl`, and `IndySystem230.bpl`, as well as `rtl230.bpl`. The executable contains RTTI names for `TIdHTTPServer`, `TIdHTTPRequestInfo`, `TIdHTTPResponseInfo`, and related Indy server types. This is consistent with the observed loopback HTTP server.

## Browser bridge: request/response mechanics

The embedded HTML/JavaScript bridge is stored in the service executable at file offset `0x7B99C` (VA `0x47C59C`). Its deobfuscated string array and code establish the following flow:

1. Listen for `window.message` events (with `attachEvent("onmessage", ...)` as a fallback).
2. Read `event.origin`, `event.source`, and `event.data`.
3. Generate `Math.floor(Math.random() * 99999)`.
4. POST `event.data` to `http://127.0.0.1:$V{myport}?invoke=` plus that generated number.
5. When XHR `readyState == 4`, send `responseText` back to the original source using `postMessage(responseText, origin)`.

This confirms that the observed `invoke=5208` is a per-message, client-generated random request value, not a stable operation ID. The operation name is in the XML body (for example, the observed `method class="EditWordDocument"` envelope). The service-side purpose of the random value—correlation, logging, or an internal request/session map—remains to be established from its request handler.

## TEmwatInvokeParam record RTTI

The service executable contains Delphi RTTI for `TEmwatInvokeParam` at file offset `0x66EB4` (VA `0x467AB4`):

- Type kind byte: `0x0E` (`tkRecord`)
- Type name: `TEmwatInvokeParam`
- Record size: `0x14` (20 bytes)
- Managed-field count: 2
- Managed fields: `System.string` at record offset 0 and `System.AnsiString` at record offset 8
- Named fields: `SessionId`, `bUnloadPkg`, `bResultSet`, `BufferIn`, `AResponseInfo`, and `AContext`

The names and managed-field metadata strongly suggest that the record carries a request/session identifier, flags, an input buffer, and Indy HTTP response/context references. The exact field-to-offset/type mapping beyond the two managed fields should be confirmed by tracing the service's record construction and use; do not infer that `SessionId` is definitely the `invoke` query value until the assignment is found.

The same record RTTI is present in `EmwatMethods.bpl1` under unit `Emwat.Sys` (typeinfo VA `0x00448084`). The TD32 symbol for `Wordviewer.OpenDoc` at `0x004B7430` includes a `PEmwatInvokeParam` parameter. This establishes that the HTTP/request context record crosses into the BPL's Word document path, although the precise service-to-`OpenDoc` call chain remains to be traced.

## Connector dispatcher context

The BPL has a `TEmwatMethod` class type, a `TEmwatMethodClass` metaclass type, and concrete connector `PerformMethod(TDictionary<AnsiString, TValue>)` procedures. `TEmwatMethod.Invoke` iterates a dictionary and dispatches through an indirect slot `+0x68`. Several concrete `PerformMethod` implementations have static method metadata, but direct CALL/immediate xrefs are absent because this path is dynamically dispatched.

The actual `TEditWordDocument.PerformMethod` name appears in the TD32 name data but has no corresponding TD32 procedure record in the current procedure inventory. It may be abstract, externally implemented, or represented through metadata not yet mapped. Do not claim its implementation has been located.

## Next analysis steps

1. Resolve the `TEmwatMethod` and connector class VMTs, including Delphi's class-name RTTI prefix layout.
2. Trace `Wordviewer.OpenDoc` callers and the `PEmwatInvokeParam` fields consumed there.
3. Trace the Indy HTTP command handler in `EmwatService.exe` from request path/query/body to the BPL method invocation. The service PE is available from the Library installer for continued local disassembly, even though it is not yet committed as a repository analysis input.
4. Identify the XML `method class="EditWordDocument"` implementation and its response serialization.
5. Reconcile the response with the user's observed apply-on-close behavior. The browser bridge returns service response text to the calling frame; it does not itself prove how document edits are committed.

