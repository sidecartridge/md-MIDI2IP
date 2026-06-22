---
id: EPIC-16
iteration: 7
title: Network reliability & latency pass
status: in-progress
---

## Goal

The link to the orchestrator is unreliable. An ICMP round-trip to the Pico W
swings wildly — from ~5 ms to ~660 ms — with periodic request timeouts, e.g.:

```
icmp_seq=1   time=561.724 ms
icmp_seq=10  time=7.282 ms
icmp_seq=18  time=5.572 ms
Request timeout for icmp_seq 19
Request timeout for icmp_seq 20
icmp_seq=21  time=658.141 ms
icmp_seq=35  time=4.833 ms
```

That jitter is not a healthy Wi-Fi link; it is the firmware not servicing the
network stack on a steady cadence. This epic makes the RP2040 firmware's network
path answer with low, consistent latency so MIDI Maze plays without drops.

## Scope

- In scope: diagnose the dominant cause of the latency variance **on the RP2040
  firmware path** (the ping targets the Pico itself); confirm/repair the Wi-Fi
  power-management configuration; ensure the lwIP/CYW43 poll loop is serviced
  regularly even while the bus-emulation hot loop runs; validate on hardware with
  a sustained ping and a MIDI Maze match.
- Out of scope: orchestrator/gateway changes (the variance is measured on the
  Pico, not the server); TLS / `wss`; any transport redesign (D-12 is closed).

## Candidate causes (to confirm in STORY-01 before changing behaviour)

The symptom — bounded-but-huge, random RTT with occasional total misses — is
consistent with more than one cause. STORY-01 measures which one dominates; the
fix in STORY-02 follows that evidence rather than guessing.

1. **Wi-Fi power-save (CYW43 PM).** Config-driven via `PARAM_WIFI_POWER`
   (`rp/src/include/gconfig.h:32`). The gconfig default is `"0"`
   (`rp/src/gconfig.c:21`) → `NETWORK_POWER_MGMT_DISABLED` = `0xa11140`
   (`rp/src/include/network.h:49`), applied at `rp/src/network.c:458-484` via
   `cyw43_wifi_pm()`. `0xa11140` decodes to the *no-powersave* PM word, so a unit
   on defaults should have PM off — but a non-default stored value (`1`
   PERFORMANCE / `2` AGGRESSIVE / `3` DEFAULT) puts the radio to sleep between
   beacons and produces exactly this RTT pattern. The affected unit's running
   value must be read, not assumed.

2. **`cyw43_arch_poll()` starvation on Core 0** (the user's "superfast polling"
   hypothesis). The hot loop runs `chandler_loop()` every iteration with no yield
   and gates `network_safePoll()` + `midi_net_poll()` + `term_loop()` behind a
   1 ms timer (`NET_POLL_MS`, `rp/src/emul.c:41`; loop at `rp/src/emul.c:618-684`,
   poll block `628-634`). Networking and the PIO/DMA bus emulation **both run on
   Core 0** (Core 1 is parked outside SELECT handling). Anything that blocks
   inside that 1 ms poll block — display/terminal rendering over I2C
   (`term_loop()`), a flash config write, a reconnect/DNS attempt in
   `midi_net_poll()` — delays the *next* `cyw43_arch_poll()` by tens to hundreds
   of milliseconds, which is precisely a multi-hundred-ms RTT spike followed by a
   recovery to single-digit ms.

3. **lwIP buffer pressure.** `lwipopts.h` is tight: `MEM_SIZE=4096`,
   `PBUF_POOL_SIZE=12`, `TCP_WND`/`TCP_SND_BUF` ≈ 6 KB. Under a MIDI burst this
   can stall allocation and add latency. Lower-probability, but cheap to rule in
   or out while instrumenting.

## Stories

- STORY-01: Instrument and identify the dominant latency source (poll-gap +
  ping under load; confirm the unit's PM setting) — decide the fix on evidence.
- STORY-02: Apply the fix and validate on hardware (sustained ping + a drop-free
  MIDI Maze match).

## Notes

- Hot loop / poll cadence: `rp/src/emul.c:618-684` (poll block `628-634`,
  `NET_POLL_MS` `41`).
- Network poll: `network_safePoll()` → `cyw43_arch_poll()`
  (`rp/src/network.c:497-501`), poll mode `NO_SYS=1` (`rp/src/lwipopts.h`).
- Power management: `rp/src/network.c:458-484`; constants
  `rp/src/include/network.h:49-50`; config default `rp/src/gconfig.c:21`.
- MIDI send is deferred to the poll context (`midi_net_flush_out`,
  `rp/src/midi.c:491-534`); receive is an async lwIP callback driven by
  `cyw43_arch_poll()` (`midi_net_recv_cb`, `rp/src/midi.c:363`).
- Clock: Core 0 @ 225 MHz, `VREG_VOLTAGE_1_10` (`rp/src/include/constants.h:52,55`).
</content>
</invoke>
