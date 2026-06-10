---
id: STORY-01
epic: EPIC-05
title: FIFO setup + documented Hatari invocation
status: todo
milestone: alpha-mvp
---

## Goal

Establish the two named pipes Hatari and the gateway share, and document exactly
how to launch Hatari against them. Stdlib only (`os.mkfifo`).

## Tasks

- [ ] Create two FIFOs (e.g. `midi_out.fifo` = Atari OUT, `midi_in.fifo` = Atari IN) via `os.mkfifo`, idempotently
- [ ] Document the Hatari command: `--midi-in <midi_out.fifo>` (Hatari writes Atari-OUT) and `--midi-out <midi_in.fifo>` (Hatari reads Atari-IN) — note the backwards naming
- [ ] Handle the FIFO open/blocking semantics (open order, non-blocking vs blocking) so neither side deadlocks at startup
- [ ] Clean up FIFOs on exit; tolerate Hatari starting before/after the gateway

## Acceptance

Running the gateway creates the FIFOs and prints the exact Hatari command; Hatari
launches against them without either side hanging on open.

## Notes

FIFO open semantics are the tricky part: opening a FIFO read or write blocks until
the other end opens. Decide the open strategy (e.g. non-blocking opens + a small
poll loop) so the gateway and Hatari can start in any order. Reference:
<https://www.hatari-emu.org/doc/manual.html#raw_MIDI_device_file_selection>.
