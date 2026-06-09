---
id: STORY-05
epic: EPIC-01
title: Automated MIDI hook validation harness
status: todo
milestone: alpha-mvp
---

## Goal

Validate STORY-01..04 automatically: a cartridge-resident m68k self-test routine,
run at boot, exercises the hooked MIDI calls (send + receive) and self-checks the
result, with a machine-readable verdict the RP reports over the serial debug
console — no human reading the ST screen.

The m68k can't be driven from the RP (BIOS/XBIOS calls run on the ST CPU), so the
ST acts as the *exerciser* and the RP as the *oracle*. The exerciser lives in the
cartridge itself (no standalone `.PRG`/`AUTO` program needed) — `main.s` already
runs cartridge code at boot after GEMDOS init, so it can issue the trap calls
directly once the hooks are installed. A test-only RP loopback closes the round
trip so EPIC-01 can be validated before EPIC-02/03 exist.

## Tasks

- [ ] Add a cartridge-resident self-test module (new `.text` section in `userfw.ld` + mirrored `equ` offset in `main.s` + `Makefile` target, gemdrive.ld-style), gated to a test/debug build
- [ ] Run it at boot once the hooks are installed: send a deterministic pattern via `Midiws` (bulk) and `Bconout` (byte-at-a-time), then read back via `Bconstat`/`Bconin` and compare
- [ ] RP-side loopback mode: echo OUT ring → IN ring in the chandler callback (test-only scaffold; replaced by the real transport in EPIC-02/03)
- [ ] Verdict channel: write pass/fail + sent/received byte counters into a shared-region result slot; RP prints `MIDI-SELFTEST: PASS|FAIL n/m` over serial
- [ ] Automation: a host script resets the ST, reads the serial line, and asserts PASS

## Acceptance

Booting a test build runs the self-test from the cartridge unattended; the serial
console emits `MIDI-SELFTEST: PASS 512/512`, and an injected mismatch yields
`FAIL` with the differing counts. Re-running is deterministic and needs no manual
screen reading. The self-test code is excluded from release builds.

## Notes

- Keep the self-test in its own section so it can be dropped from release builds
  and doesn't eat into the hooking code's share of the 8 KB cartridge budget.
- Reuse one of the 60 indexed 4-byte shared variables (or a small block in
  `APP_FREE`) for the verdict + counters — never hard-code an address in the
  `$FA0000`–`$FAFFFF` window.
- This is the capstone of EPIC-01: a PASS exercises the chained vectors
  (STORY-01), both output hooks (STORY-02/03), and the input hook (STORY-04).
