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

The parser helper `0x0046A7A4` adds a three-value record to an internal collection. The record schema and subsequent conversion to the BPL `TDictionary<AnsiString,AnsiString>` are still unresolved.

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
