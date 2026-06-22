---
id: STORY-02
epic: EPIC-16
title: Apply the fix and validate network reliability on hardware
status: todo
---

## Goal

Low, consistent RTT to the Pico and a drop-free MIDI Maze match, by applying the
fix identified in STORY-01.

## Tasks

- [ ] Apply the fix indicated by STORY-01. Likely candidates, depending on the
      measured cause:
      - **Power-save:** force Wi-Fi PM off in firmware (correct/override
        `PARAM_WIFI_POWER` handling at `network.c:458-484`) so a stale config can't
        leave the radio asleep.
      - **Poll starvation:** service `cyw43_arch_poll()` unconditionally each hot
        iteration (decouple it from the 1 ms `NET_POLL_MS` gate), and/or move the
        blocking work (`term_loop()` render, reconnect/DNS) out of the poll path so
        the network stack is never starved (`emul.c:628-634`).
      - **Buffer pressure:** raise the relevant lwIP limits in `lwipopts.h`
        (`MEM_SIZE`, `PBUF_POOL_SIZE`, `TCP_WND`/`TCP_SND_BUF`) within the RAM budget.
- [ ] Re-measure: ping ≥ 60 s idle and in-match. Target avg < ~30 ms, max well
      under 100 ms, 0% packet loss.
- [ ] Confirm no MIDI Maze regression on real hardware: byte-exact ring, master
      election / COUNT-PLAYERS, and reconnect recovery still work.
- [ ] Update `CHANGELOG.md`.

## Acceptance

A sustained ping shows tight, consistent RTT with no request timeouts, and a full
MIDI Maze match runs without drops on hardware.

## Notes

- Keep the change surgical (per CLAUDE.md): every changed line should trace to the
  root cause from STORY-01. Don't co-fix unrelated hypotheses unless STORY-01
  implicated them.
- If `cyw43_arch_poll()` is moved to run every iteration, watch the original
  rationale in `emul.c:37-40` (polling cyw43 every spin "would saturate the SPI")
  — measure SPI/throughput impact rather than assuming.
</content>
