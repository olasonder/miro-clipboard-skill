# Scene format

The composer takes a capture of copied template objects, a JSON scene and an output path:

```sh
python3 scripts/miro-clipboard-compose.py /path/template.json /path/scene.json /path/output.json
swift scripts/miro-clipboard-lab.swift replay /path/output.json
```

Every new object is a clone of a copied template object of the same type, so the template capture must contain at least one object of each type the scene uses. If one capture lacks a type, add another capture with `--add-template other.json` (repeatable); its objects get the next indexes. List all template objects with their index, type, shape, size, colour, label and text:

```sh
python3 scripts/miro-clipboard-compose.py /path/template.json --add-template /path/other.json --show-templates
```

After composing, check the layout: `python3 scripts/miro-clipboard-read.py /path/output.json --check` reports overlapping objects, objects outside their frame and broken references. Add `--against /path/input.json` to also list input stickies whose exact text is missing from the output (merged duplicates show up there on purpose). The composer checks every field, ID and reference before it writes anything, and stops with `error: ...` on anything it does not understand, including misspelled fields. Lines starting with `warning:` mean "this works locally but has not been verified in Miro; check the paste".

## Notes only

The template needs at least one sticky note; the first one is cloned.

```json
{"notes": [
  {"text": "What do we know?", "x": 0, "y": 0},
  {"text": "What should we test?", "x": 180, "y": 0, "color": "#C8F7C5"}
]}
```

## Mixed objects

```json
{"objects": [
  {"type": "shape", "x": 0, "y": 0, "width": 160, "height": 90, "text": "Start"},
  {"type": "shape", "x": 260, "y": 0, "width": 160, "height": 90, "text": "Paid?", "shape": "diamond"},
  {"type": "shape", "x": 520, "y": 0, "width": 160, "height": 90, "text": "Ship order"},
  {"type": "shape", "x": 260, "y": 200, "width": 160, "height": 90, "text": "Send reminder"},
  {"type": "line", "from": 0, "to": 1},
  {"type": "line", "from": 1, "to": 2, "caption": "yes"},
  {"type": "line", "from": 1, "to": 3, "from_side": "bottom", "to_side": "top", "caption": "no"}
]}
```

## Types

`sticker` (sticky note; `sticky` and `note` are accepted too), `shape`, `text`, `line` (`connector` accepted), `paint`, `frame` and `group`. Grids, images and data tables cannot be composed; edit decoded JSON instead (SKILL.md section 3).

## Fields for every type

