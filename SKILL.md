---
name: miro-clipboard
description: Read, edit, or compose native Miro objects through a copied selection on the macOS clipboard. Use when a user wants editable Miro notes, shapes, or connectors, or wants help restructuring a selection copied from Miro.
---

# Miro clipboard

This skill bridges local tools and Miro through the macOS clipboard. A local agent can read a copied selection as an object graph, restructure its content, and write a new native selection to the clipboard. Pasting adds objects; it does not alter the original selection in place. The observed `miro-data-v1` format is undocumented and may change.

## Read a selection

1. Ask the user to copy only the objects they want to share. The capture contains their text and board identifiers. Use a local path outside a Git repository.
2. Run `swift scripts/miro-clipboard-lab.swift inspect` to check clipboard types. Run `capture /path/selection.json` to save the selection. When the agent has access to the user's live clipboard, run these directly. Otherwise, give the user the exact commands to run in their macOS Terminal and wait for the file.
3. Run `python3 scripts/miro-clipboard-read.py /path/selection.json` for an object summary. Use `--decode-to /path/selection-decoded.json` when relationships, styles, or full text matter.
4. Explain what the copied objects actually say and how they connect before proposing content changes. Treat positions as clues, not proof of semantic meaning.

## Edit or compose

- For an existing selection, keep the capture unchanged. Edit a copy of the decoded JSON, validate its object references, and encode it with `miro-clipboard-read.py --encode-from /path/edited.json --write-capture /path/edited-capture.json`.
- For new notes, shapes, text, paint strokes, or lines, copy a disposable sample of each needed type in Miro. Describe the desired layout in a scene JSON and run `miro-clipboard-compose.py TEMPLATE SCENE OUTPUT`. See [scene format](references/scene-format.md) for supported fields.
- Use real copied objects as templates. The scripts do not invent complete Miro schemas. Image and data-table objects may depend on resources outside the clipboard; treat their portability as unverified.
- Check generated text, coordinates, IDs, and connection indices before replay. Keep derived captures local.

## Paste and verify

Run `swift scripts/miro-clipboard-lab.swift replay /path/edited-capture.json`, then paste in Miro. A local agent with clipboard access can run replay directly; otherwise give the user the replay command. Confirm that the objects are editable and that connected lines stay attached when a shape moves. Use a disposable board for the first test of a new object type or format variant.

Read [observed format](references/observed-format.md) when modifying fields beyond those exposed by the scene composer. Report what was verified locally and what was actually checked in Miro.
