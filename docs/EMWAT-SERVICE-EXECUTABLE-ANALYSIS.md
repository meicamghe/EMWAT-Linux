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

This confirms that the observed `invoke=5208` is a per-message, client-generated random request value, not a stable operation ID. The operation name is in the XML body (for example, the observed `method class="EditWordDocument"` envelope). The handler later inspects the `invoke` query key, but the numeric query value is not copied into `TEmwatInvokeParam.SessionId`; that field is generated independently by the service. Whether the browser's numeric value is consumed for any additional purpose remains unresolved.

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



## HTTP command handler and XML class dispatch (service PE disassembly)

The service's main form RTTI identifies a published method table for `TMainForm`:

- `TMainForm` VMT: `0x0047B284`
- Published method table pointer: `0x0047B84E`
- `IdHTTPServerCommandGet`: `0x0047BF30`
- `FormCreate`: `0x0047CCD8`

The `IdHTTPServerCommandGet` body is the observed loopback HTTP command handler. Its Delphi event arguments are consistent with `Self=EAX`, `AContext=EDX`, `ARequestInfo=ECX`, and `AResponseInfo=[EBP+8]`. It initializes a local `TEmwatInvokeParam` record at `[EBP-0x1C]` and fills it as follows:

| Record offset | Field | Static evidence |
|---|---|---|
| `+0x00` | `SessionId` | A server-generated random number is converted to a string and assigned to the first managed field |
| `+0x04` | `bUnloadPkg` | Initialized to false; later set by the dispatcher |
| `+0x05` | `bResultSet` | Initialized to false; later tested to decide response handling |
| `+0x08` | `BufferIn` | Request content stream is read into a string and assigned here |
| `+0x0C` | `AResponseInfo` | Set from the HTTP event's `AResponseInfo` argument |
| `+0x10` | `AContext` | Set from the HTTP event's `AContext` argument |

The record is 20 bytes (`0x14`) and its RTTI lists the same six field names. The named offsets above are supported by the handler's explicit stores/tests and by the record's two managed-field offsets (string at 0, AnsiString at 8).

### Important correction: browser invoke value versus internal SessionId

The browser's `invoke` query value is **not** copied into `TEmwatInvokeParam.SessionId` by this handler. The handler separately calls the imported `System.Random(900000)`, adds `100000`, and passes the result through imported `SysUtils.IntToStr`. Thus the internal `SessionId` is a separate server-generated six-digit value in the range 100000–999999.

The handler calls two virtual methods on the request parameter collection at `[ARequestInfo+0xD0]` using the literal key `invoke` (calls at `0x0047BFAA` and `0x0047BFBE`). The route-selection logic uses the presence/lookup of this key to reach the XML-dispatch path. The exact semantics of the collection slots and whether the numeric value is consumed elsewhere remain unresolved. Do not describe the query value as the internal session ID.

### XML parser and method metadata object

The service-side XML parser helper is at `0x00470B38`. The dispatch helper at `0x00470D00` creates a `TMethodInfo` object and passes the request record's `BufferIn` string to the parser.

