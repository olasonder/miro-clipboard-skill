# Observed Miro clipboard format

Observed in Miro running in Chrome on macOS in September 2026. This is an undocumented format, not a public Miro API.

`public.html` contains a `data-meta` attribute with `(miro-data-v1)` and `(/miro-data-v1)` around Base64. Decode that Base64, subtract 59 from each byte modulo 256, and parse the resulting UTF-8 JSON. Encoding reverses the steps. The capture file itself also Base64 encodes each raw pasteboard representation.

The decoded document contains `data.objects`. Most objects have an `id` equal to their array index, a numeric-string `initialId`, `meta`, and `widgetData`. `widgetData.type` identifies the object kind; `widgetData.json` holds position, content, style, and relationships. Some styles are JSON strings inside that JSON.

Observed object kinds include `sticker`, `shape`, `text`, `line`, `paint`, `frame`, `grid`, `grid_text`, `image`, and `data_table_widget`. A group is a separate object with an `items` array of member indices. Connected line endpoints use `primary.widgetIndex` and `secondary.widgetIndex` to point at objects in the same selection. A value of `-1` means a free endpoint. Grid cells point to their grid through `_parent.index`.

The tested composer can create copied stickies, shapes, text boxes, freehand strokes, connected lines, and free lines. Miro confirmed that a generated shape connector remained attached after moving a shape. Generated groups, grids, frames, and style variations were also pasted in experiments, but they are not exposed as scene composer operations.

Image objects contain resource references rather than pixels in the inspected JSON. Data-table widgets contain table and view IDs rather than inline cell content. Cross-board portability remains unknown. Clipboard captures may contain board, organization, author, object, and resource IDs along with private text. Store captures outside Git, and share summaries only when the text itself may be shared.
