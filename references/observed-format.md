# Miro clipboard: observed format and object guide

This guide records experiments on macOS with Miro in Chrome, September 2026, on disposable boards with invented content. It describes the copied selection format as observed. It is not a public Miro contract, and Miro may change it without notice. Every claim says whether a Miro paste confirmed it or whether it comes from local decoding only. The paste observations are listed in [evidence.md](evidence.md); open questions and test cases are in [test-plan.md](test-plan.md).

## What the experiments prove

- `public.html` alone recreates editable Miro objects. The Chromium source token, source URL and plain-text representation were not needed.
- Removing Miro's `data-meta` attribute stops native paste. Changing only the visible HTML fallback does not change a native sticky's text.
- Rewriting the decoded JSON produced stickies with new and longer text, three and twenty-five generated stickies, mixed shapes and stickies, recoloured stickies and shapes, connected and free lines, frames, grids, groups and an 18-object diagram.
- A generated connector stayed attached and rerouted when a connected shape was moved.
- Pasting always creates new objects. Nothing here edits existing board objects in place.

The experiments do **not** prove that every property below is writable. Each section states its status.

## The clipboard envelope

`scripts/miro-clipboard-lab.swift capture` writes every macOS pasteboard representation into a local JSON file. Each representation's `data` is Base64 of its raw bytes. This outer Base64 belongs to the capture file, not to Miro.

A Miro copy in Chrome produced one pasteboard item with:

```text
public.html
public.utf8-plain-text
org.chromium.internal.source-rfh-token
org.chromium.source-url
```

`public.html` holds an empty `span` with a `data-meta` attribute. Its value contains `(miro-data-v1)` and `(/miro-data-v1)` around another Base64 string. The HTML after `</span>` is a visible fallback for other apps. Miro reads the encoded data for native paste.

Decoding and encoding:

```python
payload = base64.b64decode(inner_value)
document = json.loads(bytes((byte - 59) % 256 for byte in payload))

json_bytes = json.dumps(document, separators=(",", ":")).encode("utf-8")
inner_value = base64.b64encode(bytes((byte + 59) % 256 for byte in json_bytes))
```

The shift works on UTF-8 **bytes**, not characters. It is an encoding, not encryption. The composer and reader do this for you and write captures with `public.html` only.

The decoded document, identifiers omitted:

```json
{
  "isProtected": false,
  "boardId": "...",
  "data": {"objects": [], "meta": {}},
  "version": 2,
  "host": "miro.com",
  "asPortalAmount": 0,
  "copierType": "COPY"
}
```

Keep top-level fields as copied. Which ones Miro requires has not been established.

## Privacy

A capture contains the full text of what was copied, plus identifiers: the top-level `boardId`, and per object a `meta` block with `boardId`, `orgId` (the Miro organisation) and `widgetToken`. Stickies also carry `ns:author` with an author ID. Images carry resource IDs. Keep captures and decoded JSON local, outside Git, and never share a capture of a real or confidential board. Share summaries only when the text itself may be shared.

## Common object rules

Most objects in `data.objects` have `type: 14`, a zero-based `id`, a numeric-string `initialId`, `meta` and `widgetData`. `widgetData.type` names the kind; `widgetData.json` holds its properties. A group record is different: `type: 10` with an `items` array of member indexes and no `widgetData`.

- **IDs.** `id` must equal the object's index in the array. Generated objects pasted when they had consecutive `id` values and distinct `initialId` strings derived from the template's `initialId` (template plus 1, 2, 3...). Do not invent arbitrary `initialId` values.
- **Position.** Positioned objects have `_position.offsetPx` with `x` and `y` and `schema: "canvasOffsetPx"`. Grid cells use `schema: "gridOffsetPx"` instead. `x, y` is the object's **centre**: two stickies of different sizes at the same `y` pasted with their centres level (paste confirmed for stickies; shape rows aligned the same way).
- **Size and scale.** `size` holds `width` and `height`. Many objects also have `scale.scale` and `relativeScale`. The footprint on the board appears to be size times scale (see stickies). Scale edits have not been tested on their own.
- **Rotation.** `rotation.rotation` and `relativeRotation`, in degrees. Setting both to 25 rotated a shape by about 25 degrees (paste confirmed).
- **Parent.** `_parent` is usually `null`. Grid cells point to their grid with `_parent.index`.
- **Style strings.** Most `style` values are **JSON stored as a string** inside the JSON. Parse it, change only the keys you need, and serialise it back. Replacing the whole style resets every other setting. The composer's `set_style()` does this.
- **Colours.** Colour values are decimal RGB integers: `#FFF79E` is `16775070`. `-1` means none or transparent. Convert with `int("FFF79E", 16)` and back with `"#%06X" % value`.
- **Text.** Text is HTML. Escape user text and wrap each line in `<p>...</p>`. Accents, emoji and `&` pasted correctly. Rich text (bold, lists, links) has not been tested; copy a Miro example first if you need it.
- **Index references.** Line endpoints, group `items` and grid `_parent.index` refer to array positions. When you remove, reorder or extract objects, rebase all of them. `subset()` in the composer and `miro-clipboard-read.py --subset` do this.

