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
        scale = fields.get("scale")
        if isinstance(scale, dict) and isinstance(scale.get("scale"), (int, float)) and scale["scale"] != 1:
            row["scale"] = round(scale["scale"], 4)
        for key in ("text", "html"):
            if isinstance(fields.get(key), str) and fields[key]:
                row["text"] = plain_text(fields[key])
                break
        style = fields.get("style")
        if isinstance(style, str):
            try:
                style = json.loads(style)
            except ValueError:
                style = None
        if isinstance(style, dict):
            for key in ("sbc", "bc", "lc"):
                if isinstance(style.get(key), int) and style[key] >= 0:
                    row["color"] = "#%06X" % style[key]
                    break
            if widget["type"] == "text" and isinstance(style.get("tc"), int) and style["tc"] >= 0:
                row["text_color"] = "#%06X" % style["tc"]
        if "shape" in fields:
            row["shape_code"] = fields["shape"]
        if widget["type"] == "line":
            row["from"] = fields["primary"]["widgetIndex"]
            row["to"] = fields["secondary"]["widgetIndex"]
            row["bend_points"] = len(fields.get("points", []))
            captions = (fields.get("line") or {}).get("captions") or []
            labels = [plain_text(c.get("text", "")) for c in captions if c.get("text")]
            if labels:
                row["caption"] = " / ".join(labels)
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
    compose_module.validate(document)
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
    parser.add_argument("--compact", action="store_true",
                        help="Print one line per object instead of indented JSON")
    parser.add_argument("--subset", help="Comma-separated object indexes to keep, e.g. 0,3,5; "
                        "references are rebased. Use with --write-capture to make a template")
    args = parser.parse_args()
    if args.subset:
        if not args.write_capture:
            parser.error("--subset needs --write-capture")
        if args.decode_to or args.encode_from:
            parser.error("--subset cannot be combined with --decode-to or --encode-from")
        source_html = compose_module.load_html_capture(args.capture)
        document = compose_module.decode_miro_json(source_html)
        try:
            indexes = [int(part) for part in args.subset.split(",") if part.strip()]
            compose_module.write_capture(source_html, compose_module.subset(document, indexes), args.write_capture)
        except ValueError as error:
            raise SystemExit(f"error: {error}")
        print(f"Subset of {len(indexes)} objects saved locally: {args.write_capture}")
        return
    if bool(args.encode_from) != bool(args.write_capture):
        parser.error("--encode-from and --write-capture must be used together")
    if args.encode_from:
        try:
            write_edited_capture(args.capture, args.encode_from, args.write_capture)
        except (ValueError, KeyError) as error:
            raise SystemExit(f"error: {error}")
        print(f"Edited capture saved locally: {args.write_capture}")
        return
    try:
        document = compose_module.decode_miro_json(compose_module.load_html_capture(args.capture))
    except (ValueError, KeyError, OSError) as error:
        raise SystemExit(f"error: {error}")
    rows = summary(document)
    if args.compact:
        print(f"{len(rows)} objects")
        for row in rows:
            print(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps({"objects": len(rows), "summary": rows}, ensure_ascii=False, indent=2))
    if args.decode_to:
        args.decode_to.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n")
        os.chmod(args.decode_to, 0o600)
        print(f"Full decoded JSON saved locally: {args.decode_to}")


if __name__ == "__main__":
    main()
