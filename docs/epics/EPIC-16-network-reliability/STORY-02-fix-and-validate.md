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

- [x] Apply the fix indicated by STORY-01 (cause = Wi-Fi power-save, D-15):
      - **Force PM off unconditionally**, ignoring `PARAM_WIFI_POWER`
        (`network_wifiInit` sets `staPmValue = NETWORK_POWER_MGMT_DISABLED`). The
        affected unit had `WIFI_POWER` set to a power-save mode (logged applied value
        `0xa11142` = `CYW43_PERFORMANCE_PM`); power-save is incompatible with the
        lock-step ring (C-01), so it is no longer selectable.
      - **Apply it after association**: a pre-join `cyw43_wifi_pm()` does not stick.
        `wifiLinkCallback()` flags a re-apply and `network_safePoll()` performs the
        ioctl in main-loop context (calling it from the netif callback re-enters the
        driver inside `cyw43_arch_poll()` and no-ops).
      - **Corrected the disabled constant** `0xa11140 → 0x10` (`CYW43_NONE_PM`); the
        old value carried `li_assoc=10` (~1 s listen interval).
      - Poll starvation and lwIP buffer pressure were ruled out by the STORY-01
        instrumentation (worst gap ~5.3 ms; RSSI -41 dBm ruled out RF), so neither
        was touched (surgical, per CLAUDE.md).
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

1. `WIFI_POWER` is now ignored (PM forced off), so no config change is needed.
2. Build + flash a debug image: `DEBUG_MODE=1 ./build.sh pico_w debug <APP_UUID>`.
3. `ping` the Pico ≥ 60 s idle and during a match while watching UART0 @ 115200.
   Expected: the `net-instr` worst gap stays ~ms (unchanged — the loop was always
   healthy) while **idle RTT collapses to single-digit ms** with no 100-400 ms
   spikes. Confirm the log shows `Setting power management to: 00000010 (forced off...)`
   and `Applying Wi-Fi PM (post-assoc): 00000010` with a `WiFi Link: UP` line.
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
