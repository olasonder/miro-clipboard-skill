#!/usr/bin/env python3
"""Local checks for the Python tools. Uses a synthetic template; needs no Miro and no clipboard."""

import base64
import importlib.util
import json
import tempfile
from pathlib import Path

HERE = Path(__file__).parent
spec = importlib.util.spec_from_file_location("compose", HERE / "miro-clipboard-compose.py")
compose = importlib.util.module_from_spec(spec)
spec.loader.exec_module(compose)


def obj(index, kind, **fields):
    base = {"_position": {"offsetPx": {"x": 0, "y": 0}, "schema": "canvasOffsetPx"}, "_parent": None}
    base.update(fields)
    return {"type": 14, "id": index, "initialId": str(1000 + index * 10), "meta": {},
            "widgetData": {"type": kind, "json": base}}


TEMPLATE = {"isProtected": False, "boardId": "synthetic", "version": 2, "host": "miro.com",
            "asPortalAmount": 0, "copierType": "COPY", "data": {"meta": {}, "objects": [
    obj(0, "sticker", text="<p>A</p>", size={"width": 199, "height": 228},
        style=json.dumps({"fs": 0, "fsa": 1, "ffn": "Noto Sans", "sbc": 16775070})),
    obj(1, "shape", text="<p>B</p>", shape="3", size={"width": 120, "height": 120},
        style=json.dumps({"st": 3, "bc": -1, "brc": 1710618, "brw": 2, "tc": 1710618, "fs": 14})),
    {"type": 14, "id": 2, "initialId": "1020", "meta": {}, "widgetData": {"type": "line", "json": {
        "_position": None, "points": [], "line": {"captions": [{"text": "<p>x</p>"}]},
        "primary": {"point": {"x": 1, "y": 0.5}, "positionType": 0, "widgetIndex": 1},
        "secondary": {"point": {"x": 0, "y": 0.5}, "positionType": 0, "widgetIndex": 0},
        "style": json.dumps({"lc": 3355443, "t": 2, "a_end": 9})}}},
    {"type": 10, "id": 3, "initialId": "1030", "items": [0, 1, 2]},
]}}


def main() -> None:
    html_text = '<span data-meta="<--(miro-data-v1)X(/miro-data-v1)-->"></span><div>A</div>'
    html_text = compose.encode_miro_json(html_text, TEMPLATE)
    assert compose.decode_miro_json(html_text) == TEMPLATE, "round trip"

    assert compose.parse_color("#A100FF") == 0xA100FF
    assert compose.parse_color("transparent") == -1

    notes = compose.compose(TEMPLATE, [
        {"text": "Café & ideeën 🙂", "x": 0, "y": 0},
        {"text": "two\nlines", "x": 200, "y": 0, "color": "#C8F7C5"}])
    objects = notes["data"]["objects"]
    assert [o["widgetData"]["type"] for o in objects] == ["sticker", "sticker"]
    assert objects[0]["widgetData"]["json"]["text"] == "<p>Café &amp; ideeën 🙂</p>"
    assert objects[1]["widgetData"]["json"]["text"] == "<p>two</p><p>lines</p>"
    assert json.loads(objects[1]["widgetData"]["json"]["style"])["sbc"] == 0xC8F7C5
    assert json.loads(objects[1]["widgetData"]["json"]["style"])["ffn"] == "Noto Sans", "other style keys kept"

    mixed = compose.compose_mixed(TEMPLATE, [
        {"type": "shape", "x": 0, "y": 0, "text": "S", "fill": "#D8E8FF", "radius": 8},
        {"type": "sticker", "x": 300, "y": 0, "text": "N", "color": "#FFC0CB"},
        {"type": "line", "from": 0, "to": 1, "caption": "leads to", "color": "#A100FF"},
        {"type": "line", "x1": 0, "y1": 0, "x2": 50, "y2": 50}])
    line = mixed["data"]["objects"][2]["widgetData"]["json"]
    assert line["primary"]["widgetIndex"] == 0 and line["secondary"]["widgetIndex"] == 1
    assert line["line"]["captions"][0]["text"] == "<p>leads to</p>"
    assert json.loads(line["style"])["lc"] == 0xA100FF
    free = mixed["data"]["objects"][3]["widgetData"]["json"]
    assert free["primary"]["widgetIndex"] == -1

    part = compose.subset(TEMPLATE, [1, 0, 2, 3])
    compose.validate(part)
    assert part["data"]["objects"][2]["widgetData"]["json"]["primary"]["widgetIndex"] == 0
    assert part["data"]["objects"][3]["items"] == [1, 0, 2]

    for bad, message in [([{"type": "line", "from": 0, "to": 0}], "line before targets"),
                         ([{"type": "frame", "x": 0, "y": 0}], "missing template type")]:
        try:
            compose.compose_mixed(TEMPLATE, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(message)

    with tempfile.TemporaryDirectory() as folder:
        out = Path(folder) / "out.json"
        compose.write_capture(html_text, mixed, out)
        capture = json.loads(out.read_text())
        written = base64.b64decode(capture["items"][0]["representations"][0]["data"]).decode()
        assert compose.decode_miro_json(written) == mixed
    print("selftest passed: encoding, colors, text escaping, composition, connectors, subset")


if __name__ == "__main__":
    main()
