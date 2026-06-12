# MIDI-to-IP

MIDI-to-IP is a microfirmware for the SidecarTridge Multi-device that redirects all the MIDI IN and OUT traffic from an Atari ST computer to a network endpoint, by hooking the BIOS device-3 calls (`Bconstat`/`Bconin`/`Bconout`). It runs on a Raspberry Pi Pico (RP2040) plugged into the Multi-device cartridge slot for Atari ST / STE / MegaST(E) computers.

# ⚠️ ATTENTION! READ THIS FIRST

General build and usage of SidecarTridge Multi-device microfirmware apps is documented in the official [SidecarTridge Multi-device documentation](https://docs.sidecartridge.com/sidecartridge-multidevice/programming/). To avoid inconsistencies and outdated information, we've centralized the shared instructions there. Please refer to the official documentation for the latest guidance.

## 🕹️ What is MIDI Maze (and the MIDI ring)?

**MIDI Maze** is a mid-1980s first-person shooter for the Atari ST — one of the earliest
networked multiplayer FPS games. Up to **16** machines play together by chaining their
**MIDI ports into a ring**: each machine's **MIDI OUT** feeds the next machine's **MIDI
IN**, and the last wraps back to the first. Game data (player positions, shots, the maze
itself) circulates around this ring.

```
Physical MIDI Maze ring — up to 16 machines:

   ST 1 ─▶ ST 2 ─▶ ST 3 ─▶ ... ─▶ ST 16
    ▲                              │
    └──────────────────────────────┘
   each machine's MIDI OUT feeds the next's MIDI IN; the last wraps back to ST 1
```

**MIDI-to-IP recreates that ring over the network.** Instead of MIDI cables between
machines, each node's MIDI is carried over Wi-Fi/TCP to a small **orchestrator** that
relays it around the ring. A node is either a **real Atari ST + SidecarTridge
Multi-device**, or the **Hatari emulator + gateway** — mix them freely, up to 16.

```
MIDI-to-IP — the ring relayed over Wi-Fi/TCP through one orchestrator:

      node ──┐        ┌── node        a "node" is a real Atari ST + SidecarTridge,
             v        v               or the Hatari emulator + gateway
           ┌──────────────┐
           │ orchestrator │           it relays each node's MIDI OUT
           └──────────────┘           into the next node's MIDI IN
             ^        ^                (mix freely — up to 16 in one ring)
      node ──┘        └── node
```

## 📦 Applications in this repository

| App | What it is | Where | How to get it running |
| --- | --- | --- | --- |
| **MIDI-to-IP microfirmware** | The Atari-side firmware (RP2040) that turns the ST's MIDI device into a network bridge | `rp/`, `target/atarist/` | Install from the **Booster** app (below) |
| **Orchestrator** | The server that relays the ring and serves a live ring view | `orchestrator/orchestrator.py` | `python3 orchestrator/orchestrator.py` |
| **Hatari gateway** | Bridges the Hatari emulator's MIDI to the orchestrator, so a software node joins the ring | `hatari-gateway/gateway.py` | `python3 hatari-gateway/gateway.py` |

### Installing the microfirmware (the Booster app)

Like any SidecarTridge microfirmware, you install MIDI-to-IP from the **Booster** — no
manual flashing needed:

1. Launch the **Booster** app on your SidecarTridge Multi-device.
2. Open the Booster web interface.
3. In the **Apps** tab, select **MIDI-to-IP** from the list of available apps.
4. Click **Download** to install it to the microSD card.
5. Select the app and click **Launch** to activate it.

> Developers can instead build and flash the `dist/<uuid>-<version>.uf2` UF2 by hand —
> see the official docs for UF2 flashing — but for players the Booster is the way.

### Running the orchestrator and the Hatari gateway

Both are **Python 3 standard-library** scripts — no install and no dependencies; just
run them with `python3` (see the Usage section for the exact commands).

## ▶️ Usage

You need an **orchestrator** running somewhere on the network, plus one or more **nodes**
(real STs and/or Hatari peers) pointed at it.

### 1 · Start the orchestrator

```sh
python3 orchestrator/orchestrator.py            # binds 0.0.0.0:5005, HTTP status on :8080
# options: --host H --port P --http-port P --inspect --no-http
```

Open `http://<orchestrator-ip>:8080/` for the live **ring view** — each connected node
drawn around the ring with its host/IP and bytes in/out, refreshing every 2 s. `--inspect`
logs the decoded MIDI Maze protocol as it passes; `--no-http` drops the status page (rules
out any status-poll jitter on the lock-step ring).

### 2 · Bring up a real Atari ST node (SidecarTridge Multi-device)

1. Install and launch MIDI-to-IP from the Booster (see above). Make sure Wi-Fi is
   configured (via the Booster / global config — see the official docs).
2. On boot, the MIDI-to-IP menu shows a countdown and the current Wi-Fi / local-IP /
   orchestrator status.
3. Set the endpoint: press **`[H]ost`** for the orchestrator's IP or hostname, and
   **`[P]ort`** for its port (default `5005`). The values are saved to the app config
   and **persist across reboots** — you only need to do this the first time (or
   whenever the orchestrator's address changes); otherwise just launch.
4. Press **`[E]xit to GEM`** to launch the MIDI firmware now — or let the countdown
   finish, it auto-launches. (**`[X] Booster`** returns to the Booster.) The cartridge's
   BIOS device-3 hook is now the ST's MIDI device, bridged to the orchestrator.
5. From GEM, run **MIDI Maze**. It uses the ST's MIDI ports as usual; the firmware
   transparently carries that MIDI to and from the orchestrator over Wi-Fi.

### 3 · Bring up a Hatari node (software peer)

Bridge Hatari's file-based MIDI to the orchestrator with the gateway:

```sh
python3 hatari-gateway/gateway.py --host <orchestrator-ip> --port 5005
# default --dir /tmp/hatari-midi, orchestrator 127.0.0.1:5005
```

The gateway prints the exact Hatari command; run Hatari with the two MIDI FIFOs:

```sh
hatari --midi-out /tmp/hatari-midi/midi_out.fifo \
       --midi-in  /tmp/hatari-midi/midi_in.fifo  <midimaze program or disk>
```

Start the orchestrator first; the gateway and Hatari can start in either order.

### 4 · Play a match

MIDI Maze supports **up to 16 players** in one ring. Connect each participant — any mix
of real **ST + SidecarTridge** nodes and **Hatari + gateway** nodes — to the **same
orchestrator**:

1. Start the orchestrator.
2. Bring up each participant (step 2 or step 3) pointed at the orchestrator's IP.
3. Watch `http://<orchestrator-ip>:8080/` — every node appears on the ring.
4. In MIDI Maze, run master election / count players and start the game; all nodes play
   over IP.

## 🙏 Acknowledgements

- **Jesús Ángel González Gorrado** — his *Trabajo Fin de Grado* is a great piece of work
  reverse-engineering the MIDI Maze protocol. It's what made me realize the MIDI-to-IP
  microfirmware was doable.
  [TAZ-TFG-2022-4616.pdf](https://zaguan.unizar.es/record/146840/files/TAZ-TFG-2022-4616.pdf)

- **Markus Fritze ([@sarnau](https://github.com/sarnau))** — author of MIDI Maze II and an
  expert in MIDI Maze. While I knew about his work and his support for the Atari ST scene,
  I did not use any of it in this project *"intentionally"*. And I say "intentionally"
  because at the end of Iteration 2 I realized that Claude Code had started delivering very
  cool ASCII details about the MIDI Maze map format — and digging into the sources and why
  they use that ASCII format, I figured out that the AI was clearly trained on Markus's
  work. I wish I'd known this repo when I started:
  [AtariST-MIDIMaze-Source](https://github.com/sarnau/AtariST-MIDIMaze-Source) — it
  probably would have saved me a lot of back-and-forth with Claude Code. And tokens!
  Thank you, Markus!

## 📄 License

The source code of the project is licensed under the GNU General Public License v3.0. The full license is accessible in the [LICENSE](LICENSE) file.
