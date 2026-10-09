# Scene format

The composer takes a capture of copied template objects, a JSON scene and an output path:

```sh
python3 scripts/miro-clipboard-compose.py /path/template.json /path/scene.json /path/output.json
swift scripts/miro-clipboard-lab.swift replay /path/output.json
```

Every new object is a clone of a copied template object of the same type, so the template capture must contain at least one object of each type the scene uses. The composer checks every field, ID and reference before it writes anything, and stops with `error: ...` on anything it does not understand, including misspelled fields. Lines starting with `warning:` mean "this works locally but has not been verified in Miro; check the paste".

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

`sticker` (sticky note; `sticky` and `note` are accepted too), `shape`, `text`, `line` (`connector` accepted) and `paint`. Frames, grids, images, data tables and groups cannot be composed; edit decoded JSON instead (SKILL.md section 3).

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
| `width`, `height` | size | verified for shapes and text; untested for stickies (warning) |
| `scale` | sets `scale` and `relativeScale` | untested (warning) |
| `rotation` | degrees | verified for shapes |
| `shape` | shapes only: `rectangle`/`square`, `ellipse`/`circle`/`oval`, `triangle`, `rhombus`/`diamond`, or a code. Sets `shape` and `st` together | codes verified; other codes warn |

A `\n` in `text` starts a new paragraph. That works in text boxes; in stickies it is untested.

Colour and style fields:

| Type | Field | Style key | Status |
|---|---|---|---|
| sticker | `color` | `sbc` | verified |
| shape | `fill` (or `color`) | `bc` | verified with others |
| shape | `border_color`, `border_width`, `radius` | `brc`, `brw`, `brr` | verified with others |
| shape | `text_color`, `font_size` | `tc`, `fs` | observed only |
| text | `color` or `text_color`; `background` | `tc`; `bc` | observed only |

Colours accept `"#RRGGBB"`, a decimal integer, or `"transparent"`. Note that `color` means the fill on shapes but the text colour on text boxes. There is no known key for the text colour of a sticky, so keep sticky colours light.

## Line

| Field | Use | Status |
|---|---|---|
| `from`, `to` | indexes of **earlier** objects in the scene. The line stays attached when they move | verified for shapes; other targets warn |
| `from_side`, `to_side` | `left`, `right`, `top` or `bottom`. Default: from the right side of `from` to the left side of `to` | right/left verified; top/bottom untested |
| `arrow` | `end` (default: points at `to`), `start`, `both` or `none` | end arrow verified |
| `caption` | label text. The template line must have been copied with a label. A line **without** `caption` gets no label, even if the template had one | caption text verified; removing a label untested |
| `bend_points` | list of `{"x": ..., "y": ...}`. One bend point produced a visible bend; its coordinate system has not been isolated, so avoid it unless needed | partly verified |
| `x1`, `y1`, `x2`, `y2` | a free line instead of an attached one | verified |
| `color`, `thickness` | `lc`, `t` | observed only |
| `start_arrow`, `end_arrow` | raw arrow codes (`9` showed an arrowhead, `0` none); override `arrow` | observed |

## Paint

`x`, `y`, `points` (a list of `{"x": ..., "y": ...}` relative to the stroke's position), `color`, `thickness`, `rotation`, `scale`.

## Layout tips

- Measure the template first. The reader's summary shows `size` and `scale`; a sticky's footprint is `size` times `scale`. In the sampled default that was about 86 x 98, and a grid with 180 between columns and 160 between rows kept notes apart.
- Whether `x, y` is an object's centre or corner has not been isolated. Keep shapes in one row at the same height so connectors line up.
- Put cluster headers above their notes, wrap columns at about five notes, and leave an empty column between clusters.
- Positions are relative: a paste keeps the layout between objects. Ask the user to paste in an empty area next to the original.

For fields the composer does not expose, decode the full JSON, edit the nested field and encode it again (see [observed-format.md](observed-format.md)).
