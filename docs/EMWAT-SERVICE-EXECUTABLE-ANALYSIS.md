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

This confirms that the observed `invoke=5208` is a per-message, client-generated random request value, not a stable operation ID. The operation name is in the XML body (for example, the observed `method class="EditWordDocument"` envelope). The handler later checks the `invoke` query key, but the embedded bridge shows the numeric value is generated only to make each XHR URL unique. It is not a method ID, correlation token, or `TEmwatInvokeParam.SessionId`; that field is generated independently by the service.

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

The handler calls two virtual methods on the request parameter collection at `[ARequestInfo+0xD0]` using the literal key `invoke` (calls at `0x0047BFAA` and `0x0047BFBE`). The route-selection logic uses the presence/lookup of this key to reach the XML-dispatch path. The exact semantics of the two collection slots are still not named, but the embedded JavaScript confirms that the numeric value is only a per-request URL nonce/cache-buster. Do not describe it as a method ID or internal session ID.

### XML parser and method metadata object

The service-side XML parser helper is at `0x00470B38`. The dispatch helper at `0x00470D00` creates a `TMethodInfo` object and passes the request record's `BufferIn` string to the parser.

The parser:
- creates an XML document and loads the input string;
- traverses XML nodes looking for an element named `method`;
- reads that element's `class` attribute and stores it in `TMethodInfo.ClassName` at object offset `+4`;
- traverses `param` elements, reads each `name` attribute and value, and adds them to the `Params` dictionary at object offset `+8).

The service PE's `TMethodInfo` class has VMT `0x0047097C` and instance size `0x10`. Its constructor is at `0x00471214`; it loads the dictionary class reference at `0x004699E4` (VMT `0x00469A3C`, typeinfo `0x0046A054`, class name `TDictionary<System.AnsiString,System.AnsiString>`), constructs it via `0x0046AA70`, and stores the dictionary pointer at `TMethodInfo + 0x08`. `ParseMethod` passes that exact pointer to the XML parameter parser.

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

This confirms the local service has separate bridge-initialization and Agent-heartbeat routes in addition to the browser-to-XML method route. The browser's numeric `invoke` value is only a URL nonce/cache-buster; the handler's record gets its own random six-digit `SessionId` as described above.

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

The helper `0x004610FC` is identified by its RTTI method-name reference as `TIdHTTPResponseInfo.WriteContent`. Its body examines the response status/content fields, sends through the Indy response interface, clears the temporary ContentText pointer, and performs response cleanup. The same helper is called from ParseMethod after invocation (`0x00470F34`) and from the MainForm init/heartbeat branches (`0x0047C237`, `0x0047C2A9`). The exact names/signatures of each Indy interface slot remain to be resolved. This is the **service-side generic sender**. It is distinct from the BPL-side imported `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` thunk at `0x0040448C`, which `TWordViwer.LoadDocument` calls after assigning its `response-word` XML and before setting `bResultSet=true`; that direct connector response bypasses the generic fallback.

This means the Word connector can either write the HTTP response itself and set `bResultSet`, or leave the flag false and return a string for the service's default response handling. The observed `wordConfig` XML response may therefore be produced by the connector-specific branch; inspect `TEditWordDocument` for writes to `AResponseInfo` and `bResultSet` before assigning the response serialization to the generic service handler.


## TEditWordDocument method parameters and response behavior

The concrete method target `TEditWordDocument` at `0x005EE82C) has now been disassembled through its VMT slot `+0x10`. It retrieves these four named entries from the parsed parameter dictionary:

- `wordConfig`
- `wordBody`
- `letterImages`
- `signData`

It creates/starts a worker thread and logs `CoInitializing thread`. The method passes the four parameter values, the `TEmwatInvokeParam*` stored in the instance's field `+4`, and an output-string reference to helper `0x004B7724`:

`wordConfig, wordBody, letterImages, signData, TEmwatInvokeParam*, outputString → 0x004B7724`.

