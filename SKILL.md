---
name: miro-clipboard
description: Read, edit, or create native Miro objects (sticky notes, shapes, text, connectors, frames and groups) through a copied selection on the macOS clipboard. Use when a user wants an agent to summarise, cluster, rewrite or extend what is on a Miro board, or to create editable Miro notes, shapes and connectors, without a Miro API token.
---

# Miro clipboard

This skill lets an agent work with Miro through the macOS clipboard. The user copies a selection in Miro; the agent reads it as structured objects, works with it, and writes new native objects back to the clipboard for the user to paste. Pasting always adds new objects. The originals are never changed: to "edit" a note, the user pastes the new version and deletes the old one.

It relies on Miro's undocumented clipboard format (`miro-data-v1`). Everything known about it, and what has and has not been verified, is in the references:

- [observed-format.md](references/observed-format.md): every object type, field, style key and colour seen so far. Read it before editing any field the composer does not expose.
- [scene-format.md](references/scene-format.md): every field the composer accepts.
- [evidence.md](references/evidence.md): what a Miro paste confirmed and what is still open.
- [test-plan.md](references/test-plan.md): how to test something new.

## Before you start

- **Platform.** macOS only, with Python 3.9 or newer and Swift (`xcode-select --install` provides Swift). On Windows or Linux, tell the user the skill does not support it. Do not write a substitute clipboard reader: the clipboard formats differ and nothing else has been tested.
- **Paths.** The scripts are in this skill's `scripts/` folder. Use absolute paths to them (the folder that contains this `SKILL.md`), especially in commands you give the user.
- **Working folder.** Create a private folder outside any Git repository, for example `mkdir -m 700 -p ~/miro-captures`, and put captures, decoded JSON and scenes there.
- **Clipboard access.** If you can run commands in the user's macOS session, run capture and replay yourself. If `capture` says no clipboard items are visible although the user did copy, your process probably cannot reach the clipboard (a sandbox). Then ask to run outside the sandbox, or give the user the exact commands with absolute paths and a folder you can both read. If you share no filesystem with the user at all, stop and explain: do not ask them to paste a capture into the chat, because it contains IDs and the full board text.
- **Privacy.** A capture contains the full text of the selection plus board, organisation and author IDs. Never share captures or decoded JSON. If the board may hold confidential or client material, check that the user is allowed to process it with you before reading it.
- **Test board.** For a first try, or for anything listed as untested, ask the user to paste on a test board.

## 1. Read a selection

1. Ask the user to select only the objects that matter and press ⌘C in Miro. **Wait until they confirm** before capturing.
2. Capture: `swift <skill>/scripts/miro-clipboard-lab.swift capture ~/miro-captures/selection.json`
   It refuses to save anything that is not a Miro copy. If it refuses, ask the user to copy again in Miro.
3. Summarise: `python3 <skill>/scripts/miro-clipboard-read.py ~/miro-captures/selection.json --compact`
   One line per object: index, type, position, size, scale, text, colour, shape code, line endpoints and labels. Add `--decode-to <file>` only when you need every field.
4. Tell the user what the objects say and how they connect before proposing changes. Treat position as a hint, not proof: two notes close together may or may not belong together.

## 2. Make new objects

New objects are always clones of copied template objects; the scripts do not invent Miro's schema.

1. **Get templates.** The template capture needs one object of each kind you will create. Often the user's own selection already contains them. Otherwise ask the user to copy samples on a test board and capture them:
   - notes: one sticky;
   - a flowchart: a rectangle, a diamond (rhombus), and a connector copied *with* a label if you want "yes/no" labels;
   - boxes with text: a shape; loose text: a text box;
   - a frame around the result: any copied frame (groups need no template).

   Pick a specific template object with `template_index`. Templates may come from several captures, even weeks old: add them with `--add-template <other capture>`. See every template object with its index, shape, size, colour and label: `python3 <skill>/scripts/miro-clipboard-compose.py <template> --add-template <other> --show-templates`. To keep only part of a selection as a template: `python3 <skill>/scripts/miro-clipboard-read.py <capture> --subset 0,4,7 --write-capture <dir>/template.json`.
2. **Measure.** Positions are object centres. The summary shows `size` and `scale`; a sticky's footprint is about `width * scale` by `height * scale` (about 86 x 99 in Miro's default). Plan positions from that.
3. **Write a scene** (see [scene-format.md](references/scene-format.md)). Every object needs `x`, `y` and `text`, except clones by `template_index`, which keep their text when you leave `text` out.
4. **Compose:** `python3 <skill>/scripts/miro-clipboard-compose.py <dir>/template.json <dir>/scene.json <dir>/output.json`. On `error:`, fix the scene; the message names the field, the missing template type, or the broken reference. Mention every `warning:` to the user as something to check in Miro.
5. **Check:** `python3 <skill>/scripts/miro-clipboard-read.py <dir>/output.json --check --against <dir>/selection.json` reports overlaps, objects outside their frame, broken references and input notes that went missing. Fix everything except deliberate merges.
6. **Replay:** tell the user this replaces what is on their clipboard, then run `swift <skill>/scripts/miro-clipboard-lab.swift replay <dir>/output.json` and ask them to paste (⌘V) in an empty area next to the original.
7. **Verify with the user:** text is editable, the layout is readable, connectors stay attached when a shape is moved. Report what you checked locally and what the user checked in Miro.

