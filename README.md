# Miro clipboard skill

A local-agent skill that bridges tools and Miro through the macOS clipboard. Any local LLM or script with file and clipboard access can interpret a copied selection, restructure it, and write editable notes, shapes, text, and connectors back to the clipboard for paste in Miro. It uses the observed `miro-data-v1` format. Miro does not document this format, so behavior may change.

Copy this repository into the skills directory of an agent that supports `SKILL.md` (for example, Codex), or call the scripts directly from any local tool. The skill name is `miro-clipboard`. Python 3 and macOS Swift/AppKit are required. No Miro API token or external package is needed.

The user copies a selection in Miro and captures it locally with `scripts/miro-clipboard-lab.swift`. A local agent can summarize or edit the selected objects, or compose new objects from copied samples. The output capture is replayed to the clipboard and pasted in Miro. Paste creates a new copy rather than changing existing board objects.

```sh
swift scripts/miro-clipboard-lab.swift capture /path/selection.capture.json
python3 scripts/miro-clipboard-read.py /path/selection.capture.json
python3 scripts/miro-clipboard-compose.py /path/selection.capture.json examples/notes.json /path/new-notes.capture.json
swift scripts/miro-clipboard-lab.swift replay /path/new-notes.capture.json
```

The template for `examples/notes.json` must contain exactly one copied sticky note. Use a disposable Miro board with invented content for initial experiments. A capture includes complete selected text and Miro identifiers; keep it local and out of Git.

The skill instructions are in [SKILL.md](SKILL.md). [Scene format](references/scene-format.md) documents the supported composer fields, and [observed format](references/observed-format.md) describes the clipboard structure and current limits.
