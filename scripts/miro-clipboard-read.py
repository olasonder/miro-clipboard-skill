#!/usr/bin/env python3
"""Summarize a captured Miro selection or decode its complete JSON locally."""

import argparse
import base64
import html
import importlib.util
import json
import os
import re
from pathlib import Path


COMPOSER_PATH = Path(__file__).with_name("miro-clipboard-compose.py")
module_spec = importlib.util.spec_from_file_location("miro_compose", COMPOSER_PATH)
compose_module = importlib.util.module_from_spec(module_spec)
module_spec.loader.exec_module(compose_module)


def plain_text(value: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", " ", value)).strip()


def summary(document: dict) -> list[dict]:
    objects = document["data"]["objects"]
    rows = []
    for index, obj in enumerate(objects):
        widget = obj.get("widgetData")
        if widget is None:
            rows.append({"index": index, "type": "group", "members": obj.get("items", [])})
            continue
        fields = widget.get("json", {})
        row = {"index": index, "type": widget["type"]}
        position = fields.get("_position")
        if isinstance(position, dict):
            row["position"] = position.get("offsetPx")
            if position.get("schema") == "gridOffsetPx":
                row["grid_cell"] = {"row": position.get("row"), "column": position.get("column")}
        if "size" in fields:
            row["size"] = fields["size"]
        for key in ("text", "html"):
            if isinstance(fields.get(key), str) and fields[key]:
                row["text"] = plain_text(fields[key])
                break
        if widget["type"] == "line":
            row["from"] = fields["primary"]["widgetIndex"]
            row["to"] = fields["secondary"]["widgetIndex"]
            row["bend_points"] = len(fields.get("points", []))
        if widget["type"] == "paint":
            row["points"] = len(fields.get("points", []))
        if widget["type"] == "image":
            row["resource_reference"] = bool(fields.get("resource", {}).get("id"))
        if widget["type"] == "data_table_widget":
            row["table_reference"] = bool(fields.get("tableId"))
        if widget["type"] == "grid_text":
            row["parent"] = fields.get("_parent", {}).get("index")
        rows.append(row)
    return rows


def validate_references(document: dict) -> None:
    objects = document["data"]["objects"]
    if [obj.get("id") for obj in objects] != list(range(len(objects))):
        raise ValueError("Object IDs must match their zero-based array indexes")
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
                if not isinstance(target, int) or not (-1 <= target < len(objects)):
                    raise ValueError("Line has an invalid endpoint index")


def write_edited_capture(template_capture: Path, edited_json: Path, output: Path) -> None:
    document = json.loads(edited_json.read_text())
    validate_references(document)
    template_html = compose_module.load_html_capture(template_capture)
    native_html = compose_module.encode_miro_json(template_html, document)
    if compose_module.decode_miro_json(native_html) != document:
        raise ValueError("Re-encoded document did not round-trip")
    prefix, separator, _ = native_html.partition("</span>")
    if separator:
        visible = "<div>" + "".join(
            "<div>" + html.escape(row["text"]) + "</div>"
            for row in summary(document) if "text" in row
        ) + "</div>"
        native_html = prefix + separator + visible
    capture = {"items": [{"representations": [{
        "type": "public.html",
        "data": base64.b64encode(native_html.encode("utf-8")).decode("ascii"),
    }]}]}
    output.write_text(json.dumps(capture, separators=(",", ":")))
    os.chmod(output, 0o600)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--decode-to", type=Path,
                        help="Write full decoded Miro JSON here; contains board data")
    parser.add_argument("--encode-from", type=Path,
                        help="Read an edited full JSON document and re-encode it")
    parser.add_argument("--write-capture", type=Path,
                        help="Write the re-encoded public.html capture here")
    args = parser.parse_args()
    if bool(args.encode_from) != bool(args.write_capture):
        parser.error("--encode-from and --write-capture must be used together")
    if args.encode_from:
        write_edited_capture(args.capture, args.encode_from, args.write_capture)
        print(f"Edited capture saved locally: {args.write_capture}")
        return
    document = compose_module.decode_miro_json(compose_module.load_html_capture(args.capture))
    rows = summary(document)
    print(json.dumps({"objects": len(rows), "summary": rows}, ensure_ascii=False, indent=2))
    if args.decode_to:
        args.decode_to.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        os.chmod(args.decode_to, 0o600)
        print(f"Full decoded JSON saved locally: {args.decode_to}")


if __name__ == "__main__":
    main()
