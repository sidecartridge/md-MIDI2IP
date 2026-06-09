---
id: STORY-04
epic: EPIC-01
title: Serve MIDI input — BIOS Bconin/Bconstat + XBIOS readback (device 3)
status: todo
milestone: alpha-mvp
---

## Goal

Deliver MIDI bytes that arrived from the network to the Atari by serving them
through BIOS `Bconin` (blocking read) and `Bconstat` (status) for device 3.

## Tasks

- [ ] **Bring-up:** disassemble `$341a2`/`$188f0` in the MIDI Maze binary (Steem debugger or Ghidra) to confirm (a) the XBIOS `trap #14` function number behind the readback — working assumption `Iorec(2)`, unconfirmed (D-05) — and (b) whether the readback **blocks** until a byte arrives or **polls once and aborts on negative**. (b) decides whether IP latency just lowers FPS (tolerable) or can freeze/desync the game (C-01); if poll-once, the firmware must make the read block locally until our network byte is ready
- [ ] Feed received bytes into the system MIDI input buffer so every read path sees them (D-05)
- [ ] BIOS path (trap #13): `Bconstat(3)` returns ready (-1) when bytes are available; `Bconin(3)` pops the next byte into D0 (`and.l #$ff,d0`)
- [ ] XBIOS path (trap #14): service MIDI Maze's post-write MIDI-IN readback (via `$188f0`/`$341a2`) so master election/sync sees the returned byte; confirm the exact fn# (likely `Iorec(2)`) on hardware
- [ ] Verify both paths against MIDI Maze: master election (own byte returns) and in-game receive

## Acceptance

Bytes written into the IN ring (by the RP side) are returned in order by
`Bconin`; `Bconstat` correctly reports availability; a MIDI monitor on the ST
shows the injected stream.

## Notes

D-05: MIDI Maze reads input two ways — BIOS `Bconstat(3)`+`Bconin(3)` polling in
the game loop, and an XBIOS `trap #14` MIDI-IN read after **every** write (via
`$188f0`→`$341a2`) used for master election and per-frame sync. Both must return
our network bytes, and the XBIOS readback is essential (un-serviced, MIDI Maze's
send routines hit their error path). Cleanest route: populate the system MIDI
input buffer that both paths read. Confirm the XBIOS readback fn# (likely
`Iorec(2)`) on hardware.
