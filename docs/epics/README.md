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
  STATUS.md                      # generated dashboard (epics grouped by iteration)
  ITERATIONS.md                  # iteration narrative (goal + outcome per iteration)
  templates/                     # copy these when adding new work
    epic.md
    story.md
  EPIC-01-<slug>/
    epic.md                      # the epic (carries `iteration: N`)
    STORY-01-<slug>.md           # a story (with its tasks inside)
    STORY-02-<slug>.md
  EPIC-02-<slug>/
    ...
```

- **Iteration** — a time-boxed pass with one overarching goal, grouping several
  epics. Each `epic.md` carries an `iteration: N` field; the cockpit groups epics
  under their iteration and [`ITERATIONS.md`](ITERATIONS.md) holds the narrative
  (goal + outcome). A story consciously postponed to a later iteration gets
  `status: deferred`.
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
title: Capture MIDI output (BIOS Bconout, device 3)
status: in-progress   # todo | in-progress | done | blocked | deferred
---
```

Keep `status` honest relative to the checkboxes: `todo` = no tasks done,
`done` = all tasks done, `in-progress` = some, `blocked` = waiting on something
(note why in the body), `deferred` = consciously postponed to a later iteration
(its tasks stay open; the epic's Outcome section says why).

A `done` **epic** may sit below 100% when it contains `deferred` stories — the
epic's productive work for its iteration is complete, and the deferred slice is
explicitly carried forward (see [`ITERATIONS.md`](ITERATIONS.md)).

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
orchestrator lives in this repo (`orchestrator/`, EPIC-04, Python 3 stdlib-only);
this contract is the shared interface between the firmware (EPIC-03) and the
server (EPIC-04).

## Roadmap & sequencing

**Linear flow:** each epic is fully completable before the next begins. The
working loopback moves outward one layer at a time — the observable result (solo
MIDI Maze becomes MASTER) holds at each step; real multiplayer arrives once the
orchestrator (EPIC-04) and a 2nd player (EPIC-05) exist:

```
EPIC-01  hook + LOCAL loopback     (all m68k; echo in the Atari)
   │  done — solo MIDI Maze becomes MASTER
   ▼
EPIC-02  RP byte transport         (echo moves to the RP via the byte pipe)
   │  done — same handshake, data now crosses to the RP
   ▼
EPIC-03  RP network endpoint       (echo becomes a round-trip to the network)
   │  done — MIDI over IP, validated with an echo peer
   ▼
EPIC-04  orchestrator server       (wires players into a ring; in-repo, Python stdlib)
   │
   ▼
EPIC-05  Hatari gateway            (software RP2040 → a virtual player; FIRST real match)

EPIC-06 config/UI/cleanup  and  EPIC-07 validation span the others.
```

Build order: EPIC-01 → EPIC-02 → EPIC-03 → EPIC-04 → EPIC-05 — the first playable
match lands at EPIC-05 (a Hatari player gives the 2nd node, D-09). EPIC-06
STORY-01 (config) is needed once the endpoint must be configurable; STORY-03
(trim) runs **last**. EPIC-07 STORY-01 (latency tuning) follows a working path.

### Alpha MVP — MIDI Maze over IP

The alpha cut plays MIDI Maze across the network. EPIC-01 delivers a self-
contained solo game (local loopback); EPIC-02 routes it through the RP; EPIC-03
connects two players via the Python orchestrator. Stories in this cut carry
`milestone: alpha-mvp`; the cockpit reports their progress on a dedicated line.
Out of the alpha cut: reconnect polish, ping, the status UI, latency tuning, and
template trimming. (MIDI Maze never uses XBIOS `Midiws`/`Iorec`, so neither is
hooked — D-05.)

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
