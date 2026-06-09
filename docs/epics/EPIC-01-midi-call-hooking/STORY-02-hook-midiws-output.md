---
id: STORY-02
epic: EPIC-01
title: Hook XBIOS Midiws (MIDI output)
status: todo
---

## Goal

Intercept XBIOS `Midiws` (function 12) — the bulk "write string to MIDI" call —
and copy its byte buffer into the shared-region MIDI OUT ring instead of (or in
addition to) the ACIA.

## Tasks

- [ ] Detect XBIOS function 12 in the trap #14 handler and read its args
- [ ] Copy the buffer bytes into the MIDI OUT ring (see EPIC-02)
- [ ] Route bytes to the MIDI OUT ring only — physical-port passthrough is deferred (D-07)
- [ ] Return correctly so the caller is unaware of the redirection

## Acceptance

A program that sends MIDI via `Midiws` results in the same bytes appearing in
the OUT ring, in order, with no dropped bytes under sustained output.

## Notes

`Midiws(count, ptr)` writes `count+1` bytes. Forward bytes verbatim — no MIDI
parsing (D-02). Flow control is handled in EPIC-02. **Not on the MIDI Maze path**
(it sends via BIOS `Bconout`, D-05), so this hook is for general MIDI-output apps
and sits outside the alpha MVP.
