# Hatari gateway

A software RP2040 for the [Hatari](https://www.hatari-emu.org/) emulator. It bridges
Hatari's file-based raw MIDI to the orchestrator, so MIDI Maze running in Hatari becomes
a virtual player with no hardware needed. Python 3 standard library only.

```sh
python3 hatari-gateway/gateway.py [--dir DIR] [--host H] [--port P]
                                  [--transport tcp|ws] [--room KEY]
# default: DIR=/tmp/hatari-midi, orchestrator 127.0.0.1:5005, transport tcp
```

It waits for Hatari to open the FIFOs. Then it connects to the orchestrator and bridges
raw bytes both ways. Start the orchestrator first.

## Transport and rooms

By default the gateway uses a plain TCP socket. Add `--transport ws` to reach the
orchestrator over WebSocket instead (point `--port` at the orchestrator's WebSocket port,
5006 by default); this traverses HTTP reverse proxies and firewalls that only allow web
ports. Add `--room KEY` (with `--transport ws`) to join a private ring, so this node plays
only with the others that entered the same key; without `--room` it joins the default ring.

```sh
python3 hatari-gateway/gateway.py --host <orchestrator-ip> --port 5006 --transport ws --room DIEGOROOM
```

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
