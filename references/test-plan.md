# Test plan

Use this when you extend the skill, when Miro changes, or when you need a behaviour that [evidence.md](evidence.md) lists as open. Always test on a disposable board with invented content.

## Run a check

1. Copy the objects you need as templates in Miro and capture them:
   `swift scripts/miro-clipboard-lab.swift capture ~/miro-captures/template.json` (create the folder with `mkdir -m 700 -p ~/miro-captures`)
2. Generate the case with the composer, or by editing decoded JSON (see [observed-format.md](observed-format.md)).
3. Run `python3 scripts/selftest.py` after changing any script. It needs no Miro and no clipboard.
4. Replay and paste: `swift scripts/miro-clipboard-lab.swift replay ~/miro-captures/case.json`, then paste in an empty area.
5. Check appearance **and** behaviour. For a connector, move its endpoint objects. For a group, move it and edit a child. For text, edit it. When it matters, reload the board and check again.
6. Record `pass`, `partial` or `fail` with what actually happened, and update `evidence.md`.

A case passes only when the intended native objects appear **and** the relevant behaviour survives interaction.

## Cases already run

These were generated from captured samples and pasted successfully: Unicode and long sticky text; sticky colour; rectangle, ellipse, diamond and triangle variants; shape fill, border and radius together; shape rotation; two-paragraph text box; connected and free lines; three line styles with a caption; a connector bend point; calculated pen strokes; frame title and size; a 2 x 2 grid; a data-table reference; an image reference; a group of shapes and a connector; 25 stickies in a grid. The replay of a full 34-object selection with HTML only was not reported.

## Open checks, by priority

**First, for everyday use**

- Sticky palette: copy one sticky of every swatch in Miro's colour picker, capture, and record each `sbc` value in `observed-format.md`.
- Connector between two stickies, and between a sticky and a shape. Move both ends.
- Connector sides `top` and `bottom`, and a line without a label cloned from a labelled template (the composer empties `line.captions`).
- Sticky `scale` versus `size`: which one makes a note bigger.
- Newlines in a sticky (two `<p>` paragraphs) and very long text.
- Paste the same generated capture on a second board, and after reloading Miro.

**Then, to make styling reliable**

- Change one style key per capture for shapes (`bc`, `brc`, `brw`, `brr`, `tc`, `fs`, alignment) and compare with a screenshot of the original.
- Line looks: straight, curved, elbow; dashed; thickness; start and end arrows. Map `ls`, `lt`, `t`, `a_start`, `a_end`.
- Sticky size versus `scale` and `relativeScale`.
- Rotation with `rotation` only and `relativeRotation` only.

**Later, as needed**

- Objects inside a frame: copy frame plus child and inspect `_parent`; then generate the relationship and move the frame.
- Group child edits, ungrouping, nested groups.
- Grid rows and columns, merges and cell formatting.
- Images and data tables on another board and account.
- Cards, mind-map nodes and other widgets: capture a sample first; do not infer.

## Thinking workflow checks

The format working is not enough; the result has to help people think.

- Give the agent a messy selection and ask for a summary. Check that it separates what notes say from what their position suggests.
- Ask for one reversible change at a time (relabel, cluster, add a link) and compare it with the original before pasting.
- Check that the pasted layout is readable at normal zoom, with no overlapping notes and room for people to add their own.