After the helper returns, the method copies the helper's output string into the base dispatcher's output string and sets record byte `+0x04` (`bUnloadPkg`) to true. It does not set `bResultSet` in the `TEditWordDocument` body itself.

**Correction from the complete LoadDocument range:** helper `0x004B7724` receives the `TEmwatInvokeParam*` as stack argument `[EBP+0x0C]` and uses it directly. On the non-empty-result path at `0x004B7F9C–0x004B7FBF), it:
1. obtains `AResponseInfo` from record offset `+0x0C`;
2. assigns the generated XML output string to `AResponseInfo.ContentText` at object offset `+0xBC`;
3. calls imported `IdCustomHTTPServer.TIdHTTPResponseInfo.WriteContent` (thunk `0x0040448C`, IAT slot `0x0062F9C0`);
4. sets record byte `+0x05` (`bResultSet`) to true.

Therefore, for a successful non-empty `EditWordDocument` result, the generic service dispatcher sees `bResultSet=true` and skips its fallback response branch. The earlier interpretation that the generic dispatcher always sends this method's output was based on the connector body alone and an incomplete LoadDocument trace; it is superseded.

## LoadDocument helper reached from the Word-edit VMT target (lifecycle run 77)

The TD32 procedure at `0x004B7724` is:

- Symbol: `Wordviewer.TWordViwer.LoadDocument`
- Module: `ScanRequestXML`
- Range: `0x004B7724–0x004B8A83`
- Size: `0x1360` bytes

The only direct TD32-bounded caller is the call at `0x005EE961), inside the code at `0x005EE82C`. The caller passes:
- EAX = `wordConfig`
- EDX = `wordBody`
- ECX = `letterImages`
- stack argument 1 = output-string reference
- stack argument 2 = `TEmwatInvokeParam*` (read from the connector instance's field `+4`)
- stack argument 3 = `signData`

The TD32 caller label for `0x005EE82C` is `TScanDocument.PerformMethod`, but corrected class RTTI shows that this code address is the `+0x10` target in the `TEditWordDocument` VMT. Preserve this naming discrepancy explicitly; do not silently rewrite the TD32 symbol.

Within `LoadDocument`, the code:
- parses `wordConfig` as XML and checks the `word-document` root;
- writes the `wordBody` bytes to a stream;
- stores `signData` in Wordviewer state at field `+0xF4`;
- processes configuration and image paths, including `image/tif`, `Payam-e-Dowlat` handling and a `view` branch;
- creates/configures the Wordviewer object through `0x004D0D24` and `0x004D1454`;
- calls `TWordViwer.OnTmrAutoSave` at `0x004B8A84` with the viewer and configuration string;
- reads the generated temporary document file with a retry loop (limit 100), adds its content to the result, and deletes the temporary file.

The helper references response metadata strings `application/msword` and `success`, logs `Word doc content added to result.` and `OpenDoc function succeed.`, then writes the serialized result through Indy `WriteContent`. The exact XML element layout and encoding still need byte-for-byte comparison with a captured runtime response.

### Word automation callback registration reached from LoadDocument

The `OnTmrAutoSave` routine at `0x004B8A84` stores the configuration and registers these callback pointers on the Word automation event record:

| Event-record field | Function VA | Export name / code evidence |
|---:|---:|---|
| `+0x80` | `0x004CD154` | `WordAppDocumentBeforeClose`; body logs `Document.OnBeforeClose Called.` and prompts whether to save changes |
| `+0x90` | `0x004CD54C` | `WordAppDocumentBeforeSave`; body logs `Document.OnBeforeSave called.` |
| `+0x98` | `0x004CD9C0` | Export name `WordAppNewDocument`; body includes Activation/Quitword/document-count handling |
| `+0x88` | `0x004D00AC` or `0x004CE030` | BeforePrint handlers selected by viewer state |

The function-name mapping above was checked against the BPL export address/name tables and the strings inside each body. This corrects the earlier callback labels that swapped the three addresses. The TD32 symbol/export naming for the `+0x98` callback should still be treated carefully: its code includes an `Activation` path as well as `Quitword` logic.

#### Actual main Word close callback: 0x004CD154

The registered `0x004CD154` callback is the main `TWordViwer.WordAppDocumentBeforeClose` path. Its body contains these strings:

- `Document.OnBeforeClose Called.`
- Persian prompt: `محتويات اين سند تغيير كرده است. آيا مايل به ثبت تغييرات هستيد؟`
- `Save msgBox triggered. result: %d`
- `Document.OnBeforeClose succeed.`

The close handler first calls `TWordViwer.RollBackOriginalOptions` at `0x004CB108`, then queries the active Word document's `Saved` property through interface slot `+0xD8`; the typed `TWordDocument.Get_Saved` wrapper at `0x0042BD94` confirms this slot. It tests the returned Boolean before prompting. Cancel sets the callback's `Cancel` word to `0xFFFF`. For Yes it initializes the first OleVariant argument to `-1`; for No it initializes it to `0`. It then calls the active `Wordxp._Document` interface at slot `+0x29C` with three OleVariant arguments. The BPL export table identifies the three-argument wrapper as `TWordDocument.Close` at `0x00430070`, which dispatches the same interface slot `+0x29C`. Thus this is the explicit `Close(SaveChanges, OriginalFormat, RouteDocument)` overload path; the first argument carries the Yes/No save decision. The callback also calls a `_Document` interface slot `+0xD8`; its exact property/method name remains to be mapped.

The similarly named routine at `0x004CCBBC` remains a different nested helper called from `FillImgFldsForPrint`; it is not the registered close callback. A separate `uSendLog.TfrmShowAutoSaveFiles.WordAppDocumentBeforeClose` at `0x005EC589` belongs to the autosave-preview form and is unrelated to the main letter editor's callback.

The registered BeforeSave callback at `0x004CD54C` logs `Document.OnBeforeSave called.`, checks the `view`/permission state, dispatches `Wordxp._Document` slot `+0x2BC` (mapped to `PrintOutOld()`), and calls `TWordViwer.SetDocCaption` at `0x004C5E04`. The close callback itself has no direct HTTP request call in its body. It prompts and invokes Word's Close overload; the next trace must follow its viewer helpers and the BeforeSave path to determine how the final content reaches the browser/service.



## Request routing and PostStream source (2026-11-14)

The handler's request-parameter collection exposes three route keys:
- `invoke`: enters the XML method-dispatch path described above;
- `init`: returns the embedded JavaScript bridge;
- `heartbeat`: handles the Agent heartbeat request.

The numeric browser `invoke` value selects the route but is not copied into `TEmwatInvokeParam.SessionId). The server independently creates the six-digit internal `SessionId`.

The `TIdHTTPRequestInfo` object fields used by the handler are now identified with high confidence:
- `[ARequestInfo+0xD0]` = `Params`
- `[ARequestInfo+0xD4]` = `PostStream`
- `[ARequestInfo+0xDC]` = `RemoteIP`

The handler reads a size-like value from `PostStream`, then calls its virtual slot `+0x0C` with a buffer/length pair to populate `TEmwatInvokeParam.BufferIn`. The exact stream virtual method names and signatures remain unresolved; do not name them as `Read`, `ReadBuffer`, or `Size` without matching the correct Indy stream VMT.

The service also contains internal call sites that invoke the shared XML dispatcher with embedded method XML, including `ShowEmwatSetting` and `ShowSendLog`. These are separate service-originated calls and should not be mistaken for browser POST requests.


## Embedded browser bridge deobfuscated (init route)

The `init` route returns a 508-character embedded JavaScript bridge from service VA `0x0047C59C`. The script is ASCII and deobfuscates to:

```javascript
var _origin = null;
var _source = null;

function invoke(event) {
    _origin = event.origin;
    _source = event.source;

    var xhr = new XMLHttpRequest();
    var nonce = Math.floor(Math.random() * 99999);

    xhr.open("POST", "http://127.0.0.1:$V{myport}?invoke=" + nonce);
    xhr.onreadystatechange = function () {
        if (xhr.readyState == 4) {
            _source.postMessage(xhr.responseText, _origin);
        }
    };
    xhr.send(event.data);
}

try {
    window.addEventListener("message", function (event) {
        invoke(event);
    }, false);
} catch (err) {
    window.attachEvent("onmessage", function (event) {
        invoke(event);
    }, false);
}

parent.postMessage("<inited />", "$V{host}");
```

This establishes the complete browser bridge behavior:

1. The parent web application sends a `window.postMessage` event to the bridge.
2. The bridge forwards `event.data) unchanged as the HTTP POST body to `127.0.0.1:$V{myport}`.
3. `Math.floor(Math.random()*99999)` is used only to vary the `?invoke=` URL value; the script does not use it to correlate the response or identify the method.
4. When the XHR reaches readyState 4, the bridge sends `responseText` back to the original `event.source` using the original `event.origin`.
5. After initialization, it posts `<inited />` to the parent with the configured host placeholder.

