# Hatari gateway (EPIC-05)

A **software RP2040** for the [Hatari](https://www.hatari-emu.org/) emulator:
bridges Hatari's file-based raw MIDI to the orchestrator (EPIC-04), so MIDI Maze
running in Hatari becomes a virtual player — no hardware needed. **Python 3
standard library only.**

```sh
python3 hatari-gateway/gateway.py [--dir DIR]    # default DIR: /tmp/hatari-midi
```

It creates two FIFOs and prints the exact Hatari command. The `--midi-in` /
`--midi-out` file flags enable MIDI on their own (no separate `--midi` flag):

| Hatari flag | direction | FIFO | the gateway… |
| --- | --- | --- | --- |
| `--midi-out <f>` | Atari MIDI **OUT** → host | `midi_out.fifo` | **reads** |
| `--midi-in <f>` | host → Atari MIDI **IN** | `midi_in.fifo` | **writes** |

So: `hatari --midi-out <dir>/midi_out.fifo --midi-in <dir>/midi_in.fifo <prog>`.

**Run the gateway too** — the FIFOs need a peer on the other end, so start
`gateway.py` alongside Hatari (either order). The gateway opens both ends
non-blocking and tolerates Hatari starting before or after it.

Self-test (FIFO lifecycle): `python3 hatari-gateway/selftest.py` (exit 0 = PASS).

## Status

- **STORY-01:** FIFO lifecycle — create (idempotent), documented Hatari
  invocation, robust open (any start order), cleanup.
- STORY-02 — bridge core (OUT fifo → orchestrator; orchestrator → IN fifo)
- STORY-03 — orchestrator client (connect, reconnect, status)
- STORY-04 — validate: Hatari MIDI Maze joins the ring as a player
