# EMWAT service request lifecycle — static trace checkpoint

Date: 2026-11-16
Binary evidence: `EmwatService.exe`, extracted analysis artifact `14208144442`
Scope: service-side request dispatch only. This note does not claim runtime behavior beyond the separately recorded local HTTP observations.

## Main handler control flow

The bounded disassembly at `0x0047BF30` shows the following sequence:

1. The handler establishes a local timeout/deadline value using helper `0x00401040`, adds `0x186A0`, and stores the result in a local variable. The exact unit and helper semantics are not established here.
2. It calls helper `0x0047D2C8` with a string at `0x0047C37C` and the local value. This appears to be a diagnostic/logging path; exact message text should be decoded from the binary before assigning meaning.
3. It obtains an interface-like object from a field at `self + 0xD4`, calls its first virtual slot, then calls another slot at offset `+0x0C`. The exact interface type is unresolved.
4. It initializes request-local state and calls `0x0047E0EC` at `0x0047C08D`, passing the request context and an output pointer.
5. If `0x0047E0EC` returns false, the handler takes the error/logging branch at `0x0047C096–0x0047C0BA`.
6. If it returns true, the handler calls `0x00470D00` at `0x0047C0C5`, the previously identified XML `ParseMethod` wrapper.
7. The handler then enters its cleanup/finalization path and calls `0x0047E2D4` at `0x0047C0E0`.

## Route helper `0x0047E0EC`

The helper:
- reads an object pointer from `self + 0x428`;
- calls the first virtual method on that object;
- stores the result into the caller-provided output location;
- checks whether the output is zero;
- returns a Boolean result in a local byte.

The helper therefore mediates a virtual/interface-based precondition or route selection before XML parsing. The exact meaning of the `+0x428` field and the virtual method is unknown. Do not label it as authentication, authorization, endpoint selection, or request validation until its class/interface is identified.

## Finalizer helper `0x0047E2D4`

The helper checks the value supplied through its second argument. If nonzero, it calls logging/error helper `0x0047D2C8`, invokes helper `0x0040217C` on the value, logs another message, and clears the caller's value. This resembles guarded cleanup of a pending exception/error object, but the precise exception type and ownership contract are not yet established.

## Relationship to the known XML parser

The handler's successful route branch reaches `0x00470D00`, consistent with the separately established parser envelope:
- root `emwat` with `version`;
- child `method`;
- method `class`;
- child `param` with `name`.

The parser helper `0x0046A7A4` adds a three-value record to the collection. The expanded trace through `0x0046A620` and `0x0046A570` resolves the record layout for each `param`:
- slot 0: hash computed from the parameter name;
- slot 1: the `param name` attribute;
- slot 2: the parameter element's text content.

The caller at `0x00470B38` extracts the `name` attribute and parser text separately, computes the name hash, probes the collection, then passes the hash/name/value triple to the append helper. The append helper stores the three values at a 12-byte stride and invokes the collection's virtual methods at offsets `+0x08` and `+0x0C` with the name and value.

The parser object identity is now directly proven. `ParseMethod` constructs `TMethodInfo` (VMT `0x0047097C`, instance size `0x10`) through constructor `0x00471214`. That constructor loads the dictionary class reference at `0x004699E4` (the class-reference slot for VMT `0x00469A3C`) and calls `0x0046AA70` to create `TDictionary<System.AnsiString,System.AnsiString>` (typeinfo `0x0046A054`), storing the dictionary pointer at `TMethodInfo + 0x08`. The XML parser receives that exact `+0x08` pointer and populates it through the hash/probe/entry helpers. This is the same key/value type accepted by BPL `TEmwatMethod.Invoke`; the remaining open item is the exact indirect cross-module dispatch call, not dictionary identity.

## What this trace does not establish

- Exact HTTP verb/path/header contract.
- Meaning of the `self + 0x428` virtual object.
- Meaning and units of the local timeout/deadline.
- Full parser-to-BPL dynamic dispatch.
- Exact success/error response XML.
- Whether the finalizer is handling Delphi exceptions, task state, or another error object.

## Next targets

