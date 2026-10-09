# Evidence log

Observed with disposable Miro boards and invented content, in Chrome on macOS, September 2026. This log separates what a Miro paste confirmed from what was only checked by decoding files locally. Use it to know how much to trust a field before relying on it.

## Confirmed by a Miro paste

1. Replaying a complete copied trio (outlined rectangle, sticky, orange pen stroke) recreated three editable objects in the same relative layout.
2. Replaying **only** `public.html` recreated the trio. Removing Miro's `data-meta` attribute stopped native paste; the stripped HTML still pasted as text elsewhere, so the fallback exists.
3. Changing only the visible HTML from `Hello` to `Bonjour` left the native sticky at `Hello world`. Native text comes from the encoded data.
4. Two copies of an unchanged sticky were byte-identical. A text edit in Miro changed one decoded byte. Changing that byte again through the tools produced an editable sticky with the new text.
5. Re-encoding full JSON with a longer text (`Een riskante aanname`) produced an editable sticky.
6. Cloning one sticky into three produced three editable, separately positioned notes.
7. A mixed generated selection pasted as two labelled shapes, two stickies and the copied pen stroke.
8. A generated connector linked two generated shapes. When one shape moved, Miro kept the connector attached and rerouted it. A generated free arrow stayed where it was.
9. An 18-object diagram (nine shapes, six connected arrows, three text boxes) pasted in the intended three-row layout.
10. Generated test cases pasted visibly: Unicode and emoji text, a pale-green sticky, six shape variants, a pale-blue shape with a thick red rounded border, a rotated shape, a two-paragraph text box, three line styles and an edited caption, a connector with a bend point, a calculated wave and zigzag, a resized and renamed frame, a 2 x 2 grid, a data-table view, a dummy image, a group of shapes with a connector, and 25 numbered stickies.
11. Follow-up checks: the generated group moves together, the grid shows its content but renders small, the connector bend stays correct after moving a shape, and the data table pasted empty because the source table was empty too.

12. **9 October 2026**, after the composer was extended:
    - a flowchart built from a three-week-old capture (pasted on the same board): a diamond made with the new `shape` field, connectors labelled "yes" and "no", one connector with **no** label although its template had one, and a branch from the bottom of the diamond to the top of a box;
    - sixteen stickies in every colour of Miro's picker, each with its number; Miro showed white text on the black one;
    - a sticky with two lines;
    - a sticky made twice as big with `scale` (worked) and one with doubled `size` (became wide and rectangular instead);
    - two stickies at the same `y` but different sizes had level centres, so `x, y` is the centre;
    - three pink stickies joined by connectors, using a connector merged in from the three-week-old capture; the connectors stayed attached and curved along when the middle sticky was moved.

13. **9 October 2026, stress test.** An agent with only the skill as documentation turned a messy 24-note workshop wall into a 64-object synthesis: recoloured notes, merged duplicates, a parked area, an extended legend as a group, an assumption-to-test map with two decision diamonds and four labelled connectors, and a corrected process flow, all in a frame. It pasted cleanly. The objects did not move with the frame until `_parent` links were added; with them, all 63 moved with the frame. The legend group (five stickies and a text box) moved as one piece. A follow-up showed that `fs` with `fsa: 0` gives stickies one fixed text size.

A visual pass means the objects appeared. Behaviour (editing, moving, persistence after reload) is confirmed only where stated.

## Confirmed by local checks only

- The inner Base64 becomes valid UTF-8 JSON after subtracting 59 from each byte modulo 256; adding 59 reverses it.
- A 34-object selection containing shapes, lines, a text box, a pen stroke, a frame, a data table, a grid with four cells, an image and a group decoded, re-encoded and decoded again without any change.
- Changing one shape's text in that selection left every other decoded field equal.
- Attached line endpoints reference array indexes; free endpoints use `-1`. Group records list member indexes. Grid cells point to their grid with `_parent.index`.

## Still open

- Connectors attached to text boxes, frames or groups.
- The meaning of individual line style values (`ls`, `lt`) and of several shape and sticky style keys; each was changed only together with others, or not at all.
- Rich text (bold, lists, links) inside stickies.
- Pasting on another board or in another organisation. Reuse three weeks later on the same board worked for stickies, shapes and connectors; resource-based objects (images, data tables) are the most likely to fail elsewhere.
- Child edits and ungrouping for generated groups; frames nested in frames.
- Behaviour in browsers other than Chrome, and in future Miro versions.
