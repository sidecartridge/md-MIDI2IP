# MIDI-to-IP — Epics, Stories & Tasks

This folder is the tracked backlog for MIDI-to-IP. Unlike other Sidecartridge
microfirmwares, `docs/epics/` **is committed to git** — it is the planning
source of truth alongside the code.

See [`STATUS.md`](STATUS.md) for the live cockpit (generated — don't edit it by
hand).

## Hierarchy

```
docs/epics/
  cockpit.sh                     # regenerates STATUS.md from the files below
  STATUS.md                      # generated dashboard
  templates/                     # copy these when adding new work
    epic.md
    story.md
  EPIC-01-<slug>/
    epic.md                      # the epic
    STORY-01-<slug>.md           # a story (with its tasks inside)
    STORY-02-<slug>.md
  EPIC-02-<slug>/
    ...
```

- **Epic** — a folder `EPIC-NN-<slug>/` with an `epic.md`. A coarse capability.
- **Story** — a file `STORY-NN-<slug>.md` inside an epic folder. A shippable
  slice of that epic.
- **Task** — a GitHub-style checkbox line inside a story: `- [ ]` (open) or
  `- [x]` (done). Tasks have no separate files; the checkboxes drive the
  percentages in the cockpit.

`NN` is zero-padded and only needs to be unique within its parent (epics are
globally numbered; stories restart at 01 inside each epic).

## Status field

Every `epic.md` and story file carries a YAML frontmatter block. The cockpit
reads `id`, `title`, and `status`; percentages come from the task checkboxes,
not from `status`.

```yaml
---
id: STORY-02
epic: EPIC-01
title: Hook XBIOS Midiws for MIDI output
status: in-progress   # todo | in-progress | done | blocked
---
```

Keep `status` honest relative to the checkboxes: `todo` = no tasks done,
`done` = all tasks done, `in-progress` = some, `blocked` = waiting on something
(note why in the body).

An optional `milestone: alpha-mvp` field marks a story as part of the alpha MVP
(see Roadmap below). The cockpit tracks MVP progress separately when present.

## Decisions & constraints

Cross-cutting decisions and non-functional constraints live in
[`DECISIONS.md`](DECISIONS.md) (e.g. target app = MIDI Maze, raw-byte
passthrough, transport choice, latency budget). Stories reference them as
`D-NN` / `C-NN` instead of re-arguing the point. Add a row there when a story
defers or settles a cross-cutting choice.

[`ORCHESTRATOR-CONTRACT.md`](ORCHESTRATOR-CONTRACT.md) specifies the wire format
and ring semantics between the firmware and the network orchestrator. The
orchestrator is built in its own repo; this contract is the shared interface we
iterate on here so EPIC-03 has a stable target.

## Roadmap & sequencing

The epics layer bottom-up; the self-test harness is extended at each layer:

```
EPIC-01 hooks ──▶ EPIC-02 transport ──▶ EPIC-03 network
   (self-test scaffold) ─▶ (real rings) ─▶ (network round-trip)
EPIC-04 config/UI/cleanup  and  EPIC-05 validation span the others.
```

Build order: EPIC-01 → EPIC-02 → EPIC-03. EPIC-04 STORY-01 (config) is needed
early (endpoint must be configurable); STORY-03 (trim) runs **last**, once
"unused" is unambiguous. EPIC-05 STORY-02 (latency tuning) follows a working
path.

### Alpha MVP — MIDI Maze, 2 players over IP

The alpha cut is the minimum to play 2-player MIDI Maze over IP: capture its
MIDI OUT (BIOS `Bconout(3)`) and serve its MIDI IN — both the BIOS
`Bconin`/`Bconstat(3)` poll and the XBIOS `trap #14` readback MIDI Maze does after
each write (D-05) — (EPIC-01), move bytes through the rings (EPIC-02), forward
them to the Python orchestrator and back (EPIC-03 STORY-01/02/03/05), with a
green self-test. Stories in this cut carry `milestone: alpha-mvp`; the
cockpit reports their progress on a dedicated line. Out of the alpha cut: the
XBIOS `Midiws` hook (EPIC-01 STORY-02, unused by MIDI Maze), reconnect polish,
ping, the status UI, latency tuning, and template trimming.

## Adding work

1. New epic: `cp -r templates/epic.md EPIC-NN-<slug>/epic.md` (create the folder),
   fill in the frontmatter and body.
2. New story: copy `templates/story.md` into the epic folder as
   `STORY-NN-<slug>.md`, list its tasks as checkboxes.
3. Regenerate the cockpit and commit both your change and `STATUS.md`:

   ```bash
   ./docs/epics/cockpit.sh
   ```

## Cockpit

`cockpit.sh` scans every `EPIC-*/epic.md` and `EPIC-*/STORY-*.md`, counts the
task checkboxes, and writes `STATUS.md` with per-epic and overall progress bars.
It has no dependencies beyond `bash`, `grep`, and `sed`. Run `./docs/epics/cockpit.sh --stdout`
to preview without writing the file.
