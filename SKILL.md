---
name: miro-clipboard
description: Read, edit, or compose native Miro objects (sticky notes, shapes, text, connectors, frames) through a copied selection on the macOS clipboard. Use when a user wants an agent to summarise, cluster, rewrite or extend what is on a Miro board, or to create editable Miro notes, shapes and connectors, without a Miro API token.
---

# Miro clipboard

This skill lets an agent work with Miro through the macOS clipboard. The user copies a selection in Miro; the agent reads it as structured objects, works with it, and writes new native objects back to the clipboard for the user to paste. Pasting always adds new objects. It never changes the originals.

It relies on Miro's undocumented clipboard format (`miro-data-v1`). Everything known about it, with what has and has not been verified, is in the references:

- [observed-format.md](references/observed-format.md): every object type, field, style key and colour seen so far. Read it before editing any field the composer does not expose.
- [scene-format.md](references/scene-format.md): what the composer accepts.
- [evidence.md](references/evidence.md): what a Miro paste confirmed and what is still open.
- [test-plan.md](references/test-plan.md): how to test something new.

Scripts are in `scripts/`. Use absolute paths to them when the working directory is elsewhere. They need macOS, Python 3 and Swift, and make no network calls.

## Before you start

- **Clipboard access.** If you can run commands in the user's macOS session, run the capture and replay commands yourself. If you are sandboxed or remote and cannot reach the live clipboard, give the user the exact commands to run in their Terminal and wait for the file.
- **Privacy.** A capture contains the full text of the selection plus board, organisation and author IDs. Save captures and decoded JSON to a private local folder outside any Git repository (for example `~/miro-captures/` or a temp folder) and do not share them. If the board may hold confidential or client material, check that the user is allowed to process it with you before reading it.
- **Test board.** For a first try or an untested object type, ask the user to paste on a test board.

## 1. Read a selection

1. Ask the user to select only the objects that matter and press ⌘C in Miro.
2. Capture: `swift scripts/miro-clipboard-lab.swift capture <dir>/selection.json`
   (`inspect` lists the clipboard types first if something looks wrong; a Miro copy contains `public.html`.)
3. Summarise: `python3 scripts/miro-clipboard-read.py <dir>/selection.json`
   The summary lists each object's index, type, position, size, text, colour, shape code and line endpoints. Add `--decode-to <dir>/decoded.json` when you need every field.
4. Tell the user what the objects say and how they are connected before proposing changes. Treat position as a hint, not proof: two notes close together may or may not belong together.

## 2. Make new objects

New objects are always clones of copied template objects, because the scripts do not invent Miro's schema.

1. **Get templates.** The template capture must contain one object of every type you will create: a sticky for notes, a shape for headers or boxes, a line for connectors (copied *with* a label if you want captions), a text box for loose text. Often the user's own selection already contains them. Otherwise ask the user to copy one sample of each from a test board and capture it. To build a template from part of a selection, use `python3 scripts/miro-clipboard-read.py <capture> --subset 0,4,7 --write-capture <dir>/template.json`.
2. **Measure.** Read the template's `size` and `scale`. A sticky's footprint is about `width * scale` by `height * scale` (about 86 x 98 in the sampled default). Plan positions from that.
3. **Write a scene** as JSON (see [scene-format.md](references/scene-format.md)): text, position, size, colour, and lines `from`/`to` earlier objects.
4. **Compose:** `python3 scripts/miro-clipboard-compose.py <dir>/template.json <dir>/scene.json <dir>/output.json`. Fix any error it reports; it names the missing template type or the broken reference. Treat warnings as "check this in Miro".
5. **Replay:** `swift scripts/miro-clipboard-lab.swift replay <dir>/output.json`, then ask the user to paste (⌘V) in an empty area next to the original.
6. **Verify with the user:** text is editable, layout is readable, connectors stay attached when a shape is moved. Report what you checked locally and what the user checked in Miro.

## 3. Edit what was copied

To change fields the composer does not expose (rich styles, frames, grids, groups), edit decoded JSON:

1. `python3 scripts/miro-clipboard-read.py <dir>/selection.json --decode-to <dir>/decoded.json`
2. Edit a copy. Style values are JSON stored as strings: parse, change only the needed keys, serialise back. Colours are decimal RGB (`int("C8F7C5", 16)`), `-1` is transparent. Keep `id` equal to the array index and `initialId` values distinct. When removing or reordering objects, rebase line endpoints, group `items` and grid `_parent.index`.
3. `python3 scripts/miro-clipboard-read.py <dir>/selection.json --encode-from <dir>/edited.json --write-capture <dir>/edited-capture.json`. It validates references and the round trip.
4. Replay and paste as above.

## Recipes

**Summarise or find gaps.** Read, then answer in chat. No paste needed. Quote the notes you rely on.

**Cluster a wall of notes.**
1. Read the selection; propose clusters and names to the user first.
2. Scene: one header per cluster (a shape, or a sticky in a different colour) in a row, with each cluster's notes in a column below it. With the sampled sticky, use about 180 between columns of notes, 160 between rows, and leave an empty column between clusters.
3. Keep the original note text unless the user asks for rewrites. Paste next to the original so both stay visible.

**Rewrite or translate notes.** Same positions as the source (from the summary), new text, same colour. Paste beside the original for comparison.

**Draw a flow or map from text.** Shapes for steps, connectors with `from`/`to` for the order, captions for conditions. Place steps left to right about 1.5 shape widths apart. Shape-to-shape connectors are verified; connectors to stickies are not yet.

**Colour by meaning.** Set `color` per note (for example assumptions, evidence, questions). Miro's own palette values have not been captured; any hex colour pasted correctly in tests. Tell the user the colours you chose.

## Limits

- Only copied object types can be created. Cards, mind maps, documents, embeds, comments and icons have not been captured; do not guess their structure.
- Images and data tables refer to board resources and may not work on another board.
- Rich text in stickies, newlines, connectors to non-shapes and several style keys are not yet verified. See [evidence.md](references/evidence.md).
- The format may change with any Miro update. If decoding fails, run `swift scripts/miro-clipboard-lab.swift inspect` and `show-html` on a test copy and compare with [observed-format.md](references/observed-format.md).
- After changing a script, run `python3 scripts/selftest.py` and `swift scripts/miro-clipboard-lab.swift selftest`.