Combined with the service handler, the proven data path is:

`parent postMessage(event.data) → XHR POST (?invoke=random URL nonce) → TIdHTTPRequestInfo.PostStream → TEmwatInvokeParam.BufferIn → XML/class dispatch → TEditWordDocument/LoadDocument → TIdHTTPResponseInfo.WriteContent → XHR responseText → original event.source.postMessage(responseText, origin)`.

The bridge itself is a generic message forwarder; it does not contain document-close-specific logic. Therefore the remaining question is which parent-page code posts the close-time XML message after Word's `BeforeClose` callback and how it obtains the updated document/configuration payload.



## Indy response writer method resolution — 2026-11-16

Source: workflow 43829779730, artifact 14208036695; helper trace workflow 43830209429, artifact 14208551179.

### Published method names and targets

The service executable's Delphi method RTTI associates these methods with executable addresses:

| Method | Target | Evidence |
|---|---:|---|
| WriteContent | 0x004610FC | method RTTI pointer reference at raw offset 0x5B561 |
| ServeFile | 0x00460E48 | method RTTI entry adjacent to the method name |
| SmartServeFile | 0x00460FAC | method RTTI entry adjacent to the method name |

No direct immediate CALL site was found for these published methods in the service .text scan. They may be reached through an indirect/VMT or method-RTTI dispatch path; this must be resolved before assigning a caller.

