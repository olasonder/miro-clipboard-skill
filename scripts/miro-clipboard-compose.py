#!/usr/bin/env python3
"""Compose editable Miro objects from copied object templates.

Input and output are local captures made by miro-clipboard-lab.swift. This uses
an observed, undocumented Miro clipboard encoding; it makes no network calls.
"""

import argparse
import base64
import copy
import html
import json
import os
import re
from pathlib import Path


MARKER = re.compile(r"\(miro-data-v1\)(.*?)\(/miro-data-v1\)")


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


def compose(template: dict, notes: list[dict]) -> dict:
    source_objects = template["data"]["objects"]
    if len(source_objects) != 1 or source_objects[0]["widgetData"]["type"] != "sticker":
        raise ValueError("Template must contain exactly one copied Miro sticky note")
    if not notes:
        raise ValueError("Scene must contain at least one note")
    source = source_objects[0]
    try:
        initial_id = int(source["initialId"])
    except (KeyError, ValueError) as error:
        raise ValueError("Template sticky has no numeric initialId") from error

    document = copy.deepcopy(template)
    objects = []
    for index, note in enumerate(notes):
        text = note["text"]
        x, y = note["x"], note["y"]
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f"Note {index + 1} needs nonempty text")
        if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            raise ValueError(f"Note {index + 1} needs numeric x and y")
        obj = copy.deepcopy(source)
        obj["id"] = index
        obj["initialId"] = str(initial_id + index)
        fields = obj["widgetData"]["json"]
        fields["_position"]["offsetPx"] = {"x": x, "y": y}
        fields["text"] = "<p>" + html.escape(text, quote=False) + "</p>"
        objects.append(obj)
    document["data"]["objects"] = objects
    return document


def compose_mixed(template: dict, specs: list[dict]) -> dict:
    sources = {
        obj["widgetData"]["type"]: obj
        for obj in template["data"]["objects"]
        if "widgetData" in obj
    }
    source_objects = template["data"]["objects"]
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
            raise ValueError(f"No copied {kind!r} object in the template capture")
        obj = copy.deepcopy(source)
        obj["id"] = index
        # A tested multi-sticky paste accepted fresh sequential initialId values.
        initial_id = str(int(obj["initialId"]) + index + 1)
        while initial_id in used_ids:
            initial_id = str(int(initial_id) + 1)
        obj["initialId"] = initial_id
        used_ids.add(initial_id)
        fields = obj["widgetData"]["json"]
        if kind == "line":
            if "from" in spec and "to" in spec:
                if not (0 <= spec["from"] < index and 0 <= spec["to"] < index):
                    raise ValueError("Connected line endpoints must refer to earlier objects")
                if any(objects[target]["widgetData"]["type"] != "shape" for target in (spec["from"], spec["to"])):
                    raise ValueError("This line template currently connects shapes")
                fields["primary"] = {"point": {"x": 1, "y": 0.5}, "positionType": 0, "widgetIndex": spec["from"]}
                fields["secondary"] = {"point": {"x": 0, "y": 0.5}, "positionType": 0, "widgetIndex": spec["to"]}
                fields["points"] = []
            elif all(key in spec for key in ("x1", "y1", "x2", "y2")):
                fields["primary"] = {"point": {"x": spec["x1"], "y": spec["y1"]}, "positionType": 0, "widgetIndex": -1}
                fields["secondary"] = {"point": {"x": spec["x2"], "y": spec["y2"]}, "positionType": 0, "widgetIndex": -1}
                fields["points"] = []
            else:
                raise ValueError("Line needs from/to object indices or x1/y1/x2/y2")
        else:
            fields["_position"]["offsetPx"] = {"x": spec["x"], "y": spec["y"]}
        if "text" in spec:
            fields["text"] = "<p>" + html.escape(spec["text"], quote=False) + "</p>"
        if "width" in spec or "height" in spec:
            if "size" not in fields:
                raise ValueError(f"{kind} has no size field")
            for dimension in ("width", "height"):
                if dimension in spec:
                    fields["size"][dimension] = spec[dimension]
        if "points" in spec:
            if kind != "paint":
                raise ValueError("Only a paint object can use points")
            fields["points"] = spec["points"]
        objects.append(obj)
    document["data"]["objects"] = objects
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path, help="Capture of copied Miro template objects")
    parser.add_argument("scene", type=Path, help="JSON file with a notes or objects array")
    parser.add_argument("output", type=Path, help="Destination capture JSON")
    args = parser.parse_args()

    scene = json.loads(args.scene.read_text())
    source_html = load_html_capture(args.template)
    if "objects" in scene:
        specs = scene["objects"]
        document = compose_mixed(decode_miro_json(source_html), specs)
    else:
        specs = scene["notes"]
        document = compose(decode_miro_json(source_html), specs)
    output_html = encode_miro_json(source_html, document)
    # The visible HTML is only a fallback. Keep it aligned with generated content.
    prefix, separator, _ = output_html.partition("</span>")
    if separator:
        fallback = "<div>" + "".join(
            "<div>" + html.escape(item["text"]) + "</div>" for item in specs if "text" in item
        ) + "</div>"
        output_html = prefix + separator + fallback
    capture = {
        "items": [{"representations": [{
            "type": "public.html",
            "data": base64.b64encode(output_html.encode("utf-8")).decode("ascii"),
        }]}]
    }
    args.output.write_text(json.dumps(capture, separators=(",", ":")))
    os.chmod(args.output, 0o600)
    print(f"Wrote {len(specs)} Miro objects to {args.output}")


if __name__ == "__main__":
    main()
