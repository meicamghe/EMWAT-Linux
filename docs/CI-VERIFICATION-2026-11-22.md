# CI verification — 2026-11-22

## Scope

This record captures the latest workflow results queried for PR #2 head
`46da05740fe6e93ee78419b982abd6d7ea1f5504` in
`meicamghe/EMWAT-Linux`.

PR #2 remains open, Draft, and unmerged. No merge was performed.

## Latest workflow results

| Workflow | Run | Result | Verified jobs |
|---|---:|---|---|
| Python bridge transport | [44799228821](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44799228821) | Success | test |
| LibreOffice UNO integration | [44799228605](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44799228605) | Success | uno-roundtrip; adapter unit and real UNO roundtrip step |
| Native image core | [44799228619](https://github.com/meicamghe/EMWAT-Linux/actions/runs/44799228619) | Success | build-test; sanitizer-test; deb-package-lifecycle |

The Native workflow's successful steps include CMake configure/build/test,
staged installation, AddressSanitizer/UndefinedBehaviorSanitizer tests, and
DEB install → upgrade → remove lifecycle.

The previous UNO run `44798818677` was cancelled during its test step. It is
superseded for this checkpoint by the later successful UNO run
`44799228605`; the cancelled run is not counted as a pass.

## What this establishes

- Python bridge test workflow completed successfully for the queried PR head.
- LibreOffice Writer/UNO runtime verification and the real UNO roundtrip test
  step completed successfully.
- Native build/test and sanitizer jobs completed successfully.
- The native development package lifecycle completed successfully.

## What this does not establish

These CI workflows do not establish a complete end-user EMWAT Linux
application or live compatibility with Almas Gam. Remaining acceptance gates:

1. **WordConfig semantic mapping:** the current request path parses
   `wordConfig`, but `LibreOfficeAdapter.open_document()` does not apply it.
   Exact field/twin/image/signature mapping requires a sanitized matching
   Word + WordConfig fixture and expected output. No positional or guessed
   mapping is permitted.
2. **Visible Writer close behavior:** Save, Don't Save, Cancel, and retry must
   be verified through the visible Writer window. A snapshot taken during
   `queryClosing` is not proof of the user's final choice.
3. **Almas end-to-end:** the actual Almas request/response interaction and
   Cancel/Discard response contract remain unverified.
4. **Runnable desktop application:** the existing DEB is a native-core
   development package, not the complete bridge + GTK application installer.
   The GTK Recovery picker still needs a real Ubuntu desktop runtime test and
   application entrypoint/supervision integration.
5. **Scanner hardware:** physical scanner, ADF, duplex, and multi-frame
   acceptance remain unverified.
6. **EASZ:** Linux interoperability remains gated on a real sample and its
   required password/contract evidence.

## Release rule

Do not mark the product release-ready solely from CI. Keep PR #2 Draft and
unmerged until the semantic mapping, visible close matrix, Almas E2E, and
installable Linux application acceptance gates are satisfied.
