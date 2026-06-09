---
id: STORY-03
epic: EPIC-02
title: RP chandler callback to drain OUT / fill IN
status: todo
milestone: alpha-mvp
---

## Goal

Register an RP-side command callback that, each `chandler_loop` iteration, drains
the OUT ring toward the network and fills the IN ring from the network.

## Tasks

- [ ] Implement `midi_command_cb(protocol, payloadPtr)` and register via `chandler_addCB`
- [ ] Drain OUT ring → hand bytes to the network sender (EPIC-03)
- [ ] Take received bytes → push into IN ring (respect full)
- [ ] Keep the callback non-blocking (poll-mode lwIP; never stall the bus loop)

## Acceptance

With a loopback network peer echoing bytes, data written by the ST returns to
the ST through the rings; the PIO bus loop never stalls (no Atari freezes).

## Notes

Wire it up next to `term_command_cb` in `emul_start()` (`rp/src/emul.c:347`).
The hot loop runs at 225 MHz — keep per-iteration work bounded.
