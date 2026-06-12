# MIDI-to-IP

MIDI-to-IP is a microfirmware for the SidecarTridge Multidevice that redirects all the MIDI IN and OUT traffic from an Atari ST computer to a network endpoint, by hooking the BIOS device-3 calls (`Bconstat`/`Bconin`/`Bconout`). It runs as a UF2 image on a Raspberry Pi Pico (RP2040) plugged into the Multi-device cartridge slot for Atari ST / STE / MegaST(E) computers.

# ⚠️ ATTENTION! READ THIS FIRST

General build and usage of SidecarTridge Multi-device microfirmware apps is documented in the official [SidecarTridge Multi-device documentation](https://docs.sidecartridge.com/sidecartridge-multidevice/programming/). To avoid inconsistencies and outdated information, we've centralized the shared instructions there. Please refer to the official documentation for the latest guidance.

## Usage

MIDI-to-IP joins Atari **MIDI Maze** players into one ring over IP. You run a small
**orchestrator** (relays the ring) and one or more **nodes** — a real Atari ST with the
SidecarTridge Multi-device (RP2040 Pico W), and/or the [Hatari](https://www.hatari-emu.org/)
emulator via the gateway.

> Flashing the UF2 and the general Multi-device boot/Wi-Fi setup are covered in the
> [official documentation](https://docs.sidecartridge.com/sidecartridge-multidevice/programming/).
> The steps below are the MIDI-to-IP-specific ones.

### 1 · Start the orchestrator

Python 3 standard library only (no dependencies):

```sh
python3 orchestrator/orchestrator.py            # binds 0.0.0.0:5005, HTTP status on :8080
# options: --host H --port P --http-port P --inspect --no-http
```

Open `http://<orchestrator-ip>:8080/` for the live **ring view** — each connected node
drawn around the ring with its host/IP and bytes in/out, refreshing every 2 s. `--inspect`
logs the decoded MIDI Maze protocol as it passes; `--no-http` drops the status page (rules
out any status-poll jitter on the lock-step ring).

### 2 · A real Atari ST node (SidecarTridge Multi-device / RP2040)

1. Flash the MIDI-to-IP UF2 (`dist/<uuid>-<version>.uf2`) to the **Pico W** and seat the
   board in the Multi-device cartridge slot. Make sure Wi-Fi is configured (via the
   Booster / global config — see the official docs).
2. Power on the ST. The MIDI-to-IP boot menu appears with a countdown and the current
   Wi-Fi / local-IP / orchestrator status.
3. Set the endpoint: press **`[H]ost`** to enter the orchestrator's IP or hostname, and
   **`[P]ort`** to enter its port (default `5005`). The values are saved to the app config.
4. Press **`[E]xit to GEM`** to launch the MIDI firmware now — or let the countdown finish,
   it auto-launches. (**`[X] Booster`** jumps to the Booster instead.) The cartridge's BIOS
   device-3 hook is now the ST's MIDI device, bridged to the orchestrator.
5. From GEM, run **MIDI Maze**. It uses the ST's MIDI ports as usual; the firmware
   transparently carries that MIDI to/from the orchestrator over Wi-Fi.

### 3 · A Hatari node (software peer)

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

### 4 · Play a 2-node match

1. Start the orchestrator.
2. Bring up node A (a real ST, or Hatari + gateway) pointed at the orchestrator's IP.
3. Bring up node B the same way.
4. Watch `http://<orchestrator-ip>:8080/` — both nodes appear on the ring.
5. In MIDI Maze, run master election / count players and start a game — the two nodes
   play over IP.

## Shared 64 KB region layout

A single source-of-truth layout governs the 64 KB shared region (m68k `$FA0000`–`$FAFFFF`, mirrored at RP `0x20030000`):

- The cartridge image (m68k header + code) lives in the first **8 KB** (`$FA0000`–`$FA1FFF`). `target/atarist/build.sh` enforces this with a hard size check on `BOOT.BIN`.
- A small fixed-offset metadata block (`CMD_MAGIC_SENTINEL`, `RANDOM_TOKEN`, `RANDOM_TOKEN_SEED`, 60 × 4-byte indexed shared variables) sits at `$FA2000`.
- The **APP_FREE** arena (~48 KB at `$FA2300`) is the contiguous space your app should use for its own buffers.
- The **framebuffer** (8000 B for 320×200 monochrome) sits at the very top of the region (`$FAE0C0`), so an overrun walks off the end of the 64 KB window instead of corrupting the metadata block.

Both sides derive every offset symbolically from the constants in `rp/src/include/chandler.h` (RP-side) and `target/atarist/src/main.s` (m68k side). Apps must never hard-code an address inside the region — always reference the named offset/symbol so the layout stays the single source of truth.

See `programming.md` for the full table and the budget rules.

## User firmware module

The cartridge image is split via `target/atarist/src/userfw.ld` into two sections:

- `main.s` at offset `0x0000` (`$FA0000`, 2 KB) — boot, dispatch, terminal.
- `userfw.s` at offset `0x0800` (`$FA0800`, 6 KB) — the MIDI-to-IP m68k logic that hooks the BIOS device-3 MIDI calls.

`main.s` exposes the user firmware as `USERFW equ (ROM4_ADDR + $800)`. When the RP-side terminal command `f` (`[F]irmware`) is selected, the RP writes `CMD_START = 4` to the cartridge sentinel; the m68k's vsync-polled `check_commands` dispatches to `rom_function`, which `jmp`s to `USERFW`. (`userfw.s` holds the MIDI-to-IP BIOS device-3 hook — `Bconstat`/`Bconin`/`Bconout` — serviced directly against the RP's network queues.)

Additional m68k modules follow the `gemdrive.ld`-style pattern: place each new `.text` section in `userfw.ld`, mirror the offset with an `equ` in `main.s`, and add the `.o` target to `target/atarist/Makefile`.

## License

The source code of the project is licensed under the GNU General Public License v3.0. The full license is accessible in the [LICENSE](LICENSE) file. 
