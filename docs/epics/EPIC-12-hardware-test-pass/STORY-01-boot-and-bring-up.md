---
id: STORY-01
epic: EPIC-12
title: Boot, config and node bring-up (ST via Booster + Hatari via gateway)
status: todo
---

## Goal

Both node types come up cleanly from a cold start and are ready to join a ring: a
physical Atari ST running the Booster-installed firmware, and a Hatari instance bridged
by the gateway.

## Tasks

- [ ] Install MIDI-to-IP from the Booster (Apps tab, Download, Launch) onto the SidecarTridge Multi-device; the app launches without dropping back to the Booster
- [ ] On boot the MIDI-to-IP menu shows the countdown plus Wi-Fi state, local IP, and orchestrator connection status
- [ ] Set the endpoint with `[H]ost` and `[P]ort`; power-cycle the ST and confirm the values persist with no re-entry
- [ ] `[E]xit to GEM` launches the firmware and reaches the GEM desktop; `[X]` returns to the Booster
- [ ] Start the orchestrator (`python3 orchestrator/orchestrator.py`); it binds the game port (5005) and the HTTP status port (8080)
- [ ] Start the Hatari gateway (`python3 hatari-gateway/gateway.py --host <orchestrator-ip>`); it creates `midi_out.fifo` + `midi_in.fifo` and prints the exact Hatari command
- [ ] Launch Hatari with `--midi-out` / `--midi-in` pointed at those FIFOs; the gateway reports the bridge is connected both ways

## Acceptance

A real ST boots the firmware from a Booster install, keeps its endpoint config across a
power cycle, and reaches GEM. A Hatari instance plus the gateway come up against the same
orchestrator. Record the build under test and the orchestrator host here.

## Notes

Booster install flow and the boot-menu keys are documented in the root `README.md`. The
Hatari invocation is printed by `gateway.py`; start the orchestrator first.
