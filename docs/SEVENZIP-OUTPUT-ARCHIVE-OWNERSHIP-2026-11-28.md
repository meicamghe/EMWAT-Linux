# SevenZip output archive ownership and callback contract — 2026-11-28

## Evidence

- Workflow: `EMWAT parallel contract closure v2`
- Run: `46118303840`
- Artifact: `15252965648`
- Relevant module: `EmwatUtils` / TD32 symbols for `T7zOutArchive` and `T7zPlugin`

## 1. Plugin owns an output-archive object

`T7zPlugin.Create` at `0x00452C10` has a direct call at `0x00452C25` to `T7zOutArchive.CryptoGetTextPassword2` at `0x004543C4`.

The call uses Delphi constructor-style register setup:

- `EAX` receives the class VMT pointer at `0x004529E8`.
- `DL=1` is the constructor-call flag.
- `ECX=0x00452C54` carries the constructor argument.
- The returned object pointer is stored in the `T7zPlugin` instance at offset `+0x44`.
- The plugin then passes that object through its own interface dispatch at slot `+0x30`.

The target method initializes an object, obtains an interface object from global `0x0062FBB8`, stores it at object offset `+0x2C`, and clears callback/context fields `+0x30` and `+0x34`. Despite the TD32 symbol name `CryptoGetTextPassword2`, this callsite is part of output-archive object initialization; it is not evidence that a password string is supplied at this point.

## 2. Output callback slots

- `T7zOutArchive.SetPropertie` (`0x00454800`) stores a callback pointer at `+0x30` and a context pointer at `+0x34`.
- `T7zOutArchive.SetOperationResult` (`0x004547B0`) checks `+0x30`; when the callback and operation-result object are non-null, it calls the stored callback with the stored context and the result data.
- This establishes a callback/context handoff and later invocation. The semantic identity of the callback, context object, and result fields is still unresolved.
- `T7zOutArchive.SetPassword` (`0x004547DC`) is a nine-byte stub that returns zero. No output password-setting logic is implemented in that method body.

## 3. Separate reset helper

`euResetMemory` at `0x00456F00` is not the same object as the `T7zOutArchive` callback object:

- It selects one of two global object records depending on a Boolean argument.
- It creates/obtains a helper object through `0x00452BBC`.
- It calls that object's VMT slots `+0x44`, `+0x0C`, and `+0x3C` with separate arguments.
- Its direct callers are `Applicationactivities.Finalization` (`0x00503779`) and `TfrmShowAutoSaveFiles.Delete` (`0x005EB938`).

No direct print/TIFF caller was found for `euResetMemory`; do not treat it as the final print archive writer without further evidence.

## 4. What remains unknown

1. What global interface/factory `0x0062FBB8` represents and what its lifetime is.
2. Who supplies the `SetPropertie` callback/context, and what the callback does.
3. Whether output archives are encrypted. `SetPassword` is a stub, and the current evidence does not establish an alternate password path.
4. Whether `T7zOutArchive.SetCompleted` or progress callbacks participate in the final TIFF hand-off.
5. Exact output archive entry names, destination path, and error/cleanup behavior.

No password, encryption, or archive format policy should be hard-coded from the current evidence.
