---
id: STORY-01
epic: EPIC-05
title: FIFO setup + documented Hatari invocation
status: in-progress
milestone: alpha-mvp
---

## Goal

Establish the two named pipes Hatari and the gateway share, and document exactly
how to launch Hatari against them. Stdlib only (`os.mkfifo`).

## Tasks

- [x] `create_fifos()` makes `midi_out.fifo` (Atari OUT) + `midi_in.fifo` (Atari IN) via `os.mkfifo`, idempotently
- [x] `hatari_command()` prints the invocation: `--midi-out <midi_out.fifo>` (Hatari writes Atari-OUT) + `--midi-in <midi_in.fifo>` (Hatari reads Atari-IN) — these enable MIDI on their own (no `--midi` flag)
- [x] `open_fifos()` opens non-blocking (OUT read immediate; IN write retries on ENXIO until Hatari's reader) — no deadlock at startup
- [x] `remove_fifos()` cleans up on exit; open tolerates Hatari starting before or after the gateway (both validated by `selftest.py`)

## Acceptance

Running the gateway creates the FIFOs and prints the exact Hatari command; Hatari
launches against them without either side hanging on open.

## Notes

FIFO open semantics are the tricky part: opening a FIFO read or write blocks until
the other end opens. Decide the open strategy (e.g. non-blocking opens + a small
poll loop) so the gateway and Hatari can start in any order. Reference:
<https://www.hatari-emu.org/doc/manual.html#raw_MIDI_device_file_selection>.
