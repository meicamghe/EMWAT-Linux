# Simple image editor crop interaction — recovered coordinate contract

Date: 2026-11-25
Input: TD32 procedure/caller artifacts from parallel reverse-engineering workflow run 45560465682.
Scope: static disassembly of the exact EmwatMethods.bpl1 snapshot. No runtime GUI interaction was performed.

## Preview-to-source coordinate conversion

The crop editor does not pass its displayed mouse rectangle directly to the image processor. TfrmSimpleImageEditor.pbImgViewerMouseDown (0x004F1274) reads source-image dimensions from the image object at form offset +0x408:
- source width: image object +0x40
- source height: image object +0x3c

It reads displayed viewer dimensions from the control at form offset +0x3c4:
- viewer width: control +0x58
- viewer height: control +0x5c

The handler computes independent horizontal and vertical scale ratios: scale_x = source_width / viewer_width; scale_y = source_height / viewer_height. It multiplies the four rectangle coordinates stored on the form by the matching ratio and converts each result to an integer through helper 0x00401058. The coordinate fields are used as two X bounds (form +0x40c, form +0x414) and two Y bounds (form +0x410, form +0x418). The resulting four-value record is passed to helper 0x004EEE24 with the image object.

This proves that the crop path accounts for displayed-image scale and keeps X/Y scaling independent. The exact rounding rule implemented by 0x00401058, any preview letterbox offset adjustment, and the semantic order of the four values at the final helper boundary still require confirmation.

## Selection and drag behavior

pbImgViewerMouseMove (0x004F1308) tests the pointer against the four rectangle edges and the rectangle interior. It stores a selection/handle code in form byte +0x41c and anchor coordinates in +0x420 / +0x424. The edge hit regions use asymmetric pixel tolerances (approximately -2/+5 on one side and -5/+2 on the other); the interior receives a separate code.

pbImgViewerMouseUp (0x004F1404) uses that code to update one edge or translate the rectangle using the difference between the release coordinate and stored anchor. It then notifies the viewer/control through an indirect call at slot +0xa8. The exact symbolic meaning of each handle code is not assigned here because the compiler-emitted jump-table target order should be cross-checked against the form resource/runtime state before naming individual edges.

## Applying crop

TfrmSimpleImageEditor.CropImage (0x004F11E8) dispatches through the image object's interface slot +0x88, passing a byte-valued option from image object +0x57. It then checks image-object flags at +0x58 and +0x57, conditionally queries image BPP through TGearImgProc.GetImageBPP (0x004EF0C4), updates two related controls through helper 0x0040487C and an indirect slot +0x88, and calls 0x004F17B4 for the subsequent editor state transition.

The callsite scan found CropImage called from Initial (0x004F11BD) and the editor's btnRegisterClick (0x004F1837). This establishes that the register action can invoke the crop path, but it does not prove the complete accept/cancel transaction semantics.

## Linux implementation implications

1. Keep crop selection coordinates in preview space while the user drags; convert once to source pixels using independent X/Y scale ratios.
2. Model preview origin/letterboxing explicitly if the UI can display an image with margins; the current trace proves scaling but does not prove whether offsets are zero or stored elsewhere.
3. Preserve integer conversion behavior only after helper 0x00401058 is identified.
4. Keep editor commit/cancel separate from pixel crop execution. The btnRegisterClick callsite proves a crop invocation, not a complete rollback/commit contract.
5. Add tests for nonuniform X/Y scale, preview margins, edge clamping, and integer rounding once those exact details are recovered.

## Evidence limits

- Procedure traces: 0x004F1274, 0x004F1308, 0x004F1404, 0x004F11E8, 0x004F1660.
- Direct callers: 0x004F11E8.
- Static-only. No physical scanner, actual GUI, or Windows runtime crop comparison was performed.
