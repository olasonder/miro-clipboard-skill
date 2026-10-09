#!/usr/bin/env python3
"""Compose editable Miro objects from copied object templates.

Input and output are local captures made by miro-clipboard-lab.swift. This uses
an observed, undocumented Miro clipboard encoding; it makes no network calls.
See references/observed-format.md for every field and what has been verified.
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

# Friendly scene keys mapped to keys inside each object's style string.
# Observed in captured objects; "verified" means a Miro paste showed the effect.
STYLE_KEYS = {
    "sticker": {"color": "sbc"},                                   # verified
    "shape": {"color": "bc", "fill": "bc", "border_color": "brc",  # verified together
              "border_width": "brw", "radius": "brr",              # verified together
              "text_color": "tc", "font_size": "fs"},              # observed only
    "text": {"color": "tc", "text_color": "tc", "background": "bc"},  # observed only
    "line": {"color": "lc", "thickness": "t",                      # observed only
             "start_arrow": "a_start", "end_arrow": "a_end"},
    "paint": {"color": "lc", "thickness": "t"},                    # observed only
}
COLOR_KEYS = {"sbc", "bc", "brc", "tc", "lc", "sc"}
VERIFIED_LINE_TARGETS = {"shape"}


def warn(message: str) -> None:
    print(f"warning: {message}", file=sys.stderr)


def load_html_capture(path: Path) -> str:
    capture = json.loads(path.read_text())
    for item in capture["items"]:
        for representation in item["representations"]:
            if representation["type"] == "public.html":
                return base64.b64decode(representation["data"]).decode("utf-8")
    raise ValueError("Capture has no public.html representation")


def decode_miro_json(html_text: str) -> dict:
    match = MARKER.search(html_text)
    if not match:
        raise ValueError("HTML has no miro-data-v1 payload")
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


def apply_style(kind: str, fields: dict, spec: dict) -> None:
    updates = {}
    for key, style_key in STYLE_KEYS.get(kind, {}).items():
        if key in spec:
            value = spec[key]
            updates[style_key] = parse_color(value) if style_key in COLOR_KEYS else value
    for style_key, value in spec.get("style", {}).items():
        updates[style_key] = parse_color(value) if style_key in COLOR_KEYS and isinstance(value, str) else value
    if updates:
        set_style(fields, **updates)


def set_html_text(fields: dict, text: str) -> None:
    """Escape text and keep line breaks as separate paragraphs."""
    paragraphs = text.split("\n")
    fields["text"] = "".join("<p>" + html.escape(line, quote=False) + "</p>" for line in paragraphs)


def subset(document: dict, indexes: list[int]) -> dict:
    """Keep selected objects and rebase every index reference (lines, groups, grid parents)."""
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


def compose(template: dict, notes: list[dict]) -> dict:
    """Clone the first copied sticky note into several notes."""
    stickers = [obj for obj in template["data"]["objects"]
                if obj.get("widgetData", {}).get("type") == "sticker"]
    if not stickers:
        raise ValueError("Template must contain a copied Miro sticky note")
    return compose_mixed(template, [dict(note, type="sticker") for note in notes], keep_template_ids=True)


def compose_mixed(template: dict, specs: list[dict], keep_template_ids: bool = False) -> dict:
    source_objects = template["data"]["objects"]
    sources = {}
    for obj in source_objects:
        kind = obj.get("widgetData", {}).get("type")
        if kind and kind not in sources:
            sources[kind] = obj
    if not specs:
        raise ValueError("Scene must contain at least one object")
    document = copy.deepcopy(template)
    objects = []
    used_ids = set()
    for index, spec in enumerate(specs):
        kind = spec["type"]
        if "template_index" in spec:
            source = source_objects[spec["template_index"]]
            if source.get("widgetData", {}).get("type") != kind:
                raise ValueError(f"Template index {spec['template_index']} is not a {kind}")
        else:
            source = sources.get(kind)
        if source is None:
            available = ", ".join(sorted(sources)) or "none"
            raise ValueError(f"No copied {kind!r} object in the template capture (available: {available}). "
                             f"Copy one {kind} in Miro, add it to the template selection and capture again.")
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
            if "from" in spec and "to" in spec:
                for end in (spec["from"], spec["to"]):
                    if not 0 <= end < index:
                        raise ValueError("Connected line endpoints must refer to earlier objects in the scene")
                    target_kind = objects[end]["widgetData"]["type"]
                    if target_kind == "line":
                        raise ValueError("A line cannot attach to another line")
                    if target_kind not in VERIFIED_LINE_TARGETS:
                        warn(f"line {index} attaches to a {target_kind}; only shape-to-shape connectors "
                             "have been verified in Miro. Check the paste.")
                fields["primary"] = {"point": {"x": 1, "y": 0.5}, "positionType": 0, "widgetIndex": spec["from"]}
                fields["secondary"] = {"point": {"x": 0, "y": 0.5}, "positionType": 0, "widgetIndex": spec["to"]}
                fields["points"] = spec.get("bend_points", [])
            elif all(key in spec for key in ("x1", "y1", "x2", "y2")):
                fields["primary"] = {"point": {"x": spec["x1"], "y": spec["y1"]}, "positionType": 0, "widgetIndex": -1}
                fields["secondary"] = {"point": {"x": spec["x2"], "y": spec["y2"]}, "positionType": 0, "widgetIndex": -1}
                fields["points"] = []
            else:
                raise ValueError("Line needs from/to object indices or x1/y1/x2/y2")
            if "caption" in spec:
                captions = fields.get("line", {}).get("captions") or []
                if not captions:
                    raise ValueError("This line template has no caption to edit; copy a line with a label")
                captions[0]["text"] = "<p>" + html.escape(spec["caption"], quote=False) + "</p>"
                del captions[1:]
        else:
            for key in ("x", "y"):
                if not isinstance(spec.get(key), (int, float)):
                    raise ValueError(f"Object {index} ({kind}) needs numeric x and y")
            fields["_position"]["offsetPx"] = {"x": spec["x"], "y": spec["y"]}
        if "text" in spec:
            if not isinstance(spec["text"], str) or not spec["text"].strip():
                raise ValueError(f"Object {index} needs nonempty text")
            set_html_text(fields, spec["text"])
        if "width" in spec or "height" in spec:
            if "size" not in fields:
                raise ValueError(f"{kind} has no size field")
            for dimension in ("width", "height"):
                if dimension in spec:
                    fields["size"][dimension] = spec[dimension]
        if "rotation" in spec:
            fields["rotation"] = {"rotation": spec["rotation"]}
            fields["relativeRotation"] = spec["rotation"]
        if "points" in spec:
            if kind != "paint":
                raise ValueError("Only a paint object can use points")
            fields["points"] = spec["points"]
        apply_style(kind, fields, spec)
        objects.append(obj)
    document["data"]["objects"] = objects
    validate(document)
    return document


def write_capture(source_html: str, document: dict, output: Path) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Capture of copied Miro template objects")
    parser.add_argument("scene", type=Path, help="JSON file with a notes or objects array")
    parser.add_argument("output", type=Path, help="Destination capture JSON")
    args = parser.parse_args()

    scene = json.loads(args.scene.read_text())
    source_html = load_html_capture(args.template)
    template = decode_miro_json(source_html)
    if "objects" in scene:
        specs = scene["objects"]
        document = compose_mixed(template, specs)
    else:
        specs = scene["notes"]
        document = compose(template, specs)
    write_capture(source_html, document, args.output)
    print(f"Wrote {len(specs)} Miro objects to {args.output}")


if __name__ == "__main__":
    main()