## 3. Edit what was copied

For fields the composer does not expose (grids, images, other styles):

1. `python3 <skill>/scripts/miro-clipboard-read.py <dir>/selection.json --decode-to <dir>/decoded.json`
2. Edit a copy. Style values are JSON stored as strings: parse, change only the needed keys, serialise back. Colours are decimal RGB (`int("C8F7C5", 16)`); `-1` is transparent. Keep `id` equal to the array index and every `initialId` distinct. When removing or reordering objects, rebase line endpoints, group `items` and grid `_parent.index`.
3. `python3 <skill>/scripts/miro-clipboard-read.py <dir>/selection.json --encode-from <dir>/edited.json --write-capture <dir>/edited-capture.json`. It rejects broken references and duplicate IDs and checks the round trip.
4. Replay and paste as above. The user deletes the old objects if they want the new ones to replace them.

## Recipes

**Summarise or find gaps.** Read, then answer in chat. No paste needed. Quote the notes you rely on.

**Cluster or synthesise a wall of notes.**
1. Read the selection (`--compact`). Classify each note by what it says, not by its colour; people colour inconsistently. Look for duplicates, notes outside the board's legend, and off-topic notes. Write your reading down, challenge it note by note, and propose the clusters to the user.
2. Use the selection itself as the template. Move each note by cloning it with its own index, `{"type": "sticker", "template_index": 12, "x": ..., "y": ..., "rotation": 0}`, without `text`: it keeps its exact text, and `rotation: 0` straightens a tilted note. Add `color` only to correct a note's category.
3. Give every note `"font_size": 20` so short and long notes read alike.
4. Add one header per cluster (a shape or a text box). Lay out each cluster as columns of up to five notes under its header, about 180 between columns and 160 between rows for the default sticky, with an empty column between clusters. Put merged duplicates in once and off-topic notes in a "Parked" column.
5. For a legend, make one sticky per colour plus a text box title, then a `group` of them so it moves as one piece.
6. Put everything in a `frame` with `"contains": "all"`, as the first object in the scene, so it all moves together.
7. Run `--check --against` the input, then ask the user to paste next to the original.

**Rewrite or translate notes.** Clone each note by `template_index` at the same position offset to the side, and set the new `text`. The colour is kept.

**Draw a flowchart.** Rectangles for steps, `"shape": "diamond"` for decisions (clone a copied shape; the code switches it), connectors with `from`/`to` in the order of the flow. Use `caption` for "yes"/"no" (the template line must have a label). Lay steps out left to right about 1.6 shape widths apart; send a second branch down with `"from_side": "bottom", "to_side": "top"`. Keep shapes in a row at equal heights.

**Make notes in a colour.** Set `color` to one of Miro's sixteen sticky colours, listed with descriptions in [observed-format.md](references/observed-format.md#miros-sticky-palette): for example light yellow `#FFF79E` (default), orange `#FFB575`, light pink `#FFD2F2`, pink `#FD9AE7`, light blue `#B2D0FE`, blue `#86B4F9`, violet `#B8ACFB`, green `#6AE08D`, light green `#D1F09F`, black `#151515`. Miro turns text white on the black sticky by itself. Tell the user which colours you used.

**Make a sticky bigger.** Set `"scale"` to the template's scale times the factor (twice as big: double it). Do not change `width`/`height`: that makes the sticky rectangular. The new note is a copy; the user deletes the old one.

## Limits

- Only copied object types can be created: stickies, shapes, text, connectors, pen strokes, frames and groups. Cards, mind maps, documents, embeds, comments and icons have not been captured; do not guess their structure. Grids can only be edited through decoded JSON.
- Images and data tables refer to board resources and may not work on another board.
- Untested: connectors to text boxes or frames, rich text, very long text, pasting on a different board or in another organisation. See [evidence.md](references/evidence.md).
- Cloned notes keep the template's author field; Miro may show the original author.
- The format may change with any Miro update. If decoding fails, run `swift <skill>/scripts/miro-clipboard-lab.swift inspect` on a test copy (it prints types and sizes only) and compare with [observed-format.md](references/observed-format.md).
- After changing a script, run `python3 <skill>/scripts/selftest.py` and `swift <skill>/scripts/miro-clipboard-lab.swift selftest`.
