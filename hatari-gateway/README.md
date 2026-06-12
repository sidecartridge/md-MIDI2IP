# Hatari gateway

A software RP2040 for the [Hatari](https://www.hatari-emu.org/) emulator. It bridges
Hatari's file-based raw MIDI to the orchestrator, so MIDI Maze running in Hatari becomes
a virtual player with no hardware needed. Python 3 standard library only.

```sh
python3 hatari-gateway/gateway.py [--dir DIR] [--host H] [--port P]
# default: DIR=/tmp/hatari-midi, orchestrator 127.0.0.1:5005
```

It waits for Hatari to open the FIFOs. Then it connects to the orchestrator and bridges
raw bytes both ways. Start the orchestrator first.

It creates two FIFOs and prints the exact Hatari command. The `--midi-in` / `--midi-out`
file flags enable MIDI on their own (no separate `--midi` flag):

| Hatari flag | direction | FIFO | the gateway |
| --- | --- | --- | --- |
| `--midi-out <f>` | Atari MIDI **OUT** → host | `midi_out.fifo` | reads |
| `--midi-in <f>` | host → Atari MIDI **IN** | `midi_in.fifo` | writes |

So: `hatari --midi-out <dir>/midi_out.fifo --midi-in <dir>/midi_in.fifo <prog>`.

Run the gateway too. The FIFOs need a peer on the other end, so start `gateway.py`
alongside Hatari (either order). The gateway opens both ends non-blocking and tolerates
Hatari starting before or after it.

Self-test (FIFO lifecycle): `python3 hatari-gateway/selftest.py` (exit 0 = PASS).
