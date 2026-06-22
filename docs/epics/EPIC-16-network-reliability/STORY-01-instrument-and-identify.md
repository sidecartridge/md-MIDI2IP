---
id: STORY-01
epic: EPIC-16
title: Instrument and identify the dominant latency source
status: todo
---

## Goal

Determine, with evidence, *why* the RTT to the Pico W swings 5–660 ms with
timeouts — before changing any behaviour. The fix in STORY-02 is chosen from this
measurement, not guessed, so a wrong change doesn't cost a hardware cycle.

## Tasks

- [ ] Capture a baseline: `ping` the Pico for ≥ 60 s while idle and again during a
      MIDI Maze match. Record min/avg/max/mdev and packet loss for each.
- [ ] Read the affected unit's `WIFI_POWER` config value (boot menu / serial) and
      log the resolved `pmValue` at `rp/src/network.c:483`. Confirm whether PM is
      actually disabled (`0xa11140`) on *this* unit or set to a powersave mode.
- [ ] Confirm `0xa11140` (`NETWORK_POWER_MGMT_DISABLED`, `network.h:49`) is the
      intended no-powersave word for `cyw43_wifi_pm()` (vs the SDK's
      `CYW43_NO_POWERSAVE_MODE`); note any mismatch.
- [ ] Add temporary instrumentation around the poll block (`emul.c:628-634`):
      measure the **max gap between consecutive `cyw43_arch_poll()` calls** and the
      time spent inside `term_loop()` and `midi_net_poll()`. Log the worst-case
      stall over a 60 s window.
- [ ] Correlate ping spikes with poll-gap spikes to attribute the variance:
      power-save (radio asleep) vs poll starvation (Core 0 blocked) vs lwIP buffer
      pressure.
- [ ] Record the conclusion (dominant cause + supporting numbers) in the epic
      Notes, and add a `D-NN` row to `DECISIONS.md` if it settles a cross-cutting
      choice (e.g. "PM is always forced off in firmware").

## Acceptance

A written conclusion naming the dominant cause, backed by the measured poll-gap
and ping numbers, with the STORY-02 fix approach selected on that evidence.

## Notes

- Poll cadence is gated to 1 ms by `NET_POLL_MS` (`emul.c:41`); the hot loop never
  yields between `chandler_loop()` calls, so a long operation inside the 1 ms block
  directly becomes a poll gap.
- Networking and PIO bus emulation share Core 0; Core 1 is parked outside SELECT
  handling — keep that in mind when reading stalls.
- Instrumentation is temporary: revert it (or guard it behind `DEBUG_MODE`) before
  STORY-02 ships.
</content>