## Colours seen so far

| Where | Key | Value | Hex | Status |
|---|---|---|---|---|
| Default yellow sticky | `sbc` | 16775070 | `#FFF79E` | copied |
| Recoloured sticky | `sbc` | 13170629 | `#C8F7C5` (pale green) | paste confirmed |
| Default shape border and text | `brc`, `tc`, `sc` | 1710618 | `#1A1A1A` | copied |
| Recoloured shape fill / border | `bc` / `brc` | 14215423 / 12599360 | `#D8E8FF` / `#C04040` | paste confirmed together |
| Default connector | `lc` | 3355443 | `#333333` | copied |
| Freehand pen | `lc` | 16686925 | `#FE9F4D` (orange) | copied |
| Frame title | `tc` | 6052956 | `#5C5C5C` | copied |
| Frame fill | `bc` | 16777215 | `#FFFFFF` | copied |

## Miro's sticky palette

Captured on 9 October 2026 from one sticky of each colour in Miro's colour picker, in the order they were placed on the test board. All sixteen pasted back with their colour (paste confirmed). The names are plain descriptions, not Miro's own names.

| # | Description | Hex | `sbc` |
|---|---|---|---|
| 1 | light yellow (Miro's default) | `#FFF79E` | 16775070 |
| 2 | yellow | `#FFE86D` | 16771181 |
| 3 | orange | `#FFB575` | 16758133 |
| 4 | red | `#FF9E9E` | 16752286 |
| 5 | light pink | `#FFD2F2` | 16765682 |
| 6 | pink | `#FD9AE7` | 16620263 |
| 7 | light blue | `#B2D0FE` | 11718910 |
| 8 | violet | `#B8ACFB` | 12102907 |
| 9 | cyan | `#9CE6FF` | 10282751 |
| 10 | blue | `#86B4F9` | 8828153 |
| 11 | turquoise | `#81E7DE` | 8513502 |
| 12 | green | `#6AE08D` | 7004301 |
| 13 | light green | `#D1F09F` | 13758623 |
| 14 | lime | `#B3E65F` | 11789919 |
| 15 | white | `#F3F5F7` | 15988215 |
| 16 | black | `#151515` | 1381653 |

On the black sticky Miro showed the text in white by itself; the sticky has no text-colour key. Prefer these values over invented ones. Custom colours also pasted as given (the pale green `#C8F7C5` in the table above), but they will not match the picker.


## Sticky note, `widgetData.type: "sticker"`

Fields: `text`, `size`, `scale`, `relativeScale`, `rotation`, `relativeRotation`, `_position`, `_parent`, `style`, `ns:author`.

The copied stickies had `size` 199 x 228 and `scale` 0.43, so they occupied about 86 x 99 on the canvas. Twenty-five generated stickies spaced 180 apart horizontally and 160 vertically pasted as five readable rows; sixteen spaced 120 by 130 sat close but apart. Always compute the footprint from your own template: `width * scale`, `height * scale`.

- **Bigger or smaller:** change `scale` (and `relativeScale` to the same number). Doubling it gave a sticky twice as big (paste confirmed).
- **Do not use `size` to resize.** Doubling width and height gave a wide, rectangular sticky of the original height (paste confirmed). Use `size` only if you want that rectangular shape.

| Style key | Observed | Meaning | Status |
|---|---|---|---|
| `sbc` | 16775070 | background colour | paste confirmed |
| `fs`, `fsa` | 0, 1 | font size, auto-size on (assumed) | observed only |
| `ffn` | "Noto Sans" | font family | observed only |
| `ta`, `tav` | "c", "m" | horizontal and vertical text alignment | observed only |
| `taw`, `tah` | 0, 0 | unknown | observed only |
| `lh` | 1.36 | line height | observed only |

Keep `ns:author` when cloning. Clones therefore carry the template's author; whether Miro shows that person as the author of the new notes has not been checked. Changing text length, Unicode, emoji and `&` all pasted as editable stickies. Two `<p>` paragraphs showed as two lines (paste confirmed); Miro shrinks the font to fit.

## Shape, `widgetData.type: "shape"`

Fields: `text`, `shape` (a code as a string), `size`, transform fields, `_position`, `style`.

| Shape | `shape` / `st` | Status |
|---|---|---|
| Rectangle, square | `"3"` | paste confirmed |
| Ellipse, circle | `"4"` | paste confirmed |
| Triangle | `"5"` | paste confirmed |
| Rhombus (diamond) | `"8"` | paste confirmed |

Square versus rectangle and circle versus oval come from `size`, not from the code. Other shapes (arrows, stars, callouts, cylinders...) have not been captured. Do not guess their codes; copy one first.

| Style key | Default | Meaning | Status |
|---|---|---|---|
| `bc` | -1 | fill colour (-1 transparent) | paste confirmed with others |
| `bo` | 1 | fill opacity | observed only |
| `brc` | 1710618 | border colour | paste confirmed with others |
| `brw` | 2 | border width | paste confirmed with others |
| `brr` | 0 | corner radius (rectangles only) | paste confirmed with others |
| `bro`, `brs` | 1, 2 | border opacity, border style | observed only |
| `sc` | 1710618 | stroke colour, equal to `brc` in captures | observed only |
| `st` | same as `shape` | shape type | observed only |
| `tc`, `fs`, `ffn` | 1710618, 14, "Noto Sans" | text colour, font size, font | observed only |
| `ta`, `tav` | "c", "m" | text alignment | observed only |
| `b`, `i`, `u`, `s` | 0 | bold, italic, underline, strike | observed only |
| `ss`, `tsc`, `bsc`, `hl`, `VER` | 2, 1, 1, 0, 2.1 | unknown or version | observed only |

The fill, border colour, border width and radius were changed **together** in one paste test (a pale-blue shape with a thick red rounded border). Change one key at a time before treating each mapping as certain.

## Text box, `widgetData.type: "text"`

Fields: `text`, `size`, transform fields, `_position`, `style`. The copied text box had `style.st: 14`, `ta: "l"`, transparent background `bc: -1`, text colour `tc`, font `ffn`, padding `p: 0` and font weight `fw: 0`. A generated two-paragraph box showed both lines and a literal `&` (paste confirmed). Font size control has not been tested.

## Line and connector, `widgetData.type: "line"`

Fields: `primary`, `secondary`, `points` (bend points), `line.captions`, `style`; `_position` is usually `null`.

Each endpoint looks like:

```json
{"point": {"x": 1, "y": 0.5}, "positionType": 0, "widgetIndex": 0}
```

- **Attached.** `widgetIndex` is the index of another object in the same array. `point` is then relative to that object: `x: 1, y: 0.5` is the middle of its right side, `x: 0, y: 0.5` the middle of its left side. The target must come **before** the line in the array. A generated shape-to-shape connector stayed attached and rerouted when a shape moved (paste confirmed).
- **Free.** `widgetIndex: -1` at an end; `point` then holds canvas coordinates. A free arrow did not follow moving shapes (paste confirmed).
- **Bend points.** `points: [{"x": ..., "y": ...}]` gave a visible bend that stayed sensible after moving a shape (paste confirmed).
- **Caption.** `line.captions[0].text` is HTML. Changing it to `Nieuw label` showed in Miro (paste confirmed). Only lines copied with a caption have the caption structure.
- **Sides.** `x: 0.5, y: 1` is the middle of the bottom, `x: 0.5, y: 0` the middle of the top. A connector from the bottom of a diamond to the top of a box pasted as intended (paste confirmed).
- **Connectors between sticky notes** stayed attached and curved along when a note was moved (paste confirmed). Connectors to text boxes or frames have not been verified; the composer warns.
- **No label.** Setting `line.captions` to `[]` on a clone of a labelled line removed the label (paste confirmed).

| Style key | Observed | Meaning | Status |
|---|---|---|---|
| `lc` | 3355443 | line colour | observed only |
| `t` | 2 | thickness (assumed) | observed only |
| `a_start`, `a_end` | 0, 9 | arrowheads; 9 showed an arrow at the end | arrow paste confirmed |
| `ls` | 1 or 2 | unknown (line style or shape) | observed only |
| `lt` | 0, 1 or 2 | unknown (route type) | observed only |
| `jump`, `VER` | 0, 2 | line jumps, version | observed only |

Three copied line styles pasted with visibly different routes or strokes, but the meaning of each `ls` and `lt` value has not been isolated. To get a specific look (elbow, curved, dashed), copy a line with that look and use it as the template.

## Freehand drawing, `widgetData.type: "paint"`

A pen stroke, not a connector. Fields: `_position.offsetPx`, `points` (a list of `x, y`), transform fields, `style` with `lc` (colour), `t` (thickness, 4 in the sample), `lo` and `e`. Calculated point arrays (a wave and a zigzag) pasted as strokes (paste confirmed). Paint has no endpoints, so it does not follow other objects.

## Frame, `widgetData.type: "frame"`

Fields: plain-text `text` (the title), `x`, `y`, `width`, `height`, `_position.offsetPx`, `size`, transform fields, `style` (`fs`, `tc`, `ta`, `ff`, `ss`, `sc`, `bc`, `fo`, `fd`), `boardId`, `prevFrameIndex`, `isClusteringContainer`. Position and size appear twice; change both. A renamed and resized frame pasted (paste confirmed). Whether objects pasted with a frame become its children has not been tested.

## Grid and cells, `grid` plus `grid_text`

An older table type: one `grid` object and one `grid_text` per cell. `grid.gridRoot` holds `columnsOrder`, `columns`, `rowsOrder`, `rows`, styles and merges. Each cell has HTML in `html`, `_position` with `schema: "gridOffsetPx"`, row and column IDs, and `_parent.index` pointing to the grid. A 2 x 2 grid with edited cells pasted and rendered small (paste confirmed). Adding rows or columns has not been tested.

## Data table, `widgetData.type: "data_table_widget"`

A newer table type. The clipboard holds `tableId` and `viewId`, not cell values. It pasted as a table shell; the source table was empty too. New tables cannot be created from cell content through this format.

## Image, `widgetData.type: "image"`

Holds position, scale, crop, title, alt text, a border style and a `resource` object (ID, board ID, name, dimensions). No pixels. A copy pasted with its pixels on the source account. Other boards, other accounts and new images have not been tested.

## Group, object `type: 10`

No `widgetData`; `items` lists member indexes, and the group record comes after its members. A generated group of two shapes and a connector pasted and moved together (paste confirmed). Editing a child and ungrouping have not been tested.

## Reusing captures

A capture made three weeks earlier still served as a template (paste confirmed, on the same board). A connector from that old capture, added to stickies copied that day, pasted and stayed attached (paste confirmed). The composer's `--add-template` option does this merge. Pasting on a different board has not been tested.

## Not captured yet

Cards, mind-map nodes, documents, embeds, comments, reactions, icons, kanban and app widgets. Do not infer their structure from other objects. Copy a small disposable sample, capture it, and read it first.

## Working with a real selection

1. Select only the objects the question needs, copy, and capture with `swift scripts/miro-clipboard-lab.swift capture /path/capture.json`.
2. Summarise with `python3 scripts/miro-clipboard-read.py /path/capture.json`. Add `--decode-to /path/decoded.json` only when you need every field.
3. Keep the original capture unchanged. Either compose new objects from a scene, or edit a copy of the decoded JSON and encode it with `--encode-from ... --write-capture ...`. The encoder checks IDs and every index reference and confirms the round trip.
4. Replay with `swift scripts/miro-clipboard-lab.swift replay /path/output.json` and paste in Miro.
5. Check the result: edit text, move shapes to test connectors, resize, and reload the board when persistence matters.

An agent in a sandbox may be able to read files but not the live clipboard. In that case it gives the user the exact capture and replay commands to run in their own Terminal.
