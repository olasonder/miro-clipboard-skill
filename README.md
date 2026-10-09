# Miro clipboard skill

Let your AI agent work on a Miro board. Copy a few sticky notes, ask Claude Code or Codex to cluster, rewrite or extend them, and paste the result back into Miro as real, editable notes, shapes and connectors.

No Miro API token, no admin approval, no extra packages. Just the macOS clipboard.

## Why I built this

I wanted AI to work with me in Miro. Miro has its own AI features, but they don't have my context, and the Miro MCP is not always available. The clipboard turned out to be the easiest route that needs no extra access. When you copy a selection, Miro puts a full description of those objects on the clipboard. This skill reads that description, lets your agent work with it, and writes new objects back the same way.

I built it in my own time, in September 2026.

## What you can do with it

- **Make sense of a wall of notes.** Copy fifty stickies and ask the agent to summarise, cluster or find the gaps.
- **Restructure.** Get clustered, renamed or rewritten notes back as a new selection you paste next to the original.
- **Draw from text.** Describe a flow or a map, and get shapes connected by lines that stay attached when you move them.
- **Colour by meaning.** Give notes and shapes any colour, for example assumptions in one colour and evidence in another.

Paste always adds a copy. Your original objects are never changed.

## Install

Paste this into Claude Code or Codex:

> Install the skill from https://github.com/olasonder/miro-clipboard-skill

Or install it yourself:

```sh
# Claude Code
git clone https://github.com/olasonder/miro-clipboard-skill ~/.claude/skills/miro-clipboard
# Codex
git clone https://github.com/olasonder/miro-clipboard-skill ~/.codex/skills/miro-clipboard
```

Requirements: macOS, Python 3 and Swift (included with the Xcode Command Line Tools).

## How it works

You copy a selection in Miro and capture it locally with `scripts/miro-clipboard-lab.swift`. A local agent can summarise or edit the selected objects, or compose new objects from copied samples. The output capture is replayed to the clipboard and pasted in Miro.

```sh
swift scripts/miro-clipboard-lab.swift capture /path/selection.capture.json
python3 scripts/miro-clipboard-read.py /path/selection.capture.json
python3 scripts/miro-clipboard-compose.py /path/selection.capture.json examples/notes.json /path/new-notes.capture.json
swift scripts/miro-clipboard-lab.swift replay /path/new-notes.capture.json
```

New objects are clones of copied samples, so the template capture needs one object of each type you create (a sticky for `examples/notes.json`; shapes, a line and a sticky for `examples/flow.json`).

Everything the skill knows is written down:

- [SKILL.md](SKILL.md): the agent's instructions and recipes.
- [Observed format](references/observed-format.md): every object type, field, style key and colour seen so far, and what has been verified.
- [Scene format](references/scene-format.md): what the composer accepts.
- [Evidence](references/evidence.md) and [test plan](references/test-plan.md): what a Miro paste confirmed, what is still open, and how to test more.

`python3 scripts/selftest.py` checks the Python tools without Miro or a clipboard.

## Good to know

- The skill relies on Miro's clipboard format (`miro-data-v1`). Miro does not document it, so it may change without notice.
- A capture contains the full text of what you copied and Miro identifiers. Keep captures local and out of Git; `.gitignore` already excludes them.
- Try it on a test board with invented content first.
- Mind what you copy. The agent sees everything in the selection, so only use it on confidential boards through AI tools your organisation has approved.

## License

MIT. See [LICENSE](LICENSE).