| Field | Use |
|---|---|
| `type` | required |
| `template_index` | index (from the reader's summary) of the template object to clone. Needed when the template has several objects of one type, for example a rectangle and a diamond. Default: the first object of that type |
| `style` | raw style keys to merge, for example `{"brs": 1}`. Colour keys accept `"#RRGGBB"` |

## Sticker, shape, text

| Field | Use | Status |
|---|---|---|
| `x`, `y` | position; required | verified |
| `text` | plain text, escaped for you. **Required**, unless `template_index` is set: then the clone keeps that object's text (use this to move notes without retyping them) | verified |
| `width`, `height` | size | verified for shapes and text. On a sticky it changes the shape (doubling both gave a wide rectangle), not the size; the composer warns |
| `scale` | sets `scale` and `relativeScale`. To make a sticky twice as big, double the template's scale | verified for stickies; other types warn |
| `rotation` | degrees. Cloned notes keep their tilt; set `0` to straighten them | verified for shapes and stickies |
| `shape` | shapes only: `rectangle`/`square`, `ellipse`/`circle`/`oval`, `triangle`, `rhombus`/`diamond`, or a code. Sets `shape` and `st` together | codes verified; other codes warn |

A `\n` in `text` starts a new paragraph (verified in text boxes and stickies; Miro shrinks a sticky's font to fit).

Colour and style fields:

| Type | Field | Style key | Status |
|---|---|---|---|
| sticker | `color` | `sbc` | verified |
| sticker | `font_size` | `fs`, and `fsa: 0` | verified: every note gets the same text size (14 is small, 20 to 24 reads well). Without it Miro fits the text, so short notes get huge letters |
| shape | `fill` (or `color`) | `bc` | verified with others |
| shape | `border_color`, `border_width`, `radius` | `brc`, `brw`, `brr` | verified with others |
| shape | `text_color`, `font_size` | `tc`, `fs` | observed only |
| text | `color` or `text_color`; `background` | `tc`; `bc` | observed only |

Colours accept `"#RRGGBB"`, a decimal integer, or `"transparent"`. Note that `color` means the fill on shapes but the text colour on text boxes. For stickies, use the sixteen palette values in [observed-format.md](observed-format.md); on the black sticky Miro made the text white by itself.

## Line

| Field | Use | Status |
|---|---|---|
| `from`, `to` | indexes of **earlier** objects in the scene. The line stays attached when they move | verified for shapes and stickies; other targets warn |
| `from_side`, `to_side` | `left`, `right`, `top` or `bottom`. Default: from the right side of `from` to the left side of `to` | verified |
| `arrow` | `end` (default: points at `to`), `start`, `both` or `none` | end arrow verified |
| `caption` | label text. The template line must have been copied with a label. A line **without** `caption` gets no label, even if the template had one | verified |
| `bend_points` | list of `{"x": ..., "y": ...}`. One bend point produced a visible bend; its coordinate system has not been isolated, so avoid it unless needed | partly verified |
| `x1`, `y1`, `x2`, `y2` | a free line instead of an attached one | verified |
| `color`, `thickness` | `lc`, `t` | observed only |
| `start_arrow`, `end_arrow` | raw arrow codes (`9` showed an arrowhead, `0` none); override `arrow` | observed |

## Frame

```json
{"type": "frame", "x": 900, "y": 600, "width": 1800, "height": 1200, "text": "Synthesis", "contains": "all"}
```

| Field | Use |
|---|---|
| `x`, `y` | the frame's centre |
| `width`, `height` | its size |
| `text` | the title (plain text) |
| `contains` | `"all"` for every later object in the scene, or a list of scene indexes. These become the frame's children: they move with it. Without `contains` the frame is only drawn behind them |

Put the frame **first** (or at least before its contents), so it sits behind them. Give the contents ordinary board positions; the composer converts them to positions inside the frame. A copied frame is needed as template (any frame; `--add-template` can bring one from another capture). Verified: a frame with 63 children pasted, and all of them moved with it.

## Group

```json
{"type": "group", "items": [12, 13, 14]}
```

`items` lists indexes of **earlier** objects in the scene; Miro then moves them as one piece. No template needed. Verified for shapes with a connector, and for stickies with a text box.

## Paint (pen strokes)

The easy way: give the stroke as board coordinates and let the composer place it.

```json
{"type": "paint", "path": [[100, 50], [140, 90], [120, 150]], "color": "#1A1A1A", "thickness": 2}
```

| Field | Use | Status |
|---|---|---|
| `path` | list of `[x, y]` (or `{"x": .., "y": ..}`) in board coordinates. Sample curves densely (20 to 60 points) for smooth lines | verified: 57 strokes lined up into one drawing |
| `x`, `y`, `points` | the raw form instead of `path`: the stroke's centre, and points measured from the stroke's own top-left corner | verified |
| `color`, `thickness` | `lc`, `t`. Thickness 1 to 3 suits line art; fractions such as 1.5 work | verified |
| `rotation`, `scale` | as for other objects | untested for strokes |

Every stroke is a separate object. To move a drawing as one piece, put it in a `frame` or a `group`. See `examples/mona-lisa.py` for a complete drawing.

## Layout tips

- `x, y` is the **centre** of an object.
- Measure the template first. The reader's summary shows `size` and `scale`; a sticky's footprint is `size` times `scale`. In the sampled default that was about 86 x 99: 120 between centres leaves a small gap, 180 by 160 leaves room to read.
- Put cluster headers above their notes, wrap columns at about five notes, and leave an empty column between clusters.
- Positions are relative: a paste keeps the layout between objects. Ask the user to paste in an empty area next to the original.

For fields the composer does not expose, decode the full JSON, edit the nested field and encode it again (see [observed-format.md](observed-format.md)).
