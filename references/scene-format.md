# Scene format

The composer takes a local Miro capture as a template, a JSON scene, and an output capture path:

```sh
python3 scripts/miro-clipboard-compose.py /path/template.json examples/notes.json /path/output.json
swift scripts/miro-clipboard-lab.swift replay /path/output.json
```

Run the Swift replay command in a macOS session with access to the user's clipboard. Then paste in Miro.

## Notes

For a template containing exactly one copied sticky note:

```json
{"notes":[{"text":"Question","x":0,"y":0},{"text":"Possible answer","x":260,"y":0}]}
```

## Mixed objects

For a template selection with the required object types:

```json
{"objects":[
  {"type":"shape","x":0,"y":0,"width":180,"height":90,"text":"Assumption"},
  {"type":"shape","x":300,"y":0,"width":180,"height":90,"text":"Test"},
  {"type":"line","from":0,"to":1}
]}
```

Supported positioned types are copied `shape`, `sticker`, `text`, and `paint` objects. `text`, `width`, `height`, and `points` are optional where the source object supports them. A `line` may connect two earlier shapes with `from` and `to` indices, or use free endpoints `x1`, `y1`, `x2`, `y2`. Set `template_index` to choose a particular object from the copied selection when it contains more than one of a type. Index values are zero based within the template or output array as appropriate.

The composer clones style and metadata from the sample objects. It does not expose all Miro properties. To change a field such as fill color or rotation, decode the full JSON and edit the relevant nested field, then encode the document again. Test the result in Miro.