### WriteContent behavior

The disassembly at 0x004610FC supports the following bounded observations:

- It ensures response-header preparation through helper 0x004612F4 when the response state flag at object offset +0xC2 is not set.
- It suppresses body output for HTTP status codes 100, 204, and 304.
- It has a content-text branch using the response object's +0xBC field and a content-stream branch using +0xB8.
- When neither content stream nor content text is available, it constructs a fallback HTML body and uses a UTF-8 HTML content type.
- It clears the temporary content-stream field and calls cleanup helper 0x00460764.

The helper trace identifies 0x004609EC as a routine that stores the response status code at object offset +0xB0 and selects status-specific response handling. The exact names of the underlying context-interface slots are not yet proven.

### SmartServeFile behavior

- It reads the If-Modified-Since header.
- It parses/compares a timestamp against file metadata.
- It can set response status 404 (0x194) or 304 (0x130) and delegates file output through the response object's VMT slot +0x1C (the ServeFile method).
- The exact branch condition and timestamp tolerance should be rechecked with the helper/constant trace before documenting a strict cache decision rule.

Evidence boundary: this resolves the service's generic HTTP response writer, not yet the final Almas EditWordDocument response path or the exact body serialization for its close-time registration.


## MainForm CommandGet and concrete response-write callsites — 2026-11-16

