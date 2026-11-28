# Reverse-engineering parallel follow-up — 2026-11-28 Run 33

## GDI+ interface table base candidates

The existing class metadata and interface RTTI artifact provides candidate addresses for a direct raw table dump:

- TGPImage class slot 0x00484728 + 0x28 points to interface-table metadata at 0x0047DD2C.
- The associated interface RTTI candidate starts at 0x0047DD84. Its +0x58 DWORD contains 0x0062EEA0, a candidate base pointer for the TGPImage interface method table.
- TGPEncoderParameters class slot 0x00483F4C + 0x28 contains 0x0062EE88, a separate interface-table candidate. The two candidate bases differ by 0x18 bytes, consistent with nearby interface tables but not proof of the exact layout.

If 0x0062EEA0 is the TGPImage interface VTable base, the call slots map to candidate DWORD addresses:
- +0x48 -> 0x0062EEE8
- +0x58 -> 0x0062EEF8
- +0x5C -> 0x0062EEFC
- +0x70 -> 0x0062EF10
- +0x74 -> 0x0062EF14

These are address calculations only. The actual DWORD pointer values at those addresses are absent from the downloaded artifact and must not be inferred. A raw dump of 0x0062EE88 through 0x0062EF18 from the original PE will confirm or reject the candidate and provide the actual method pointers.

The operation-level Save/SaveAdd map remains independently supported:
- +0x48: initial SaveImageToFile
- +0x5C: SaveAddImage for subsequent pages
- +0x58: final SaveAdd with EncoderValueFlush=20

No tests, CI, or package build were run.