The parser:
- creates an XML document and loads the input string;
- traverses XML nodes looking for an element named `method`;
- reads that element's `class` attribute and stores it in `TMethodInfo.ClassName` at object offset `+4`;
- traverses `param` elements, reads each `name` attribute and value, and adds them to the `Params` dictionary at object offset `+8).

The service PE's `TMethodInfo` class has VMT `0x0047097C` and instance size `0x10`. Its constructor is at `0x00471214` and initializes the internal `TDictionary<AnsiString, AnsiString>` used for parameters.

### Class resolution and invocation

After parsing, the dispatcher takes the XML class name, prefixes it with the literal `T`, and calls the imported `System.Classes.GetClass(UnicodeString)` through thunk `0x00402354` (IAT target `0x00487B9C`). Therefore an XML envelope with `class="EditWordDocument"` is resolved as Delphi class `TEditWordDocument`.

The dispatcher then creates an instance of the resolved class, stores the `TEmwatInvokeParam` pointer in the instance's first field at offset `+4`, and calls instance VMT slot `+0x0C` with the parsed parameter dictionary and an output string. The BPL VMT/RTTI scan resolves this slot for all `TEmwatMethod` descendants to shared base routine `0x0046C9E0`; that routine calls `TEmwatMethod.Invoke` at `0x0046C82C`, then dispatches to the instance's subclass slot `+0x10`. For XML `class="EditWordDocument"`, `GetClass` resolves `TEditWordDocument`, whose VMT slot `+0x10` targets `0x005EE82C`. That target reads the `document` parameter and calls helper `0x004B7724`.

### Package and response path

- `TMainForm.IdHTTPServerCommandGet` calls helper `0x0047E0EC` before dispatch. Its control flow checks the package-management object at `Self+0x428` and includes the log string `Unable to load "EmwatMethods.bpl".`; classify it as a package-availability/load gate pending a complete call graph.
- The handler sets CORS response headers using `Access-Control-Allow-Origin:*`, `Access-Control-Allow-Headers:*`, and `Access-Control-Allow-Method:*`.
- On successful dispatch it logs `Method invoked successfully.`; parser/dispatch exception paths log `Calling ParseMethod exception:` and `Unable to call "invoke" method:`.
- The helper that writes the final response content and the precise response serialization contract still need separate tracing.

**Current proven request chain:**

`browser postMessage → XHR POST 127.0.0.1:<port>?invoke=<random> → TMainForm.IdHTTPServerCommandGet → TEmwatInvokeParam(SessionId, BufferIn, AResponseInfo, AContext) → XML ParseMethod → TMethodInfo(ClassName, Params) → GetClass("T"+className) → class-instance VMT slot +0x0C`.

This is now a statically supported service-to-class dispatch path. It is not yet proof that the specific `EditWordDocument` class's method completes the observed apply-on-close operation; that requires resolving its class VMT slot and response/commit path.



## Correction: concrete class VMT dispatch now resolved (lifecycle run 76)

The earlier statement that `TEditWordDocument.PerformMethod` might be abstract or external is superseded. The corrected BPL class-RTTI scan finds `TEditWordDocument` VMT `0x005ED764` and proves its slot `+0x10` points to executable code at `0x005EE82C`. The method name is present in TD32 name data, although no TD32 procedure record covers this implementation address.

The service's dynamic call at `0x00470EF6` is to VMT slot `+0x0C`. For all `TEmwatMethod` descendants this slot resolves to `0x0046C9E0`. That shared base routine calls `TEmwatMethod.Invoke` (`0x0046C82C`) and then calls the instance's VMT slot `+0x10` (`0x0046CA88`) to execute the concrete class method. Thus the full dispatch chain is:

`GetClass("T"+XML class) → construct instance → set instance field +4 to TEmwatInvokeParam* → VMT+0x0C (0x46C9E0) → TEmwatMethod.Invoke (0x46C82C) → VMT+0x10 (class-specific method)`.

For `EditWordDocument`, the final method target is `0x005EE82C`. Its code reads the `document` parameter from the parsed dictionary and calls helper `0x004B7724`. That helper and the full `TEditWordDocument` body remain under analysis.

The corrected VMT scan also recovered these other method targets: `TScanDocument=0x005EEB48`, `TFaxDocument=0x005EEDFC`, `TGetEmwatVersion=0x005EF110`, `TSetEmwatVersion=0x005EF218`, `TUpgradeEmwat=0x005EF24C`, `TImageEdition=0x005EF300`, `TEditExcelWorkBook=0x005EF8AC`, `TCompareWordDocument=0x005EFC54`, `TShowEmwatSetting=0x005EFD4C`, `TShowLastEditedDocs=0x005EFE4C`, and `TShowSendLog=0x005EFF4C`.

**Important naming caveat:** some TD32 procedure labels differ from the class whose VMT slot points to the code address. For example, `TEditExcelWorkBook` VMT slot `+0x10` points to `0x005EF8AC`, whose TD32 label is `TCompareWordDocument.PerformMethod`. Keep the VMT target and TD32 label separate until the method body semantics resolve the discrepancy.

### Additional route branches and common dispatcher callers

The same `TMainForm.IdHTTPServerCommandGet` body checks three request parameter keys in the request parameter collection at `[ARequestInfo+0xD0]`:

| Key | Check site | Branch purpose |
|---|---:|---|
| `invoke` | `0x0047BF9D` | Main XML method dispatch path |
| `init` | `0x0047C102` | Returns the embedded JavaScript bridge and logs the script request |
| `heartbeat` | `0x0047C25F` | Handles the Agent heartbeat path |

This confirms the local service has separate bridge-initialization and Agent-heartbeat routes in addition to the browser-to-XML method route. The numeric `invoke` value is not assigned to the record's `SessionId`; the handler's record gets its own random six-digit identifier as described above.

The callback register/stack usage matches the Indy event signature: EDX is `AContext`, ECX is `ARequestInfo`, and `[EBP+8]` is `AResponseInfo`. The PE RTTI contains `TIdHTTPRequestInfo` and its fields/properties `FParams`/`Params`, `FPostStream`/`PostStream`, and `FRemoteIP`/`RemoteIP`. Combined with the handler's use, the offsets map with high confidence as `[ARequestInfo+0xD0] = Params`, `[ARequestInfo+0xD4] = PostStream`, and `[ARequestInfo+0xDC] = RemoteIP`. The handler queries the PostStream object for a size-like value, obtains a buffer, and calls its virtual slot `+0x0C` with a buffer/length pair before assigning the resulting string to `BufferIn`. The object is therefore identified as the request-body stream; the exact names/signatures of its two virtual methods remain unresolved.

The shared dispatcher at `0x00470D00` has three additional direct callers in the service PE:

- `0x0047D91A`
- `0x0047DB5E`
- `0x0047DDA2`

These routines construct local `TEmwatInvokeParam` records and pass embedded XML to the same class-dispatch path. Their embedded XML includes internal method classes such as `ShowEmwatSetting` and `ShowSendLog`. Consequently, `0x00470D00` is a reusable service-side method dispatcher used both by the HTTP command handler and by internal service routines.

**Evidence boundary:** the static chain now proves request-body-to-record-to-XML-class-resolution-to-`TEmwatMethod.Invoke`-to-concrete `TEditWordDocument` VMT slot `+0x10` (`0x005EE82C`). The body/helper semantics at `0x005EE82C` / `0x004B7724`, the final response serialization/transport, and the upstream Word-close event that initiates the request remain under investigation.

### Response result flag and HTTP send path

The dispatcher at `0x00470D00` checks `TEmwatInvokeParam.bResultSet` immediately after the class method returns:

- If `bResultSet != 0`, the connector has marked the response as already handled; the service skips its default output-string response path.
- If `bResultSet == 0`, the service checks that the output string is nonempty and `AResponseInfo` at record offset `+0x0C` is non-null.
- It assigns the output string to `AResponseInfo.ContentText` at object offset `+0xBC), calls helper `0x004610FC`, then sets `bResultSet = 1`.