Source: workflow 43831365563, artifact 14208144442.

- Delphi method RTTI resolves TMainForm.IdHTTPServerCommandGet to 0x0047BF30.
- The handler reads the request parameter named invoke (UTF-16 string at 0x0047C360) and routes the invoke path through helper 0x0047E0EC; package lifecycle/logging helpers include 0x0047E2D4 and 0x0047D2C8. The exact close-time response body for this invoke branch still needs to be traced.
- The same handler has separate init and heartbeat routes. The init branch reads parameter init, applies CORS response headers (Access-Control-Allow-Origin, Access-Control-Allow-Headers, Access-Control-Allow-Method), and returns the embedded initialization HTML/JavaScript at 0x0047C59C. The embedded script sends POST requests to 127.0.0.1:$V{myport}?invoke=<nonce> and forwards responseText to the parent window.
- The init branch assigns the response text to TIdHTTPResponseInfo.ContentText at object offset +0xBC and directly calls WriteContent at 0x004610FC from 0x0047C237. The heartbeat branch checks parameter heartbeat and also calls WriteContent at 0x0047C2A9.
- This direct callsite confirms the field layout: ContentText is +0xBC; ContentStream is +0xB8. Earlier draft notes that reversed these fields have been corrected.
- Evidence boundary: the generic HTTP response writer is now directly tied to the MainForm handler for init/heartbeat. The invoke branch's plugin result serialization and exact close-time Almas response envelope remain the next target.


## Invoke request parser trace — 2026-11-16

Source: workflow 43832144163, artifact 14209690263.

- TMainForm.IdHTTPServerCommandGet (0x0047BF30) routes the invoke query branch through ParseMethod wrapper 0x00470D00.
- 0x00470D00 calls parser worker 0x00470B38 and contains exception text references for "Calling ParseMethod exception" and "XML is not valid".
- The parser recognizes root tag "emwat", its "version" attribute, and child tags "method", "class", and "param"; the "param" child uses the "name" attribute.
- Parser token helper 0x0046ADBC compares the token names and routes recognized elements. Helper 0x0046A7A4 appends a three-value record to the parser's dynamic collection (three adjacent string/value slots); exact semantic names for all three record fields remain unconfirmed.
- This is the service-side XML parsing stage. The BPL-side TEmwatMethod.Invoke dictionary contract is known separately; the conversion/link from these parser records to the BPL invocation and the exact response payload still need proof.

## Delphi runtime package and class-resolution imports

The PE import table confirms that `EmwatService.exe` imports `LoadPackage`, `UnloadPackage`, `StartExe`, `GetClass`, `ClassCreate`, `ClassDestroy`, `TObject.InheritsFrom`, `ClassParent`, `ClassName`, and two `GetProcAddress` entries. Exact callsites now confirm `LoadPackage` via thunk `0x00402174` at `0x0047E15F`, and `GetClass` via thunk `0x00402354` at `0x00470E07`. `ClassCreate` via thunk `0x00401158` at `0x00471220` and `ClassDestroy` via thunk `0x00401160` at `0x0047127F` form the constructor/destructor pair for the `TMethodInfo` parser metadata object. The destructor beginning at `0x00471258` frees its Params dictionary at object offset `+0x08` before invoking `ClassDestroy`. These calls must not be conflated with creation of the dynamically resolved BPL method object. The latter is constructed by the class-reference path in `ParseMethod` after `GetClass`, then dispatched through the recovered VMT slots. `StartExe` at `0x004014BA` belongs to package startup initialization; `GetProcAddress` at `0x00401720` and its wrapper at `0x00401D84` belong to runtime dynamic-symbol resolution, not a second EMWAT method dispatch path.

## TMainForm published event/method table