1. Resolve the class/VMT for the object at `self + 0x428` and its first virtual method.
2. Trace `0x00470D00` and its worker through the three-value parser record into method-class construction.
3. Decode the string constants used by the handler and finalizer.
4. Correlate the service finalizer with the BPL long-lived Word wait and actual HTTP response writer.


## New binary-backed parser trace — 2026-11-16

The archive-driven CI run extracted `EmwatService.exe` (679,936 bytes) and produced artifact `emwat-service-dispatch-crosswalk` (run `43882629052`, artifact `14232189125`). The service job completed successfully after optional TD32 metadata probes were made non-fatal.

New static observations from the artifact:

### XML parser worker: `0x00470B38`

- Creates/initializes a parser-related object through global factory and helper calls.
- Repeatedly queries parser state and branches on token-kind bytes at object offset `+0x40`.
- One branch handles token kind `5`, obtains a value from an object at offset `+0x54` using helper `0x004670A8`, then assigns the result into the caller's structure.
- Another branch handles token kind `8`, obtains a value through the same object region, and calls `0x0046ADBC` with the parser context and two string-like arguments.
- This confirms a token-driven parser loop and two distinct token handling paths. The numeric token meanings and the exact strings are not yet established.

### Token-record append helper: `0x0046A7A4`

The helper computes `index * 3`, then writes into a table at 12-byte record intervals:
- first 32-bit slot receives the incoming `EDX` value;
- second slot is assigned from stack argument `[EBP+0x0C]` via helper `0x00401220`;
- third slot is assigned from stack argument `[EBP+0x08]` via the same helper;
- the collection count at `[EBX+8]` is incremented.

This establishes the physical three-slot record layout. The semantic names/types of the three values remain unresolved; do not label them as name/value/type until corroborated by token constants or runtime fixtures.

### Parser record caller: `0x0046ADBC`

The caller grows/obtains a record index, retrieves parser state, and passes the index plus two string-like arguments to `0x0046A7A4`. This links the token parser worker to the three-slot collection append operation.

### Handler and route helper

The fresh `0x0047BF30` trace confirms:
- the handler calls `0x0047E0EC` at `0x0047C08D`;
- a false return follows a separate error/logging path;
- a true return calls XML parser wrapper `0x00470D00` at `0x0047C0C5`;
- the handler then reaches finalizer helper `0x0047E2D4`.

The route helper `0x0047E0EC` reads an object pointer from `self+0x428` and invokes its first virtual slot. Its identity and semantic role are still unknown.

### CI correction

The first archive-backed service run failed only after writing the six requested address traces: optional class/VMT/interface metadata probes returned non-zero because the service PE did not expose the expected TD32 signature. Commit `ce79705a41d97baf90a8b19219a1eb606fe02290` makes those optional probes non-fatal. The follow-up service job in run `43882629052` completed successfully and uploaded the artifact above.


## Important correction — 0x0047E0EC is a BPL package loader gate, not a generic route validator

The extended archive-backed trace decoded the constants used by `0x0047E0EC`. It passes the literal package name `EmwatMethods.bpl` to helper `0x00401308`, then tests the result of helper `0x00402174`. Its two branches log:
- `Unable to load "EmwatMethods.bpl".`
- `"EmwatMethods.bpl" loaded.`

The routine returns a Boolean to its caller. Therefore the earlier neutral label “route helper” was misleading: the strongest supported interpretation is that this is a package-load/check gate for `EmwatMethods.bpl`, not endpoint selection or authentication.

The MainForm handler's call at `0x0047C08D` is now understood as:
1. prepare/check that the `EmwatMethods.bpl` package is loaded;
2. if the check fails, take the error/logging branch;
3. if it succeeds, call the XML parser at `0x00470D00`.

The same string decode found:
- `invoke` at `0x0047C360`, passed to a request-object virtual method in the handler;
- `Emwat method called from ` at `0x0047C37C`;
- response-header-like literals `Access-Control-Allow-Origin:*`, `Access-Control-Allow-Headers:*`, and the exact singular spelling `Access-Control-Allow-Method:*`.

This is strong evidence for an `invoke` command/route token and CORS-related response headers. The precise HTTP verb, full URL path, header-setting API, and status/body contract remain unresolved. Do not normalize the singular `Allow-Method` literal to the standards spelling in compatibility code unless runtime capture proves the original behavior is different.

