# MIDI-to-IP

MIDI-to-IP is a microfirmware for the SidecarTridge Multi-device that redirects all the MIDI IN and OUT traffic from an Atari ST computer to a network endpoint, by hooking the BIOS device-3 calls (`Bconstat`/`Bconin`/`Bconout`). It runs on a Raspberry Pi Pico (RP2040) plugged into the Multi-device cartridge slot for Atari ST / STE / MegaST(E) computers.

# ⚠️ ATTENTION! READ THIS FIRST

General build and usage of SidecarTridge Multi-device microfirmware apps is documented in the official [SidecarTridge Multi-device documentation](https://docs.sidecartridge.com/sidecartridge-multidevice/programming/). To avoid inconsistencies and outdated information, we've centralized the shared instructions there. Please refer to the official documentation for the latest guidance.

## 🕹️ What is MIDI Maze (and the MIDI ring)?

**MIDI Maze** is a mid-1980s first-person shooter for the Atari ST, one of the earliest
networked multiplayer FPS games. Up to **16** machines play together by chaining their
**MIDI ports into a ring**: each machine's **MIDI OUT** feeds the next machine's **MIDI
IN**, and the last wraps back to the first. The game data circulates around this ring.

```
Physical MIDI Maze ring, up to 16 machines:

   ST 1 ─▶ ST 2 ─▶ ST 3 ─▶ ... ─▶ ST 16
    ▲                              │
    └──────────────────────────────┘
   each machine's MIDI OUT feeds the next's MIDI IN; the last wraps back to ST 1
```

**MIDI-to-IP recreates that ring over the network.** Instead of MIDI cables between
machines, each node's MIDI is carried over Wi-Fi/TCP to a small **orchestrator** that
relays it around the ring. A node is either a **real Atari ST + SidecarTridge
Multi-device**, or the **Hatari emulator + gateway**. Mix them freely, up to 16.

```
MIDI-to-IP: the ring relayed over Wi-Fi/TCP through one orchestrator.

      node ──┐        ┌── node       A "node" is a real Atari ST + SidecarTridge,
             ▼        ▼              or the Hatari emulator + gateway.
           ┌──────────────┐
           │ orchestrator │          It relays each node's MIDI OUT
           └──────────────┘          into the next node's MIDI IN.
             ▲        ▲              (Mix freely, up to 16 in one ring.)
      node ──┘        └── node
```

## 📦 Applications in this repository

| App | What it is | Where | How to get it running |
| --- | --- | --- | --- |
| **MIDI-to-IP microfirmware** | The Atari-side firmware (RP2040) that turns the ST's MIDI device into a network bridge | `rp/`, `target/atarist/` | Install from the **Booster** app (below) |
| **Orchestrator** | The server that relays the ring and serves a live ring view | `orchestrator/orchestrator.py` | `python3 orchestrator/orchestrator.py` |
| **Hatari gateway** | Bridges the Hatari emulator's MIDI to the orchestrator, so a software node joins the ring | `hatari-gateway/gateway.py` | `python3 hatari-gateway/gateway.py` |

### Installing the microfirmware (the Booster app)

Like any SidecarTridge microfirmware, you install MIDI-to-IP from the **Booster**. No
manual flashing needed:

1. Launch the **Booster** app on your SidecarTridge Multi-device.
2. Open the Booster web interface.
3. In the **Apps** tab, select **MIDI-to-IP** from the list of available apps.
4. Click **Download** to install it to the microSD card.
5. Select the app and click **Launch** to activate it.

> Developers can instead build and flash the `dist/<uuid>-<version>.uf2` UF2 by hand
> (see the official docs for UF2 flashing). For players, the Booster is the way.

### Running the orchestrator and the Hatari gateway

Both are **Python 3 standard-library** scripts: no install, no dependencies. Run them
with `python3` (see the Usage section for the exact commands).

## ▶️ Usage

You need an **orchestrator** running somewhere on the network, plus one or more **nodes**
(real STs and/or Hatari peers) pointed at it.

### 1 · Start the orchestrator

```sh
python3 orchestrator/orchestrator.py            # TCP game on 0.0.0.0:5005, HTTP status on :8080
# common options:
#   --ws [--ws-port 5006]   also accept WebSocket nodes (see "WebSocket transport")
#   --admin-key <key>       enable the rooms REST API (see "Private rooms")
#   --rooms-file <path>     persist provisioned rooms across restarts
#   --host H  --port P  --http-port P  --inspect  --no-http
```

Open `http://<orchestrator-ip>:8080/` for the live **ring view**: each connected node is
drawn around the ring with its host/IP, transport, and bytes in/out, refreshing every 2 s.
A room dropdown picks which ring to watch, and `/lobby` lists every room. `--inspect` logs
the decoded MIDI Maze protocol as it passes. `--no-http` drops the status page (which rules
out any status-poll jitter on the lock-step ring).

### 2 · Bring up a real Atari ST node (SidecarTridge Multi-device)

1. Install and launch MIDI-to-IP from the Booster (see above). Make sure Wi-Fi is
   configured (via the Booster / global config; see the official docs).
2. On boot, the MIDI-to-IP menu shows a countdown and the current Wi-Fi / local-IP /
   orchestrator status.
3. Set the endpoint: press **`[H]ost`** for the orchestrator's IP or hostname, and
   **`[P]ort`** for its port (default `5005`). The values are saved to the app config
   and **persist across reboots**. You only need to do this the first time, or whenever
   the orchestrator's address changes; otherwise just launch.
   - **`[T]ransport`** cycles `tcp` / `ws` (see [WebSocket transport](#-websocket-transport)).
     `[P]ort` edits the port for the selected transport.
   - **`[R]oom`** sets a play-room key to join a private ring (see
     [Private rooms](#-private-rooms-play-rooms)); leave it empty for the default ring.
4. Press **`[E]xit to GEM`** to launch the MIDI firmware now, or let the countdown finish
   and it auto-launches. (**`[X] Booster`** returns to the Booster.) The cartridge's BIOS
   device-3 hook is now the ST's MIDI device, bridged to the orchestrator.
5. From GEM, run **MIDI Maze**. It uses the ST's MIDI ports as usual; the firmware
   transparently carries that MIDI to and from the orchestrator over Wi-Fi.

### 3 · Bring up a Hatari node (software peer)

Bridge Hatari's file-based MIDI to the orchestrator with the gateway:

```sh
python3 hatari-gateway/gateway.py --host <orchestrator-ip> --port 5005
# default --dir /tmp/hatari-midi, orchestrator 127.0.0.1:5005
# WebSocket instead of TCP:  --transport ws --port 5006
# join a private room:       --transport ws --port 5006 --room DIEGOROOM
```

The gateway prints the exact Hatari command. Run Hatari with the two MIDI FIFOs:

```sh
hatari --midi-out /tmp/hatari-midi/midi_out.fifo \
       --midi-in  /tmp/hatari-midi/midi_in.fifo  <midimaze program or disk>
```

Start the orchestrator first; the gateway and Hatari can start in either order.

### 4 · Play a match

MIDI Maze supports **up to 16 players** in one ring. Connect each participant (any mix of
real **ST + SidecarTridge** nodes and **Hatari + gateway** nodes) to the **same
orchestrator**:

1. Start the orchestrator.
2. Bring up each participant (step 2 or step 3) pointed at the orchestrator's IP. To play
   in a private group, give every participant the **same room key** (see
   [Private rooms](#-private-rooms-play-rooms)); otherwise they all share the default ring.
3. Watch `http://<orchestrator-ip>:8080/`: every node appears on the ring (pick the room in
   the dropdown).
4. In MIDI Maze, run master election / count players and start the game. All nodes play
   over IP.

## 🌐 WebSocket transport

By default a node reaches the orchestrator over a plain **TCP** socket (port 5005). A node
can instead use **WebSocket**, which rides a standard HTTP port and an Upgrade handshake,
so it can pass an HTTP reverse proxy (nginx, Cloudflare, a PaaS load balancer) or a
firewall that only allows web ports. The MIDI bytes are identical; WebSocket only wraps the
carrier. TCP and WebSocket nodes share the same ring, so you can mix them.

Enable it on each side:

- **Orchestrator:** add `--ws` (and optionally `--ws-port`, default 5006). Both listeners
  run at once.
  ```sh
  python3 orchestrator/orchestrator.py --ws        # TCP :5005, WebSocket :5006, HTTP :8080
  ```
- **Real Atari ST node:** in the boot menu press **`[T]ransport`** to cycle `tcp` / `ws`.
  Each carrier keeps its own port, so **`[P]ort`** edits the port for the selected
  transport. The choice persists across reboots.
- **Hatari gateway:** add `--transport ws` and point `--port` at the WebSocket port.
  ```sh
  python3 hatari-gateway/gateway.py --host <orchestrator-ip> --port 5006 --transport ws
  ```

No TLS yet: `wss` is not supported on the RP, so the WebSocket carries clear text. For an
exposed deployment, put a TLS-terminating reverse proxy in front and speak `ws` to the
orchestrator on the internal network.

## 🔒 Private rooms (play rooms)

One orchestrator can host **many independent rings** at once. A **room key** is a short
word that selects a private ring: every node that enters the same key plays together,
isolated from the other rooms. A node with no key joins a shared **default room** (the
original single-ring behavior). Rooms ride the WebSocket carrier (the key travels in the
handshake), so a room node uses the `ws` transport.

### Operator: provision the rooms

Start the orchestrator with an admin key, then create rooms over a small REST API on the
HTTP port. A join to a room that was not provisioned is refused, so only the rooms you
create exist.

```sh
python3 orchestrator/orchestrator.py --ws --admin-key secret --rooms-file rooms.json

# create a named room
curl -X POST http://<orchestrator-ip>:8080/rooms -H "X-Admin-Key: secret" -d '{"key":"DIEGOROOM"}'
# or mint a short auto-generated code
curl -X POST http://<orchestrator-ip>:8080/rooms -H "X-Admin-Key: secret"
# list rooms / delete a room
curl http://<orchestrator-ip>:8080/rooms
curl -X DELETE http://<orchestrator-ip>:8080/rooms/DIEGOROOM -H "X-Admin-Key: secret"
```

`--rooms-file` keeps the provisioned rooms across restarts. An empty room is reclaimed
after `--room-ttl` seconds (default 600); the default room is never reclaimed. Each ring
caps at the MIDI Maze limit of 16 players.

### Player: enter the room key

- **Real Atari ST node:** set `[T]ransport` to `ws`, then press **`[R]oom`** and type the
  key (for example `DIEGOROOM`). It persists across reboots; leave it empty for the default
  room.
- **Hatari gateway:** add `--transport ws --room DIEGOROOM`.
  ```sh
  python3 hatari-gateway/gateway.py --host <orchestrator-ip> --port 5006 --transport ws --room DIEGOROOM
  ```

### Watch a room

The ring view at `http://<orchestrator-ip>:8080/` has a room dropdown and highlights the
master node. `http://<orchestrator-ip>:8080/lobby` lists every room with its player count
and game phase, each a link into that room's ring. `http://<orchestrator-ip>:8080/?room=DIEGOROOM`
opens straight into a room.

A room key gates a ring; it is not a password for the traffic. Without TLS it travels in
clear text, so use a reverse proxy for TLS and to guard the admin REST API on an exposed
deployment.

## 🙏 Acknowledgements

- **Jesús Ángel González Gorrado**: his *Trabajo Fin de Grado* is a great piece of work
  reverse-engineering the MIDI Maze protocol. It's what made me realize the MIDI-to-IP
  microfirmware was doable.
  [TAZ-TFG-2022-4616.pdf](https://zaguan.unizar.es/record/146840/files/TAZ-TFG-2022-4616.pdf)

- **Markus Fritze ([@sarnau](https://github.com/sarnau))**: author of MIDI Maze II and an
  expert in MIDI Maze. I knew about his work and his support for the Atari ST scene, but I
  did not use any of it in this project *"intentionally"*. And I say "intentionally"
  because at the end of Iteration 2 I realized that Claude Code had started delivering very
  cool ASCII details about the MIDI Maze map format. Digging into the sources and why they
  use that ASCII format, I figured out that the AI was clearly trained on Markus's work. I
  wish I'd known this repo when I started:
  [AtariST-MIDIMaze-Source](https://github.com/sarnau/AtariST-MIDIMaze-Source). It probably
  would have saved me a lot of back-and-forth with Claude Code. And tokens! Thank you,
  Markus!

## 📄 License

The source code of the project is licensed under the GNU General Public License v3.0. The full license is accessible in the [LICENSE](LICENSE) file.

## Docker deployment

A single Docker image runs the orchestrator (all ports) and serves the
[midi-maze-js](https://github.com/diegoparrilla/midi-maze-js) web app on port 80,
so any server can host MIDI Maze over IP for browsers and hardware nodes alike.
See [`docker/README.md`](docker/README.md). Quick start:

```sh
git submodule update --init
docker build -f docker/Dockerfile -t md-midi2ip .
docker run -d -p 80:80 -p 5005:5005 -p 5006:5006 -p 8080:8080 \
  -v midi2ip-data:/data md-midi2ip
```