The helper `0x004610FC` operates on the Indy response-info object and examines status/response fields before sending; it is the response-send path used by the default branch. Its full imported/virtual call mapping is still being traced.

This means the Word connector can either write the HTTP response itself and set `bResultSet`, or leave the flag false and return a string for the service's default response handling. The observed `wordConfig` XML response may therefore be produced by the connector-specific branch; inspect `TEditWordDocument` for writes to `AResponseInfo` and `bResultSet` before assigning the response serialization to the generic service handler.


## TEditWordDocument method parameters and response behavior

The concrete method target `TEditWordDocument` at `0x005EE82C) has now been disassembled through its VMT slot `+0x10`. It retrieves these four named entries from the parsed parameter dictionary:

- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`

It creates/starts a worker thread and logs `CoInitializing thread`. The method passes the four parameter values, the `TEmwatInvokeParam*` stored in the instance's field `+4`, and an output-string reference to helper `0x004B7724`:

`wordConfig, wordBody, letterImages, signData, TEmwatInvokeParam*, outputString → 0x004B7724`.

After the helper returns, the method copies the output string into the result string supplied by the base dispatcher and sets record byte `+0x04` (`bUnloadPkg`) to true. It does **not** set `bResultSet` (record byte `+0x05`) in this body.

This explains the generic service response path:
1. `TEditWordDocument` returns the helper's output string.
2. `bResultSet` remains false.
3. The service dispatcher writes the output string to `AResponseInfo.ContentText`, calls `0x004610FC` to send the HTTP response, then sets `bResultSet=true`.
4. The separate `bUnloadPkg=true` flag requests package unload/cleanup after the method call.

The helper `0x004B7724` is now the critical next target: it receives the four Word payload values and request context and appears to own the actual document/Word automation and construction of the response string. Its complete TD32 procedure/caller traces are included in lifecycle run 77.

The parameter names and response behavior align with the user's observed `EditWordDocument` response containing `wordConfig`, but the exact XML generation and close-time commit semantics must be confirmed inside `0x004B7724` and its downstream calls.