The updated parser/loader artifact is `emwat-service-parser-followup`, run `43882768547`, artifact `14233102935`. Its bounded traces also confirm the XML parser compares the literal child names `method`, `class`, `param`, and `name`.


## Cross-reference to the already recovered end-to-end invoke contract

The parser/package-loader findings above are not the whole protocol. Existing request-capture and BPL crosswalk documents provide the next stages:

- The browser bridge issues `POST /?invoke=<random>`; its embedded JavaScript computes `Math.floor(Math.random() * 99999)`. The query value is therefore a per-message request nonce, not the operation identifier. The method identity is carried in the XML `method class` attribute.
- The captured outer envelope uses `<emwat version="1.0">`, one `method` element, its `class` attribute, and `param name` children.
- A captured `EditWordDocument` call carries `wordConfig` and `wordBody` as Base64 text, plus `signData`; the concrete BPL method also retrieves `letterImages`. The inner `wordConfig` is a second XML document, while `wordBody` is opaque legacy DOC/CFB data in the captured sample.
- Service dispatch resolves `T` + the parsed class name through Delphi `GetClass`, constructs the class instance, and invokes the inherited `Invoke` virtual slot. The BPL `TEmwatMethod.Invoke` wrapper then dispatches the concrete subclass's `PerformMethod`.
- The successful `EditWordDocument` response is `response-word status="success"`, with a `return-types/type` node whose `mimetype` is `application/msword` and `encryption` is `base64`. The successful response writer is reached after the close-driven document path.
- The service contains exact CORS-like literals `Access-Control-Allow-Origin:*`, `Access-Control-Allow-Headers:*`, and `Access-Control-Allow-Method:*` (singular `Method` spelling).

For full evidence and request/response capture context, see:
- `docs/HTTP-LOCAL-API-ANALYSIS.md`
- `docs/EDITWORD-REQUEST-SCHEMA.md`
- `docs/EMWAT-SERVICE-EXECUTABLE-ANALYSIS.md`
- `docs/WORD-DOCUMENT-PROTOCOL-ANALYSIS.md`

The Linux bridge retains an allowlisted Origin policy as a security hardening choice; it does not blindly reproduce the Windows wildcard origin. It now emits the recovered `Access-Control-Allow-Headers` and singular `Access-Control-Allow-Method` literals on POST responses. The random invoke query remains opaque at the transport layer rather than being treated as a method name.


## Parser collection record layout — follow-up artifact 14233736412

The expanded parser-token trace resolves the prior three-slot ambiguity. In `0x00470B38`, the parser reads the `param` element's `name` attribute into one string and the element text into a second string. `0x0046A620` computes a hash from the name; `0x0046A570` probes the collection for the key/insertion slot. The caller then invokes `0x0046A7A4`, which writes the hash, name, and value into three consecutive 32-bit slots at a 12-byte stride.

The collection append helper also calls its virtual methods at `+0x08` and `+0x0C` with the key and value strings. This is strong evidence that the three-slot structure is a hash-table entry representation, not an arbitrary XML token tuple.

The expanded VMT/constructor trace now proves the exact link: `TMethodInfo` (`0x0047097C`) constructs `TDictionary<System.AnsiString,System.AnsiString>` using class reference `0x004699E4` → VMT `0x00469A3C`, stores it at `TMethodInfo + 0x08`, and `ParseMethod` passes that dictionary to the XML parser. The BPL `TEmwatMethod.Invoke` signature accepts the same string-to-string dictionary type. Only the final indirect cross-module dispatch edge remains unresolved.

Artifact: `emwat-service-dispatch-crosswalk`, run `43883105610`, artifact `14233736412`.

### Duplicate parameter behavior

The parser's dictionary insertion helper `0x0046ADBC` probes the hash table before appending. If the key already exists (`0x0046A570` returns a non-negative bucket index), it enters the duplicate-key exception path (`0x00402 11C` / `0x00401198`) instead of treating the second value as an overwrite. The Python envelope parser's `duplicate_parameter` rejection therefore matches the native Add semantics; it must not be changed to last-value-wins behavior.
