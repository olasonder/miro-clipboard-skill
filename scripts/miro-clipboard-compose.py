#!/usr/bin/env python3
"""Compose editable Miro objects from copied object templates.

Input and output are local captures made by miro-clipboard-lab.swift. This uses
an observed, undocumented Miro clipboard encoding; it makes no network calls.
See references/scene-format.md for the scene fields and
references/observed-format.md for every Miro field and what has been verified.
"""

import argparse
import base64
import copy
import html
import json
import os
import re
import sys
from pathlib import Path


MARKER = re.compile(r"\(miro-data-v1\)(.*?)\(/miro-data-v1\)")

COMPOSABLE = {"sticker", "shape", "text", "line", "paint", "frame"}
TYPE_ALIASES = {"sticky": "sticker", "note": "sticker", "sticky_note": "sticker", "connector": "line"}

# Friendly scene keys mapped to keys inside each object's style string.
STYLE_KEYS = {
    "sticker": {"color": "sbc", "font_size": "fs"},
    "shape": {"color": "bc", "fill": "bc", "border_color": "brc", "border_width": "brw",
              "radius": "brr", "text_color": "tc", "font_size": "fs"},
    "text": {"color": "tc", "text_color": "tc", "background": "bc"},
    "line": {"color": "lc", "thickness": "t", "start_arrow": "a_start", "end_arrow": "a_end"},
    "paint": {"color": "lc", "thickness": "t"},
}
COLOR_KEYS = {"sbc", "bc", "brc", "tc", "lc", "sc"}
COMMON_KEYS = {"type", "template_index", "style"}
POSITIONED_KEYS = {"x", "y", "text", "width", "height", "rotation", "scale"}
ALLOWED_KEYS = {
    "sticker": COMMON_KEYS | POSITIONED_KEYS,
    "shape": COMMON_KEYS | POSITIONED_KEYS | {"shape"},
    "text": COMMON_KEYS | POSITIONED_KEYS,
    "paint": COMMON_KEYS | {"x", "y", "points", "rotation", "scale"},
    "frame": COMMON_KEYS | {"x", "y", "width", "height", "text", "contains"},
    "group": {"type", "items"},
    "line": COMMON_KEYS | {"from", "to", "from_side", "to_side", "bend_points",
                           "x1", "y1", "x2", "y2", "caption", "arrow"},
}
for _kind, _keys in STYLE_KEYS.items():
    ALLOWED_KEYS[_kind] |= set(_keys)
HINTS = {("sticker", "fill"): "use 'color'", ("sticker", "background"): "use 'color'",
         ("shape", "background"): "use 'fill'", ("text", "fill"): "use 'background'"}

# Shape codes seen in captures; others exist in Miro but have not been captured.
SHAPE_CODES = {"rectangle": "3", "square": "3", "ellipse": "4", "circle": "4", "oval": "4",
               "triangle": "5", "rhombus": "8", "diamond": "8"}
SIDES = {"left": {"x": 0, "y": 0.5}, "right": {"x": 1, "y": 0.5},
         "top": {"x": 0.5, "y": 0}, "bottom": {"x": 0.5, "y": 1}}
ARROWS = {"end", "start", "both", "none"}
VERIFIED_LINE_TARGETS = {"shape", "sticker"}


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def load_html_capture(path: Path) -> str:
    capture = json.loads(path.read_text())
    for item in capture.get("items", []):
        for representation in item.get("representations", []):
            if representation.get("type") == "public.html":
                return base64.b64decode(representation["data"]).decode("utf-8")
    raise ValueError(f"{path} has no public.html representation; is it a capture of a Miro copy?")


def decode_miro_json(html_text: str) -> dict:
    match = MARKER.search(html_text)
    if not match:
        raise ValueError("HTML has no miro-data-v1 payload; the capture is not a Miro copy")
    payload = base64.b64decode(match.group(1), validate=True)
    return json.loads(bytes((byte - 59) % 256 for byte in payload))