The VMT at `0x0047B284` points to a Delphi published method table at `0x0047B84E` (`VMT-0x40`). The table begins with a 16-bit count of 17, followed by records containing entry size, code address, and shortstring method name. The first entry is `IdHTTPServerCommandGet` at `0x0047BF30`, proving the HTTP request handler's class/method identity. Other recovered entries include `FormCreate`, `Terminate`, `Log`, `ShowMainForm`, `HideMainForm`, and `FormClose`. The VMT inspector now decodes the full table for the next pass.

### Complete TMainForm published methods

The method table contains 17 published methods, including the HTTP request handler (`IdHTTPServerCommandGet` at `0x0047BF30`) and HTTP exception handler (`IdHTTPServerException` at `0x0047CA44`), plus `FormCreate`, `FormClose`, `Terminate`, `LoadQuickConfig`, `Log`, and UI/timer handlers. The next analysis pass traces the startup, shutdown, and HTTP exception methods to recover server initialization and failure behavior.

## Runtime BPL method object lifecycle (confirmed callsites)

The `ParseMethod` body provides the complete dynamic dispatch lifecycle:

1. `GetClass` via thunk `0x00402354` at `0x00470E07` resolves the Delphi class named by the XML `class` attribute (after the parser's `T` prefix handling).
2. `TObject.ClassName` via thunk `0x004010B8` at `0x00470E5D` checks whether the resolved class name equals `TUpgradeEmwat` (`0x00471128`); the result is stored in `TMethodInfo+0x04`.
3. `TObject.Create` via thunk `0x004010D8` at `0x00470EDC` constructs the actual BPL method object.
4. The service attaches the `TMethodInfo` pointer at instance offset `+0x04` and calls the object's VMT slot `+0x0C` at `0x00470EF6`.
5. `TObject.Free` via thunk `0x004010E8` at `0x00470F42` releases the method object after invocation.

This object lifecycle is distinct from the parser metadata object's own constructor/destructor (`ClassCreate` at `0x00471220`; `ClassDestroy` at `0x0047127F`). The distinction is important for the Linux dispatcher: the XML class name selects a registered method class; a per-call method object receives the parsed method-info payload, executes through its virtual dispatch slot, and is then released.

### Exact Delphi class-name construction and Invoke wrapper bridge

The `T` prefix is now confirmed at instruction level, not merely inferred from the nearby literal. In `ParseMethod`, the XML `class` value is combined with the constant `T` at `0x004710E0` by helper `0x00401310`; that thunk resolves to `rtl230.bpl!System.@UStrCat3`. The resulting `T` + class string is passed to `GetClass` through thunk `0x00402354` at `0x00470E07`.

The BPL side resolves the service's virtual call precisely:

- Service instruction `0x00470EF6` invokes `[instance.VMT+0x0C]`.
- For `TEmwatMethod`, the `+0x0C` VMT entry is `0x0046C9E0`, the public/exported `Invoke` wrapper. Preserve the TD32 naming mismatch: TD32 calls `0x0046C9E0` `Finalization` and labels the inner routine `0x0046C82C` as `TEmwatMethod.Invoke`.
- The wrapper at `0x0046C9E0` calls the 433-byte shared dictionary/XML helper at `0x0046C82C`, then invokes `[instance.VMT+0x10]` at `0x0046CA88`.
- For `TEditWordDocument`, VMT `0x005ED764` has `+0x10 = 0x005EE82C`; this concrete `PerformMethod` reads `wordConfig`, `wordBody`, `letterImages`, and `signData`, then calls `TWordViwer.LoadDocument` (`0x004B7724`).

This closes the class-name construction and service→BPL→concrete `PerformMethod` edge. It does not close all document-field semantics or end-to-end Almas integration.


## Parallel route and CORS-header trace (2026-11-24)

A bounded disassembly of the service's `CommandGet` response path and its string references confirms that the handler writes these literal response headers:

- `Access-Control-Allow-Origin:*`
- `Access-Control-Allow-Headers:*`
- `Access-Control-Allow-Method:*`

The last header is singular (`Allow-Method`), unlike the standard plural `Access-Control-Allow-Methods`. The wildcard origin/header values are static evidence of a permissive CORS response; the inspected range does not establish whether a separate Origin, token, or session check exists elsewhere in the request path.

The embedded bridge still posts to the loopback service and returns `responseText` to the original `postMessage` source/origin. That response routing is not equivalent to server-side authorization. The Linux replacement should use an explicit origin allowlist and request authentication rather than copying wildcard CORS behavior by default.

The same route trace confirms that the service loads `EmwatMethods.bpl` and logs package-load success/failure around the dispatch path. XML parsing separately resolves the `method`, `class`, `param`, and `name` vocabulary; exact method schemas and all error responses remain open.


## Agent/Service lifecycle import-callsite audit — current extracted build (2026-11-24)

The original executables were re-extracted from the repository's `EMWAT_Extracted.zip` and hashed before tracing:

- `EmwatService.exe`: SHA-256 `9b07e270fa216095fe6648694a4896f6f8a190e69002c6742dc894c11a002659`, PE32, ImageBase `0x00400000`, entry point `0x00481C30`.
- `EmwatAgent.exe`: SHA-256 `4553c4c65a5697b5e8121ac70e894a1b98a3def470a7165d931f078d258e4157`, PE32, ImageBase `0x00400000`.

For the current Service build, a byte-level x86 CALL-thunk scan (rather than linear disassembly across Delphi RTTI/data) resolves 31 callsites for the selected lifecycle APIs:

| API | Callsite count | Addresses / notes |
|---|---:|---|
| `CreateMutexW` | 1 | `0x00401D1A` |
| `FindWindowW` | 2 | `0x00468154`, `0x00468273` |
| `GetWindowTextW` | 1 | `0x00468170` |
| `RegisterWindowMessageW` | 1 | `0x0047CE21` |
| `PostMessageW` | 1 | `0x0047DFD6` |
| `TerminateProcess` | 2 | `0x0047D85D`, `0x0047DFF5` |
| `ShellExecuteW` | 1 | `0x00468263` |
| `GetTempPathW` | 2 | `0x00442AEF`, `0x00467E85` |
| `CreateFileW` | 1 | `0x0041A3CC` |

This is concrete evidence of mutex-based single-instance/coordinator behavior and Win32 window-message communication between processes, plus explicit process termination paths. The actual mutex name, registered-message string, target window identity and termination conditions still need to be traced.

The current extracted Service build has no imports for `OpenSCManagerW`, `OpenServiceW`, `StartServiceW`, `CreateServiceW`, or WTS session notification APIs in the inspected import table. Therefore the filename `EmwatService.exe` must not be treated as proof that this particular binary is a Windows SCM service; the observed coordination is currently better described as a user-mode process with window/mutex IPC. A separate installer/service wrapper or another version could still exist.


## 2026-11-24 — confirmed local heartbeat endpoint

The Agent/Service crosswalk now resolves the exact health-check request and response:

- The request handler checks the query-parameter key `heartbeat` (string VA `0x0047C9F0`).
- When present, it assigns the exact text `TickTack` (VA `0x0047CA30`) to `TIdHTTPResponseInfo.ContentText` at response-object offset `+0xBC`.
- It then calls the Indy response writer at `0x004610FC`.
- The startup error string explicitly reports that port `1984` must be free if binding fails.

The matching Agent binary issues an HTTP `GET` to `http://127.0.0.1:1984/?heartbeat` and compares the returned body with `TickTack`. This closes the previously open string-to-callsite gap.

**Native requirement:** implement `GET /?heartbeat` on loopback port `1984` with response body exactly `TickTack`. Do not route this request through document processing or return JSON. Keep health checking independent from the document API.
