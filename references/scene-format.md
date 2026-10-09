# Scene format

The composer takes a capture of copied template objects, a JSON scene and an output path:

```sh
python3 scripts/miro-clipboard-compose.py /path/template.json /path/scene.json /path/output.json
swift scripts/miro-clipboard-lab.swift replay /path/output.json
```

Run the replay in a macOS session that can reach the user's clipboard, then paste in Miro. Every new object is a clone of a copied template object of the same type, so the template capture must contain at least one object of each type the scene uses. The composer validates IDs and references before it writes anything.

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
  {"type": "shape", "x": 0, "y": 0, "width": 180, "height": 90, "text": "Assumption", "fill": "#D8E8FF"},
  {"type": "shape", "x": 300, "y": 0, "width": 180, "height": 90, "text": "Test"},
  {"type": "sticker", "x": 0, "y": 200, "text": "Evidence", "color": "#FFF79E"},
  {"type": "line", "from": 0, "to": 1, "caption": "tested by"},
  {"type": "line", "x1": 0, "y1": 300, "x2": 200, "y2": 300}
]}
```

## Fields

All types:

| Field | Use |
|---|---|
| `type` | `sticker`, `shape`, `text`, `line` or `paint` |
| `template_index` | index of the template object to clone, when the template has several of that type (for example a circle and a rectangle). Default: the first object of that type |
| `x`, `y` | position on the canvas (all but `line`) |
| `text` | plain text; escaped for you. `\n` starts a new paragraph |
| `width`, `height` | size, when the object has one |
| `rotation` | degrees |
| `style` | raw style keys to merge, for example `{"brs": 1}`. Colour keys accept `"#RRGGBB"` |

Friendly style fields:

| Type | Field | Style key | Status |
|---|---|---|---|
| sticker | `color` | `sbc` | verified |
| shape | `fill` or `color` | `bc` | verified with others |
| shape | `border_color`, `border_width`, `radius` | `brc`, `brw`, `brr` | verified with others |
| shape | `text_color`, `font_size` | `tc`, `fs` | observed only |
| text | `color` / `text_color`, `background` | `tc`, `bc` | observed only |
| line | `color`, `thickness`, `start_arrow`, `end_arrow` | `lc`, `t`, `a_start`, `a_end` | observed only |
| paint | `color`, `thickness` | `lc`, `t` | observed only |

Colours accept `"#RRGGBB"`, a decimal integer, or `"transparent"`.

Lines:

| Field | Use |
|---|---|
| `from`, `to` | indexes of **earlier** objects in the same scene; the line stays attached when they move |
| `bend_points` | optional list of `{"x": ..., "y": ...}` |
| `x1`, `y1`, `x2`, `y2` | a free line instead of an attached one |
| `caption` | label text; the template line must have been copied with a label |

Only shape-to-shape connectors are verified. Attaching to stickies or text works in the composer but prints a warning; check the paste.

Paint: `points` is a list of `{"x": ..., "y": ...}` relative to the stroke's position.

## Layout tips

- Measure the template first. A sticky's footprint is `size` times `scale`; in the captured sample that was about 86 x 98, and a 180 x 160 grid of positions kept notes apart.
- Put cluster headers (shapes or text) above their notes and leave at least one note's width between clusters.
- Positions are relative: a paste keeps the layout between objects. Tell the user to paste in an empty area next to the original.

The composer clones style and metadata from the template objects. For fields it does not expose, decode the full JSON, edit the nested field and encode it again (see [observed-format.md](observed-format.md)).
