---
id: STORY-01
epic: EPIC-16
title: Instrument and identify the dominant latency source
status: in-progress
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
- [x] Confirm `0xa11140` (`NETWORK_POWER_MGMT_DISABLED`, `network.h:49`) is the
      intended no-powersave word for `cyw43_wifi_pm()` (vs the SDK's
      `CYW43_NO_POWERSAVE_MODE`); note any mismatch.
- [x] Add temporary instrumentation around the poll block (now `emul.c:643-683`):
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

## Findings (in progress)

### Power-management constant — confirmed correct (no bug)

`0xa11140` decodes through `cyw43_pm_value(li_assoc<<20 | li_dtim<<16 |
li_beacon<<12 | (ret_ms/10)<<4 | pm_mode)` (`pico-sdk/.../cyw43.h:627`) as:

| field | value |
| --- | --- |
| `pm_mode` (nibble 0) | `0x0` = `CYW43_NO_POWERSAVE_MODE` |
| `pm2_sleep_ret_ms` | 200 |
| `li_beacon_period` / `li_dtim_period` / `li_assoc` | 1 / 1 / 10 |

So `0xa11140` is bit-for-bit `CYW43_PERFORMANCE_PM` (`0xa11142`) with the mode
nibble forced to `0`. Because `pm_mode = NO_POWERSAVE`, the radio never sleeps and
the listen-interval fields are ignored — it genuinely disables power-save. It is
**not** identical to the SDK's `CYW43_NONE_PM` (`0x10`) but is functionally
equivalent. **Conclusion: the constant is correct.** The gconfig default
`WIFI_POWER="0"` (`rp/src/gconfig.c:21`) resolves to it (`network.c:458-484`), so a
default unit runs with PM off. → If the latency persists on a default unit, PM is
not the cause and poll starvation is the prime suspect. *Still to do on hardware:*
read the affected unit's actual stored `WIFI_POWER` to rule out a non-default
override.

### Instrumentation landed

`rp/src/emul.c` main loop now measures, on a 5 s rolling window (debug build only,
gated behind `_DEBUG`), the worst gap between consecutive poll-block runs and the
worst time spent in `cyw43_arch_poll` / `midi_net_poll` / `term_loop`. Both the
debug and release compile paths were syntax-checked clean (`-Wall -Wextra`).
Optimization is MinSizeRel in both builds, so the debug numbers reflect real
timing; the periodic (not per-poll) report keeps UART cost negligible.

## How to capture on hardware

1. Build a debug image so UART stdio + `DPRINTF` are enabled (release disables both,
   `CMakeLists.txt:187-193`):
   `DEBUG_MODE=1 ./build.sh pico_w debug <APP_UUID>`
2. Flash the resulting UF2 and attach a 3V3 USB-UART to **UART0 (GP0 TX / GP1 RX),
   115200 8N1**.
3. While watching the console, `ping` the Pico for ≥ 60 s, idle and during a MIDI
   Maze match. Each 5 s the firmware prints, e.g.:
   `net-instr[5000ms]: worst gap=NNN us | cyw43=NN midi=NN term=NN us`
4. Interpret:
   - **gap** ≈ 1000 µs healthy. Large gap + small cyw43/midi/term → starvation from
     `chandler_loop()` outside the poll block.
   - Large gap **and** large `term`/`midi` → the poll block itself blocks (display
     render / reconnect / DNS) and that, in turn, widens the next gap.
   - Correlate gap spikes with the ping RTT spikes to name the dominant cause for
     STORY-02. If gaps stay ~1 ms while RTT still spikes, suspect PM (re-check the
     unit's `WIFI_POWER`) or lwIP buffer pressure.

## Notes

- Poll cadence is gated to 1 ms by `NET_POLL_MS` (`emul.c:41`); the hot loop never
  yields between `chandler_loop()` calls, so a long operation inside the 1 ms block
  directly becomes a poll gap.
- Networking and PIO bus emulation share Core 0; Core 1 is parked outside SELECT
  handling — keep that in mind when reading stalls.
- Instrumentation is temporary: revert it (or guard it behind `DEBUG_MODE`) before
  STORY-02 ships.
</content>
