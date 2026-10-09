#!/usr/bin/env python3
"""Local checks for the Python tools. Uses a synthetic template; needs no Miro and no clipboard."""

import base64
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
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
    obj(4, "frame", text="Frame", x=0, y=0, width=100, height=100, size={"width": 100, "height": 100},
        style=json.dumps({"fs": 14, "bc": 16777215})),
    obj(5, "paint", points=[{"x": 0, "y": 0}, {"x": 10, "y": 10}], style=json.dumps({"lc": 16686925, "t": 4})),
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

    def expect_error(specs, text):
        try:
            compose.compose_mixed(TEMPLATE, specs)
        except ValueError as error:
            assert text in str(error), (text, str(error))
        else:
            raise AssertionError(f"expected an error containing {text!r}")

    with contextlib.redirect_stderr(io.StringIO()) as warnings:
        mixed = compose.compose_mixed(TEMPLATE, [
            {"type": "shape", "x": 0, "y": 0, "text": "S", "fill": "#D8E8FF", "radius": 8},
            {"type": "sticky", "x": 300, "y": 0, "text": "N", "color": "#FFC0CB"},
            {"type": "line", "from": 0, "to": 1, "caption": "leads to", "color": "#A100FF"},
            {"type": "line", "x1": 0, "y1": 0, "x2": 50, "y2": 50},
            {"type": "shape", "x": 0, "y": 200, "text": "Paid?", "shape": "diamond"},
            {"type": "line", "from": 0, "to": 4, "from_side": "bottom", "to_side": "top"},
            {"type": "line", "from": 0, "to": 4, "arrow": "none"}])
    assert warnings.getvalue().count("warning:") == 0, warnings.getvalue()
    objects = mixed["data"]["objects"]
    assert objects[1]["widgetData"]["type"] == "sticker", "alias sticky -> sticker"
    line = objects[2]["widgetData"]["json"]
    assert line["primary"]["widgetIndex"] == 0 and line["secondary"]["widgetIndex"] == 1
    assert line["line"]["captions"][0]["text"] == "<p>leads to</p>"
    assert json.loads(line["style"])["lc"] == 0xA100FF
    free = objects[3]["widgetData"]["json"]
    assert free["primary"]["widgetIndex"] == -1
    assert free["line"]["captions"] == [], "template label not copied onto an unlabelled line"
    diamond = objects[4]["widgetData"]["json"]
    assert diamond["shape"] == "8" and json.loads(diamond["style"])["st"] == 8
    sided = objects[5]["widgetData"]["json"]
    assert sided["primary"]["point"] == {"x": 0.5, "y": 1} and sided["secondary"]["point"] == {"x": 0.5, "y": 0}
    assert json.loads(sided["style"])["a_start"] == 0 and json.loads(sided["style"])["a_end"] == 9
    plain = json.loads(objects[6]["widgetData"]["json"]["style"])
    assert plain["a_start"] == 0 and plain["a_end"] == 0

    moved = compose.compose_mixed(TEMPLATE, [{"type": "sticker", "template_index": 0, "x": 5, "y": 5}])
    assert moved["data"]["objects"][0]["widgetData"]["json"]["text"] == "<p>A</p>", "template_index keeps text"

    expect_error([{"type": "sticker", "x": 0, "y": 0, "text": "x", "fill": "#FFFFFF"}], "use 'color'")
    expect_error([{"type": "sticker", "x": 0, "y": 0, "text": "x", "colour": "#FFFFFF"}], "unknown field")
    expect_error([{"type": "sticker", "x": 0, "y": 0}], "needs 'text'")
    expect_error([{"type": "image", "x": 0, "y": 0}], "cannot be composed")
    drawn = compose.compose_mixed(TEMPLATE, [{"type": "paint", "path": [[100, 50], [140, 90], [120, 150]],
                                              "color": "#1A1A1A", "thickness": 2}])
    stroke = drawn["data"]["objects"][0]["widgetData"]["json"]
    assert stroke["_position"]["offsetPx"] == {"x": 120, "y": 100}, stroke["_position"]
    assert stroke["points"][0] == {"x": 0, "y": 0} and stroke["points"][2] == {"x": 20, "y": 100}
    assert json.loads(stroke["style"])["lc"] == 0x1A1A1A and json.loads(stroke["style"])["t"] == 2
    expect_error([{"type": "paint", "path": [[0, 0], [1, 1]], "x": 0, "y": 0}], "either 'path'")
    expect_error([{"type": "shape", "x": 0, "y": 0, "text": "a"},
                  {"type": "frame", "x": 0, "y": 0, "width": 10, "height": 10, "contains": [0]}], "before its contents")
    expect_error([{"type": "shape", "x": 0, "y": 0, "text": "a"}, {"type": "group", "items": [0, 5]}], "earlier")

    board = compose.compose_mixed(TEMPLATE, [
        {"type": "frame", "x": 500, "y": 400, "width": 1000, "height": 800, "text": "Synthesis", "contains": "all"},
        {"type": "sticker", "x": 200, "y": 200, "text": "a", "font_size": 24},
        {"type": "sticker", "x": 500, "y": 200, "text": "b"},
        {"type": "line", "from": 1, "to": 2},
        {"type": "group", "items": [1, 2]}])
    objs = board["data"]["objects"]
    frame = objs[0]["widgetData"]["json"]
    assert frame["text"] == "Synthesis" and frame["width"] == 1000 and frame["size"]["height"] == 800
    child = objs[1]["widgetData"]["json"]
    assert child["_parent"] == {"index": 0}
    assert child["_position"] == {"offsetPx": {"x": 200, "y": 200}, "schema": "parentOffsetPx",
                                  "containerType": "FRAME"}, child["_position"]
    assert objs[3]["widgetData"]["json"]["_parent"] == {"index": 0}, "lines join the frame"
    assert objs[4]["type"] == 10 and objs[4]["items"] == [1, 2] and "_parent" not in objs[4]
    assert json.loads(child["style"])["fs"] == 24 and json.loads(child["style"])["fsa"] == 0
    assert json.loads(objs[2]["widgetData"]["json"]["style"])["fsa"] == 1, "default stays automatic"
    expect_error([{"x": 0, "y": 0}], "needs a 'type'")
    expect_error([{"type": "sticker", "template_index": 99, "x": 0, "y": 0}], "template_index")
    expect_error([{"type": "sticker", "template_index": -1, "x": 0, "y": 0}], "template_index")
    expect_error([{"type": "sticker", "template_index": 1, "x": 0, "y": 0}], "not a sticker")
    expect_error([{"type": "line", "from": "0", "to": 1}], "earlier objects")
    expect_error([{"type": "line", "from": 0, "to": 0}], "earlier objects")

    merged = compose.merge_templates(TEMPLATE, TEMPLATE)
    assert len(merged["data"]["objects"]) == 11, "group record is not merged"
    assert merged["data"]["objects"][8]["widgetData"]["json"]["primary"]["widgetIndex"] == -1, "merged line detached"
    joined = compose.compose_mixed(merged, [{"type": "shape", "template_index": 7, "x": 0, "y": 0, "text": "S"},
                                            {"type": "shape", "template_index": 1, "x": 200, "y": 0, "text": "T"},
                                            {"type": "line", "template_index": 8, "from": 0, "to": 1}])
    assert joined["data"]["objects"][2]["widgetData"]["json"]["secondary"]["widgetIndex"] == 1

    part = compose.subset(TEMPLATE, [1, 0, 2, 3])
    compose.validate(part)
    assert part["data"]["objects"][2]["widgetData"]["json"]["primary"]["widgetIndex"] == 0
    assert part["data"]["objects"][3]["items"] == [1, 0, 2]
    for bad in ([0, 0], [0, 9]):
        try:
            compose.subset(TEMPLATE, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"subset {bad} should fail")

    with tempfile.TemporaryDirectory() as folder:
        folder = Path(folder)
        out = folder / "out.json"
        compose.write_capture(html_text, mixed, out)
        capture = json.loads(out.read_text())
        written = base64.b64decode(capture["items"][0]["representations"][0]["data"]).decode()
        assert compose.decode_miro_json(written) == mixed

        # Reader command line: summary, subset, decode and encode.
        template_capture = folder / "template.json"
        compose.write_capture(html_text, TEMPLATE, template_capture)
        reader = [sys.executable, str(HERE / "miro-clipboard-read.py")]
        run = lambda *args: subprocess.run(reader + [str(a) for a in args], capture_output=True, text=True)
        result = run(template_capture, "--compact")
        assert result.returncode == 0 and '"caption":"x"' in result.stdout and "#FFF79E" in result.stdout, result.stderr
        assert run(template_capture, "--subset", "0,1,2,3", "--write-capture", folder / "sub.json").returncode == 0
        framed = folder / "framed.json"
        compose.write_capture(html_text, board, framed)
        assert run(framed, "--check").returncode == 0, run(framed, "--check").stdout
        crowded = compose.compose_mixed(TEMPLATE, [{"type": "sticker", "x": 0, "y": 0, "text": "a"},
                                                   {"type": "sticker", "x": 10, "y": 10, "text": "b"}])
        compose.write_capture(html_text, crowded, folder / "crowded.json")
        result = run(folder / "crowded.json", "--check", "--against", template_capture)
        assert result.returncode == 1 and "overlap" in result.stdout and "missing from output" in result.stdout, result.stdout
        composer = [sys.executable, str(HERE / "miro-clipboard-compose.py")]
        listing = subprocess.run(composer + [str(template_capture), "--show-templates"], capture_output=True, text=True)
        assert listing.returncode == 0 and "label=x" in listing.stdout and "color=#FFF79E" in listing.stdout, listing
        assert run(template_capture, "--subset", "0,0", "--write-capture", folder / "bad.json").returncode != 0
        assert run(template_capture, "--decode-to", folder / "decoded.json").returncode == 0
        decoded = json.loads((folder / "decoded.json").read_text())
        decoded["data"]["objects"][1]["initialId"] = decoded["data"]["objects"][0]["initialId"]
        (folder / "edited.json").write_text(json.dumps(decoded))
        result = run(template_capture, "--encode-from", folder / "edited.json", "--write-capture", folder / "e.json")
        assert result.returncode != 0 and "initialId" in result.stderr, "duplicate initialId rejected"
    print("selftest passed: encoding, colours, text, shapes, connectors, labels, arrows, frames, groups, font size, field checks, subset, reader")


if __name__ == "__main__":
    main()
