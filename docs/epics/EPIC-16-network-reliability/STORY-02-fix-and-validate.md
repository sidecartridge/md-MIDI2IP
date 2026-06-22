---
id: STORY-02
epic: EPIC-16
title: Apply the fix and validate network reliability on hardware
status: in-progress
---

## Goal

Low, consistent RTT to the Pico and a drop-free MIDI Maze match, by applying the
fix identified in STORY-01.

## Tasks

- [x] Apply the fix indicated by STORY-01 (cause = Wi-Fi power-save, D-15): the
      resolved PM value (`staPmValue`) is now re-applied on every link-up in
      `wifiLinkCallback()` (`network.c:605`), because the pre-association
      `cyw43_wifi_pm()` in `network_wifiInit()` (`network.c:484`) does not survive
      the join. Poll starvation and lwIP buffer pressure were ruled out by the
      STORY-01 instrumentation, so neither was touched (surgical, per CLAUDE.md).
- [ ] Re-measure: ping ≥ 60 s idle and in-match. Target avg < ~30 ms, max well
      under 100 ms, 0% packet loss.
- [ ] Confirm no MIDI Maze regression on real hardware: byte-exact ring, master
      election / COUNT-PLAYERS, and reconnect recovery still work.
- [ ] Update `CHANGELOG.md`.

## Acceptance

A sustained ping shows tight, consistent RTT with no request timeouts, and a full
MIDI Maze match runs without drops on hardware.

## Notes

**Validation still required on hardware (re-uses the STORY-01 instrumentation):**

1. Set `WIFI_POWER=0` in the boot menu if it isn't already (default is `0`).
2. Build + flash a debug image: `DEBUG_MODE=1 ./build.sh pico_w debug <APP_UUID>`.
3. `ping` the Pico ≥ 60 s idle and during a match while watching UART0 @ 115200.
   Expected: the `net-instr` worst gap stays ~ms (unchanged — the loop was always
   healthy) while **idle RTT collapses to single-digit ms** with no 100-400 ms
   spikes. Confirm `Setting power management to: 00a11140` and a `WiFi Link: UP`
   line appear in the log.
4. Confirm no MIDI Maze regression (byte-exact ring, master election, reconnect).
5. Once validated, **remove the STORY-01 instrumentation** from `emul.c` before this
   ships.


- Keep the change surgical (per CLAUDE.md): every changed line should trace to the
  root cause from STORY-01. Don't co-fix unrelated hypotheses unless STORY-01
  implicated them.
- If `cyw43_arch_poll()` is moved to run every iteration, watch the original
  rationale in `emul.c:37-40` (polling cyw43 every spin "would saturate the SPI")
  — measure SPI/throughput impact rather than assuming.
</content>