def encode_miro_json(html_text: str, document: dict) -> str:
    serialized = json.dumps(document, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
    payload = base64.b64encode(bytes((byte + 59) % 256 for byte in serialized)).decode("ascii")
    if not MARKER.search(html_text):
        raise ValueError("HTML has no miro-data-v1 payload")
    return MARKER.sub(lambda _: f"(miro-data-v1){payload}(/miro-data-v1)", html_text, count=1)


def parse_color(value: object) -> int:
    """Return Miro's decimal RGB number. Accepts '#RRGGBB', 'RRGGBB', an int, or 'transparent'."""
    if isinstance(value, bool):
        raise ValueError(f"Invalid color {value!r}")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip().lower()
        if text in ("transparent", "none"):
            return -1
        text = text.lstrip("#")
        if re.fullmatch(r"[0-9a-f]{6}", text):
            return int(text, 16)
    raise ValueError(f"Invalid color {value!r}; use '#RRGGBB', an integer, or 'transparent'")


def set_style(fields: dict, **updates: object) -> None:
    """Change selected keys in a style that Miro stores as a JSON string, keeping all others."""
    raw = fields.get("style")
    if raw is None:
        raise ValueError("This object has no style field")
    style = json.loads(raw) if isinstance(raw, str) else dict(raw)
    style.update(updates)
    fields["style"] = json.dumps(style, separators=(",", ":")) if isinstance(raw, str) else style


def get_style(fields: dict) -> dict:
    raw = fields.get("style")
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except ValueError:
            return {}
    return dict(raw or {})


def apply_style(kind: str, fields: dict, spec: dict) -> None:
    updates = {}
    for key, style_key in STYLE_KEYS.get(kind, {}).items():
        if key in spec:
            value = spec[key]
            updates[style_key] = parse_color(value) if style_key in COLOR_KEYS else value
    raw = spec.get("style", {})
    if not isinstance(raw, dict):
        raise ValueError("'style' must be an object of raw style keys")
    for style_key, value in raw.items():
        updates[style_key] = parse_color(value) if style_key in COLOR_KEYS and isinstance(value, str) else value
    if kind == "sticker" and "font_size" in spec:
        updates["fsa"] = 0  # fixed size; Miro's default (fs 0, fsa 1) fits the text automatically
    if updates:
        set_style(fields, **updates)


def set_html_text(fields: dict, text: str) -> None:
    """Escape text and keep line breaks as separate paragraphs."""
    fields["text"] = "".join("<p>" + html.escape(line, quote=False) + "</p>" for line in text.split("\n"))


def subset(document: dict, indexes: list[int]) -> dict:
    """Keep selected objects and rebase every index reference (lines, groups, grid parents)."""
    count = len(document["data"]["objects"])
    if len(set(indexes)) != len(indexes):
        raise ValueError("Subset indexes must be distinct")
    for index in indexes:
        if not 0 <= index < count:
            raise ValueError(f"Subset index {index} is outside 0..{count - 1}")
    result = copy.deepcopy(document)
    mapping = {old: new for new, old in enumerate(indexes)}
    objects = [copy.deepcopy(document["data"]["objects"][index]) for index in indexes]
    for index, obj in enumerate(objects):
        obj["id"] = index
        if "items" in obj:
            obj["items"] = [mapping[item] for item in obj["items"] if item in mapping]
        fields = obj.get("widgetData", {}).get("json", {})
        parent = fields.get("_parent")
        if isinstance(parent, dict) and "index" in parent:
            if parent["index"] not in mapping:
                raise ValueError(f"Object {indexes[index]} needs its parent {parent['index']} in the subset")
            parent["index"] = mapping[parent["index"]]
        if obj.get("widgetData", {}).get("type") == "line":
            for endpoint in ("primary", "secondary"):
                old = fields[endpoint]["widgetIndex"]
                if old != -1:
                    if old not in mapping:
                        raise ValueError(f"Line {indexes[index]} needs its endpoint {old} in the subset")
                    fields[endpoint]["widgetIndex"] = mapping[old]
    result["data"]["objects"] = objects
    return result


def validate(document: dict) -> None:
    objects = document["data"]["objects"]
    if [obj.get("id") for obj in objects] != list(range(len(objects))):
        raise ValueError("Object IDs must match their zero-based array indexes")
    initial_ids = [obj.get("initialId") for obj in objects]
    if len(set(initial_ids)) != len(initial_ids):
        raise ValueError("Every object needs a distinct initialId")
    for obj in objects:
        for child in obj.get("items", []):
            if not isinstance(child, int) or not 0 <= child < len(objects):
                raise ValueError("Group contains an invalid member index")
        fields = obj.get("widgetData", {}).get("json", {})
        parent = fields.get("_parent")
        if isinstance(parent, dict) and "index" in parent:
            if not isinstance(parent["index"], int) or not 0 <= parent["index"] < len(objects):
                raise ValueError("Object has an invalid parent index")
        if obj.get("widgetData", {}).get("type") == "line":
            for endpoint in ("primary", "secondary"):
                target = fields[endpoint]["widgetIndex"]
                if not isinstance(target, int) or not -1 <= target < len(objects):
                    raise ValueError("Line has an invalid endpoint index")


def check_spec(index: int, spec: object, count: int) -> str:
    """Validate one scene entry and return its normalised type."""
    if not isinstance(spec, dict):
        raise ValueError(f"Scene object {index} must be a JSON object")
    if "type" not in spec:
        raise ValueError(f"Scene object {index} needs a 'type' (sticker, shape, text, line or paint)")
    kind = TYPE_ALIASES.get(spec["type"], spec["type"])
    if kind == "group":
        unknown = sorted(set(spec) - ALLOWED_KEYS["group"])
        if unknown or not isinstance(spec.get("items"), list) or len(spec["items"]) < 2:
            raise ValueError(f"Scene object {index}: a group needs only 'items', a list of two or more earlier indexes")
        return kind
    if kind not in COMPOSABLE:
        raise ValueError(f"Scene object {index}: type {spec['type']!r} cannot be composed. Use sticker, shape, text, "
                         "line, paint, frame or group. For grids, images or data tables, edit decoded JSON "
                         "(SKILL.md section 3).")
    unknown = sorted(set(spec) - ALLOWED_KEYS[kind])
    if unknown:
        hints = "; ".join(f"'{key}': {HINTS.get((kind, key), 'not a ' + kind + ' field')}" for key in unknown)
        raise ValueError(f"Scene object {index} ({kind}) has unknown field(s): {hints}. See references/scene-format.md.")
    if "template_index" in spec:
        template_index = spec["template_index"]
        if not isinstance(template_index, int) or isinstance(template_index, bool) or not 0 <= template_index < count:
            raise ValueError(f"Scene object {index}: template_index must be an integer from 0 to {count - 1}")
    return kind


def merge_templates(template: dict, extra: dict) -> dict:
    """Append another capture's composable objects to a template, so one scene can use both.

    Verified in Miro: a connector from a three-week-old capture, added to sticky notes
    copied that day on the same board, pasted and stayed attached; a frame merged the
    same way worked too. Lines are detached; groups and grid relations are left out.
    """
    merged = copy.deepcopy(template)
    objects = merged["data"]["objects"]
    next_id = max(int(obj["initialId"]) for obj in objects) + 1000
    for obj in extra["data"]["objects"]:
        kind = obj.get("widgetData", {}).get("type")
        if kind not in COMPOSABLE:
            continue
        clone = copy.deepcopy(obj)
        if isinstance(clone["widgetData"]["json"].get("_parent"), dict):
            clone["widgetData"]["json"]["_parent"] = None
        clone["id"] = len(objects)
        clone["initialId"] = str(next_id)
        next_id += 1000
        fields = clone["widgetData"]["json"]
        if kind == "line":
            for endpoint in ("primary", "secondary"):
                fields[endpoint]["widgetIndex"] = -1
        objects.append(clone)
    validate(merged)
    return merged


def put_in_frame(document: dict, frame_index: int, members: "list[int] | None" = None) -> dict:
    """Make objects children of a frame, as Miro stores them after you drag them into it.

    A child gets `_parent: {"index": frame}` and a position relative to the frame's
    top-left corner (`schema: "parentOffsetPx"`, `containerType: "FRAME"`); a frame's
    own x, y is its centre. Lines get `_parent` only. Observed in a copy of a frame
    whose children Miro had attached; see references/observed-format.md.
    """
    result = copy.deepcopy(document)
    objects = result["data"]["objects"]
    frame = objects[frame_index]
    if frame.get("widgetData", {}).get("type") != "frame":
        raise ValueError(f"Object {frame_index} is not a frame")
    fields = frame["widgetData"]["json"]
    centre = fields["_position"]["offsetPx"]
    width = fields.get("width") or fields["size"]["width"]
    height = fields.get("height") or fields["size"]["height"]
    left, top = centre["x"] - width / 2, centre["y"] - height / 2
    if members is None:
        members = [i for i, obj in enumerate(objects) if i != frame_index and "widgetData" in obj]
    for index in members:
        obj = objects[index]
        kind = obj.get("widgetData", {}).get("type")
        if kind is None or kind == "frame":
            raise ValueError(f"Object {index} cannot be put in a frame")
        child = obj["widgetData"]["json"]
        child["_parent"] = {"index": frame_index}
        position = child.get("_position")
        if isinstance(position, dict) and position.get("schema") == "canvasOffsetPx":
            offset = position["offsetPx"]
            child["_position"] = {"offsetPx": {"x": offset["x"] - left, "y": offset["y"] - top},
                                  "schema": "parentOffsetPx", "containerType": "FRAME"}
    validate(result)
    return result


def compose(template: dict, notes: list[dict]) -> dict:
    """Clone the first copied sticky note into several notes."""
    if not isinstance(notes, list):
        raise ValueError("'notes' must be a list")
    return compose_mixed(template, [dict(note, type="sticker") for note in notes], keep_template_ids=True)


def compose_mixed(template: dict, specs: list[dict], keep_template_ids: bool = False) -> dict:
    if not isinstance(specs, list) or not specs:
        raise ValueError("Scene must contain a non-empty list of objects")
    source_objects = template["data"]["objects"]
    sources = {}
    for obj in source_objects:
        kind = obj.get("widgetData", {}).get("type")
        if kind and kind not in sources:
            sources[kind] = obj
    document = copy.deepcopy(template)
    objects = []
    used_ids = set()
    frames = []
    for index, spec in enumerate(specs):
        kind = check_spec(index, spec, len(source_objects))
        if kind == "group":
            objects.append(make_group(index, spec, objects, source_objects, used_ids))
            continue
        if "template_index" in spec:
            source = source_objects[spec["template_index"]]
            source_kind = source.get("widgetData", {}).get("type")
            if source_kind != kind:
                raise ValueError(f"Scene object {index}: template_index {spec['template_index']} is a "
                                 f"{source_kind or 'group'}, not a {kind}")
        else:
            source = sources.get(kind)
        if source is None:
            available = ", ".join(sorted(sources)) or "none"
            raise ValueError(f"Scene object {index}: the template capture has no {kind} to clone "
                             f"(it has: {available}). Check that you passed the template capture and spelled "
                             f"the type correctly; otherwise ask the user to copy one {kind} in Miro and capture again.")
        obj = copy.deepcopy(source)
        obj["id"] = index
        # Tested pastes accepted fresh sequential initialId values derived from the template.
        offset = index if keep_template_ids else index + 1
        initial_id = int(obj["initialId"]) + offset
        while str(initial_id) in used_ids:
            initial_id += 1
        obj["initialId"] = str(initial_id)
        used_ids.add(obj["initialId"])
        fields = obj["widgetData"]["json"]

        if kind == "line":
            compose_line(index, spec, fields, objects, get_style(source["widgetData"]["json"]))
        elif kind == "frame":
            for key in ("x", "y", "width", "height"):
                if not isinstance(spec.get(key), (int, float)) or isinstance(spec.get(key), bool):
                    raise ValueError(f"Frame {index} needs numeric x, y (its centre), width and height")
            fields["_position"] = {"offsetPx": {"x": spec["x"], "y": spec["y"]}, "schema": "canvasOffsetPx"}
            fields["x"], fields["y"] = spec["x"], spec["y"]
            fields["width"], fields["height"] = spec["width"], spec["height"]
            fields["size"] = {"width": spec["width"], "height": spec["height"]}
            fields["text"] = str(spec.get("text", "Frame"))  # frame titles are plain text, not HTML
            fields["_parent"] = None
            frames.append((index, spec.get("contains")))
        else:
            for key in ("x", "y"):
                if not isinstance(spec.get(key), (int, float)) or isinstance(spec.get(key), bool):
                    raise ValueError(f"Scene object {index} ({kind}) needs numeric x and y")
            fields["_position"]["offsetPx"] = {"x": spec["x"], "y": spec["y"]}
            if kind in ("sticker", "shape", "text"):
                if isinstance(fields.get("_position"), dict) and fields["_position"].get("schema") != "canvasOffsetPx":
                    fields["_position"] = {"offsetPx": fields["_position"]["offsetPx"], "schema": "canvasOffsetPx"}
                fields["_parent"] = None
                if "text" in spec:
                    if not isinstance(spec["text"], str) or not spec["text"].strip():
                        raise ValueError(f"Scene object {index} needs nonempty text")
                    set_html_text(fields, spec["text"])
                elif "template_index" not in spec:
                    raise ValueError(f"Scene object {index} ({kind}) needs 'text'. To keep an existing object's "
                                     "text (for example when moving notes), set template_index to that object.")
        if "shape" in spec:
            code = SHAPE_CODES.get(str(spec["shape"]).lower(), str(spec["shape"]))
            if code not in set(SHAPE_CODES.values()):
                warn(f"object {index}: shape code {code} has not been captured; copy that shape in Miro and "
                     "use it with template_index instead")
            fields["shape"] = code
            set_style(fields, st=int(code))
        if "width" in spec or "height" in spec:
            if "size" not in fields:
                raise ValueError(f"{kind} has no size field")
            if kind == "sticker":
                warn(f"object {index}: a sticky's width/height changes its shape (doubling both gave a wide, "
                     "rectangular note), not its size. To make a sticky bigger, use 'scale'.")
            for dimension in ("width", "height"):
                if dimension in spec:
                    fields["size"][dimension] = spec[dimension]
        if "scale" in spec:
            if not isinstance(spec["scale"], (int, float)) or spec["scale"] <= 0:
                raise ValueError(f"Scene object {index}: scale must be a positive number")
            fields["scale"] = {"scale": spec["scale"]}
            fields["relativeScale"] = spec["scale"]
            if kind != "sticker":
                warn(f"object {index}: scale is verified for sticky notes only; check the size after pasting")
        if "rotation" in spec:
            fields["rotation"] = {"rotation": spec["rotation"]}
            fields["relativeRotation"] = spec["rotation"]
        if "points" in spec:
            fields["points"] = spec["points"]
        apply_style(kind, fields, spec)
        objects.append(obj)
    document["data"]["objects"] = objects
    for frame_index, contains in frames:
        if contains is None:
            continue
        if contains == "all":
            members = [i for i, o in enumerate(objects)
                       if i > frame_index and o.get("widgetData", {}).get("type") not in (None, "frame")]
        elif isinstance(contains, list) and all(isinstance(i, int) for i in contains):
            members = contains
        else:
            raise ValueError(f"Frame {frame_index}: 'contains' must be \"all\" or a list of scene indexes")
        for member in members:
            if not frame_index < member < len(objects):
                raise ValueError(f"Frame {frame_index}: put the frame before its contents in the scene "
                                 f"(member {member} must come after it)")
        document = put_in_frame(document, frame_index, members)
    validate(document)
    return document


def make_group(index: int, spec: dict, objects: list, source_objects: list, used_ids: set) -> dict:
    """A group record lists earlier objects; Miro moves them as one piece."""
    items = spec["items"]
    for item in items:
        if not isinstance(item, int) or isinstance(item, bool) or not 0 <= item < index:
            raise ValueError(f"Group {index}: items must be indexes of earlier objects in the scene")
        if "widgetData" not in objects[item]:
            raise ValueError(f"Group {index}: nested groups are not supported")
    copied = [obj for obj in source_objects if obj.get("type") == 10 and "widgetData" not in obj]
    meta = copy.deepcopy(copied[0].get("meta", {}) if copied else objects[items[0]].get("meta", {}))
    initial_id = int(objects[items[-1]]["initialId"]) + 1
    while str(initial_id) in used_ids:
        initial_id += 1
    used_ids.add(str(initial_id))
    return {"type": 10, "items": list(items), "id": index, "initialId": str(initial_id), "meta": meta}


def compose_line(index: int, spec: dict, fields: dict, objects: list, template_style: dict) -> None:
    if "from" in spec or "to" in spec:
        ends = (spec.get("from"), spec.get("to"))
        for end in ends:
            if not isinstance(end, int) or isinstance(end, bool) or not 0 <= end < index:
                raise ValueError(f"Line {index}: 'from' and 'to' must be indexes of earlier objects in the scene")
            if objects[end]["widgetData"]["type"] == "line":
                raise ValueError(f"Line {index} cannot attach to another line")
        unverified = sorted({objects[end]["widgetData"]["type"] for end in ends} - VERIFIED_LINE_TARGETS)
        if unverified:
            warn(f"line {index} attaches to {', '.join(unverified)}; only connectors between shapes and "
                 "sticky notes have been verified in Miro. Check the paste.")
        sides = []
        for key, default in (("from_side", "right"), ("to_side", "left")):
            side = spec.get(key, default)
            if side not in SIDES:
                raise ValueError(f"Line {index}: {key} must be one of {', '.join(SIDES)}")
            sides.append(dict(SIDES[side]))
        fields["primary"] = {"point": sides[0], "positionType": 0, "widgetIndex": spec["from"]}
        fields["secondary"] = {"point": sides[1], "positionType": 0, "widgetIndex": spec["to"]}
        fields["points"] = spec.get("bend_points", [])
    elif all(key in spec for key in ("x1", "y1", "x2", "y2")):
        fields["primary"] = {"point": {"x": spec["x1"], "y": spec["y1"]}, "positionType": 0, "widgetIndex": -1}
        fields["secondary"] = {"point": {"x": spec["x2"], "y": spec["y2"]}, "positionType": 0, "widgetIndex": -1}
        fields["points"] = []
    else:
        raise ValueError(f"Line {index} needs from/to object indexes or x1/y1/x2/y2")

    # Never carry the template's label onto a new line.
    line_fields = fields.get("line")
    captions = (line_fields or {}).get("captions") or []
    if "caption" in spec:
        if not captions:
            raise ValueError(f"Line {index}: the template line has no label to edit; copy a line with a label")
        captions[0]["text"] = "<p>" + html.escape(str(spec["caption"]), quote=False) + "</p>"
        del captions[1:]
    elif captions:
        line_fields["captions"] = []

    # Arrow direction follows from -> to unless the scene says otherwise.
    head = max(template_style.get("a_start", 0) or 0, template_style.get("a_end", 0) or 0) or 9
    arrow = spec.get("arrow", "end")
    if arrow not in ARROWS:
        raise ValueError(f"Line {index}: arrow must be one of {', '.join(sorted(ARROWS))}")
    set_style(fields, a_start=head if arrow in ("start", "both") else 0,
              a_end=head if arrow in ("end", "both") else 0)


def write_capture(source_html: str, document: dict, output: Path) -> None:
    validate(document)
    output_html = encode_miro_json(source_html, document)
    if decode_miro_json(output_html) != document:
        raise ValueError("Encoded document did not round-trip")
    # The visible HTML is only a fallback for other apps. Keep it aligned with the content.
    prefix, separator, _ = output_html.partition("</span>")
    if separator:
        texts = []
        for obj in document["data"]["objects"]:
            fields = obj.get("widgetData", {}).get("json", {})
            value = fields.get("text") or fields.get("html")
            if isinstance(value, str) and value:
                texts.append(html.unescape(re.sub(r"<[^>]+>", " ", value)).strip())
        output_html = prefix + separator + "<div>" + "".join(
            "<div>" + html.escape(text) + "</div>" for text in texts if text) + "</div>"
    capture = {"items": [{"representations": [{
        "type": "public.html",
        "data": base64.b64encode(output_html.encode("utf-8")).decode("ascii"),
    }]}]}
    output.write_text(json.dumps(capture, separators=(",", ":")))
    os.chmod(output, 0o600)


def describe_template(index: int, obj: dict) -> str:
    kind = obj.get("widgetData", {}).get("type", "group")
    fields = obj.get("widgetData", {}).get("json", {})
    parts = [str(index), kind]
    if kind == "group":
        parts.append(f"items={obj.get('items')}")
    style = get_style(fields)
    if "shape" in fields:
        name = {v: k for k, v in SHAPE_CODES.items() if k in ("rectangle", "ellipse", "triangle", "rhombus")}
        parts.append(f"shape={name.get(fields['shape'], fields['shape'])}")
    size = fields.get("size")
    if isinstance(size, dict):
        scale = (fields.get("scale") or {}).get("scale", 1)
        parts.append(f"size={size.get('width')}x{size.get('height')}" + (f"*{scale:.4g}" if scale != 1 else ""))
    for key in ("sbc", "bc", "lc"):
        if isinstance(style.get(key), int) and style[key] >= 0:
            parts.append("color=#%06X" % style[key])
            break
    if kind == "line":
        captions = (fields.get("line") or {}).get("captions") or []
        parts.append("label=" + (re.sub(r"<[^>]+>", "", captions[0].get("text", "")) if captions else "none"))
    text = re.sub(r"<[^>]+>", " ", str(fields.get("text") or "")).strip()
    if text:
        parts.append(repr(text[:40]))
    return "\t".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Capture of copied Miro template objects")
    parser.add_argument("scene", type=Path, nargs="?", help="JSON file with a notes or objects array")
    parser.add_argument("output", type=Path, nargs="?", help="Destination capture JSON")
    parser.add_argument("--add-template", type=Path, action="append", default=[],
                        help="Another capture whose stickies, shapes, text, lines and pen strokes are added as extra "
                             "templates after the main template's objects. Use --show-templates to see their indexes")
    parser.add_argument("--show-templates", action="store_true",
                        help="Print the combined template objects with their indexes and stop")
    args = parser.parse_args()
    if not args.show_templates and (args.scene is None or args.output is None):
        parser.error("scene and output are required unless you use --show-templates")
    try:
        source_html = load_html_capture(args.template)
        template = decode_miro_json(source_html)
        for extra in args.add_template:
            template = merge_templates(template, decode_miro_json(load_html_capture(extra)))
        if args.show_templates:
            for index, obj in enumerate(template["data"]["objects"]):
                print(describe_template(index, obj))
            return
        scene = json.loads(args.scene.read_text())
        if not isinstance(scene, dict) or not ({"objects", "notes"} & set(scene)):
            raise ValueError("The scene must be a JSON object with an 'objects' or a 'notes' list")
        if "objects" in scene:
            specs = scene["objects"]
            document = compose_mixed(template, specs)
        else:
            specs = scene["notes"]
            document = compose(template, specs)
        write_capture(source_html, document, args.output)
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        sys.exit(1)
    print(f"Wrote {len(specs)} Miro objects to {args.output}")


if __name__ == "__main__":
    main()
