# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

See also: `programming.md` (full shared-region table and budget rules), `README.md` (user-facing overview of every component), `AGENTS.md` (overlapping playbook + troubleshooting table), `docs/epics/` (the committed backlog, decisions, and iteration history).

## What this repo is

**MIDI-to-IP** turns an Atari ST / STE / MegaST(E) into a network player for **MIDI Maze** by
redirecting all MIDI IN and OUT traffic to a network endpoint. It hooks the BIOS device-3 calls
(`Bconstat` / `Bconin` / `Bconout`, trap #13) so the hook *is* the MIDI device: MIDI Maze does all
its ring I/O through those calls (never XBIOS `Midiws`, never `Iorec`, never the 6850 ACIA
registers). Direct-ACIA software is out of scope by design (D-01: those bus cycles never reach the
cartridge).

The repo holds four deliverables:

| Component | What it is | Where |
| --- | --- | --- |
| **Microfirmware** | A Sidecartridge Multi-device app: m68k cartridge code plus RP2040 firmware, shipped as a UF2 | `target/atarist/`, `rp/` |
| **Orchestrator** | The server that relays the MIDI ring between nodes and serves a live ring view | `orchestrator/orchestrator.py` |
| **Hatari gateway** | Bridges the Hatari emulator's file-FIFO MIDI into the ring, giving a software node | `hatari-gateway/gateway.py` |
| **Docker image** | Orchestrator plus the `midi-maze-js` browser game under one supervisor | `docker/` |

`midi-maze-js` is a git submodule (its own repo, with its own `CLAUDE.md`); only the Docker build
consumes it. Platform build/usage docs live at
<https://docs.sidecartridge.com/sidecartridge-multidevice/programming/>.

Status: `v1.1.1beta` (see `version.txt` and `CHANGELOG.md`). Iterations 1 to 10 are closed; a real
2-player match over IP works on hardware.

## Build

Top-level build is driven by `build.sh` in the repo root:

```bash
# <board_type> = pico | pico_w | sidecartos_16mb
# <build_type> = debug | release   (note: always compiled as MinSizeRel, see below)
# <app_uuid_key> = UUID4 identifying this app, must match desc/app.json
./build.sh pico_w release 123e4567-e89b-12d3-a456-426614174000
```

Required host environment:
- ARM GNU Toolchain 14.2; export `PICO_TOOLCHAIN_PATH` to its `arm-none-eabi/bin` dir.
- `atarist-toolkit-docker` (`stcmd`) for the m68k target. `stcmd` requires a PTY (`pty=true`).
- SDK paths (auto-set from the repo if unset): `PICO_SDK_PATH`, `PICO_EXTRAS_PATH`, `FATFS_SDK_PATH`.

Build flow (orchestrated by `build.sh`):
1. Copies `version.txt` into `rp/` and `target/atarist/`.
2. Builds the Atari ST target (`target/atarist/build.sh`) via `stcmd make`. Enforces an **8 KB hard
   limit** on `BOOT.BIN` (the cartridge code budget: `CHANDLER_CARTRIDGE_CODE_SIZE` in
   `rp/src/include/chandler.h`, mirrored as `CARTRIDGE_CODE_SIZE` in `target/atarist/src/main.s`);
   a build that exceeds it aborts with `ERROR: cartridge code is N bytes; limit is 8192`. A separate
   copy (`FIRMWARE.IMG`) is padded to 64 KB to fill the whole shared region, and `firmware.py`
   converts it into `rp/src/include/target_firmware.h` (a C byte array embedded in the RP firmware).
3. Builds the RP firmware (`rp/build.sh`): pins submodule versions (pico-sdk 2.2.0, pico-extras
   sdk-2.2.0, fatfs-sdk at a specific commit), runs CMake, produces `rp/dist/rp-<board>.uf2`. The
   FatFs configuration lives at `rp/src/ff/ffconf.h` and shadows the submodule's default via
   `target_include_directories(... BEFORE PRIVATE)` in `rp/src/CMakeLists.txt`, so the `fatfs-sdk`
   submodule stays pristine.
4. Computes MD5, renames to `dist/<APP_UUID>-<VERSION>.uf2`, and substitutes UUID/MD5/version into
   `dist/<APP_UUID>.json` from the `desc/app.json` template.

### Build gotchas
- **CMake always builds with `-DCMAKE_BUILD_TYPE=MinSizeRel`** regardless of the `<build_type>`
  argument. A full `Release` previously caused breakage (memory/over-optimization). The legacy line
  is left commented in `rp/build.sh`. `<build_type>` only controls the `DEBUG_MODE` macro and the
  dist filename.
- `CHARACTER_GAP_MS` must remain defined (700) in `rp/src/include/blink.h`; removing it breaks the
  RP build.
- Harmless VASM warnings during the m68k build (`target data type overflow`, `trailing garbage after
  option -D`) can be ignored.
- VASM/`stcmd` errors like `the input device is not a TTY` mean `stcmd` was invoked without a PTY.
  `target/atarist/build.sh` already exports `STCMD_NO_TTY=1` for every `stcmd` call it makes; export
  it yourself only when invoking `stcmd` directly from a non-TTY context (CI, sub-shells, build
  wrappers). Without it the m68k build can fail silently and the previous `BOOT.BIN` survives,
  leading to a working RP firmware that displays garbage on the ST because `target_firmware.h` is
  stale.

## Running the server side

Both Python programs are **Python 3 standard library only** (D-10). No install, no dependencies, and
no third-party packages may be added.

```bash
python3 orchestrator/orchestrator.py                 # TCP ring :5005, HTTP status :8080
python3 orchestrator/orchestrator.py --ws --admin-key secret --rooms-file rooms.json
python3 hatari-gateway/gateway.py --host <ip> --port 5005
python3 tools/echo_peer.py [port]                    # dev echo peer for firmware bring-up

git submodule update --init                          # midi-maze-js, needed by the image
docker build -f docker/Dockerfile -t md-midi2ip .    # build from the repo root
docker/run.sh <ADMIN_KEY>                            # all defaults; NETWORK=host for lowest latency
docker/deploy.sh root@server                         # build locally, install remotely
```

`docker/README.md` documents every env var, the nginx single-port mode (`ws://<host>/ws`,
`http://<host>/rooms` on :80), and the latency tunings.

## Tests

```bash
python3 orchestrator/selftest.py     # exit 0 = PASS
python3 hatari-gateway/selftest.py   # exit 0 = PASS
```

Both spawn what they need (test ports, temp FIFOs, a fake peer) and print per-check PASS/FAIL lines.
The orchestrator self-test covers the ring relay, connection identity, the `--inspect` decoder, and
the RFC 6455 codec in `orchestrator/ws.py`. Keep them passing when touching either program, and add
a phase rather than a new framework.

The firmware itself has no automated tests. Verification there is: the build succeeds, the UF2 boots
on hardware, and behavior is checked over the serial debug console plus the orchestrator's
`--inspect` trace and ring view. `docs/epics/EPIC-12-hardware-test-pass/` holds the manual checklist.

### CI / release
- `.github/workflows/build.yml` builds `pico_w` Release on PR.
- `.github/workflows/release.yml` triggers on `v*` tags: builds, attaches UF2 + JSON to the GitHub
  Release, uploads to `s3://atarist.sidecartridge.com/`.
- `make tag` tags HEAD with the contents of `version.txt` and pushes the tag, which triggers release.
- `upload_s3.sh <file>` is a manual one-off uploader; needs `AWS_ACCESS_KEY_ID` /
  `AWS_SECRET_ACCESS_KEY`.

## Architecture

The firmware is a **two-target build**: m68k assembly that runs on the Atari ST is compiled into a
ROM image, embedded as a C array inside the RP2040 firmware, and served back to the Atari over the
cartridge bus that the RP2040 emulates with PIO + DMA.

### Atari ST side (`target/atarist/`)
- `src/main.s` is the m68k cartridge boot, dispatch, and terminal, living at `$FA0000` in the ST
  address space (ROM4 cartridge region). It defines the cartridge header (`CA_MAGIC`, `CA_INIT`, ...),
  the command magic numbers, and the shared-variable layout used to talk to the RP2040.
- `src/userfw.s` is **the primary extension point for app-specific m68k code**. `src/userfw.ld`
  places `main.s` at offset `0x0000` (2 KB budget) and `userfw.s` at offset `0x0800` (6 KB budget);
  `main.s` exposes the latter as `USERFW equ (ROM4_ADDR + $800)`. It holds the MIDI BIOS device-3
  hook, installed with the XBRA convention.
- **Boot order matters.** `start_rom_code` in `main.s` does a `jsr USERFW` at boot, while `send_sync`
  commands still work, so the hook is installed before the menu ever runs. The later `CMD_START`
  dispatch (`rom_function`) only boots GEM; the fast-path gate is committed RP-side by
  `midi_set_active(true)` inside `cmdFirmware`. Do not move the install back into `rom_function`.
- Adding more m68k modules: add a new `.text_<name>` section in `userfw.ld`, mirror the offset with
  an `equ (ROM4_ADDR + $????)` in `main.s`, and add the `.o` target to `target/atarist/Makefile`
  (same pattern as `gemdrive.ld` in `md-drives-emulator`).

### Shared 64 KB cartridge region
The Atari ST sees a 64 KB window at `$FA0000` to `$FAFFFF`, mirrored RP-side at `0x20030000`. This is
the **single source of truth** for any cross-target data layout: both sides derive every offset
symbolically from constants in `rp/src/include/chandler.h` (RP) and `target/atarist/src/main.s`
(m68k). **Never hard-code an address inside this region**; always reference the named offset/symbol.

| Offset | Symbol | Size | Purpose |
| --- | --- | --- | --- |
| `$FA0000` | cartridge image | 8 KB | m68k header + all `.text_*` sections (hard limit) |
| `$FA2000` | `CMD_MAGIC_SENTINEL` | 4 B | m68k polls here for NOP/RESET/command words |
| `$FA2004` | `RANDOM_TOKEN` | 4 B | chandler echoes the request token |
| `$FA2008` | `RANDOM_TOKEN_SEED` | 4 B | |
| `$FA200C` | reserved | 4 B | framework use; apps must not write here |
| `$FA2010` | `SHARED_VARIABLES` | 240 B | 60 indexed 4-byte slots |
| `$FA2100` | `APP_BUFFERS` | ~48 KB | arena; its first 512 B are the high-res mask table written by `display_setupU8g2()` |
| `$FA2300` | `APP_FREE` | ~48 KB | free arena. MIDI-to-IP puts its IN mailbox at the base |
| `$FAE0C0` | `FRAMEBUFFER` | 8000 B | 320x200 monochrome; sits at the top of the region so an overrun walks off the end of the 64 KB window instead of corrupting the metadata block |

See `programming.md` for the full table and budget rules.

### The MIDI transport (EPIC-09 fast path)

This is the part that spans both targets and is easy to get wrong. Iteration 1 shipped a per-byte
`CMD_MIDI_SEND` / `CMD_MIDI_RECV` command handshake and hardware measurement killed it: ~970 bytes/s
each way, about 3x slower than a real 31250-baud MIDI ring, and untunable because the cost is the bus
handshake itself (D-12). Those commands are retired. The current path:

- **OUT (ST to RP)** is fire-and-forget. Each byte is a single ROM3 read whose address encodes it:
  `ROM3_SYNC_BASE ($FB8000) + MIDI_OUT_MARKER ($0100) + byte`. RP-side, `midi_rom3_consumer` in
  `midi.c` is registered with `chandler_setRawConsumer()` and sees every commemul sample **before**
  the TPROTOCOL parser, recovers `addr ^ 0x8000`, and routes bit-8 samples straight to the network.
  No frame, no token, no wait.
- **IN (RP to ST)** is a mailbox in `APP_FREE`, written by the RP and polled by the m68k (which owns
  no writable state, since the cartridge is ROM): `$FA2300` pre-baked `Bconstat` return
  (-1 ready / 0 none), `$FA2304` the popped byte for `Bconin`, `$FA2308` an advance-ack counter the
  RP bumps after a pop plus republish. The ST signals consumption with marker `$0200`.
- **Marker `$0400`** deactivates the gate on a warm reset so the re-install's command frame is parsed
  normally.
- `midiActive` (set by `midi_set_active`) gates the routing, so boot-menu and config command frames
  are never mistaken for MIDI bytes.
- The only surviving MIDI command is `CMD_MIDI_SAVE_VECTOR` (`0x0300`): the m68k cannot write the
  XBRA `<old>` field in ROM, so it asks the RP to patch that longword into the served image.

Marker values, the mailbox offsets, and the command number are duplicated in
`rp/src/include/midi.h` and `target/atarist/src/userfw.s`. Change both together.

### RP2040 side (`rp/src/`)
- `main.c` only sets clock/voltage, calls `gconfig_init` then `aconfig_init`, and hands off to
  `emul_start()`. If config init fails it jumps to the **Booster** app via `reset_jump_to_booster()`.
  **Don't add features to `main.c`**; put them in `emul.c` or a new module.
- `emul.c` / `emul.h` hold the main loop and the boot menu. `emul_start()` initializes
  config/network/display, calls `commemul_init()`, `chandler_init()`, `chandler_addCB(term_command_cb)`,
  and `midi_init()`, then spins the hot loop: `chandler_loop()` first and unconditionally (a gated
  call cost ~1 ms per MIDI byte), then `network_safePoll()`, `midi_net_poll()`, `term_loop()`, the
  countdown/menu refresh, and finally `cyw43_arch_wait_for_work_until(LOOP_TEST_WAIT_MS)` to pace the
  loop without free-spinning the CYW43 SPI. commemul raises no IRQ, so that timeout is the only bound
  on how long MIDI can stall: keep it at 1 ms.
- `midi.c` / `include/midi.h`: the MIDI app itself. Raw-sample consumer, IN/OUT queues, the lwIP TCP
  and WebSocket client to the orchestrator, DNS resolution of the configured host, reconnect, link
  status strings for the menu, and the per-app config keys (`MIDI_HOST`, `MIDI_PORT`,
  `MIDI_TRANSPORT`, `MIDI_WS_PORT`, `MIDI_WS_PATH`, `MIDI_ROOM`, `MIDI_ENABLED`).
- `midi_ws.c` / `include/midi_ws.h`: RFC 6455 client framing and handshake math, deliberately free of
  lwIP and pico dependencies so it stays portable and mirrors `orchestrator/ws.py`.
- `chandler.c` / `include/chandler.h`: **the primary RP-side extension point.** `chandler_loop()`
  polls the shared region for command words the m68k posted and dispatches to a linked list of
  callbacks registered with `chandler_addCB(cb)` (signature
  `void cb(TransmissionProtocol *protocol, uint16_t *payloadPtr)`, max `CHANDLER_MAX_CALLBACKS` = 16).
  `chandler_setRawConsumer(cb)` installs the single pre-parser hook used by the MIDI fast path. This
  file also owns the canonical region-layout constants that `main.s` mirrors.
- `romemul.c` / `romemul.pio`: PIO programs and runtime emulating the cartridge ROM/RAM bus (driven by
  the `READ_*` / `WRITE_*` GPIOs in `include/constants.h`).
- `commemul.c` / `commemul.pio`: ROM3 communication emulator backed by an aligned DMA ring buffer;
  feeds command/payload words from the Atari bus to chandler.
- `gconfig.c` / `aconfig.c`: global vs per-app configuration in dedicated flash sectors, on top of
  `settings/` (a key-value store).
- `network.c`: Wi-Fi (CYW43, lwIP poll mode). **Power management is forced off unconditionally and
  `PARAM_WIFI_POWER` is ignored** (D-15). Any power-save mode makes idle RTT swing from 5 ms to
  ~900 ms and breaks the lock-step ring. Do not "restore" the setting.
- `sdcard.c`, `hw_config.c`: FatFs over SPI/SDIO via the bundled `fatfs-sdk`.
- `display.c`, `display_term.c`, `term.c`, `u8g2/`: terminal-style display rendered into the Atari
  framebuffer at `$FAE0C0` and/or a local OLED. `term.c` plus the `cmd*` handlers in `emul.c` build
  the boot menu (`[H]ost`, `[P]ort`, `[T]ransport`, `[R]oom`, `[E]xit to GEM`, `[X] Booster`).
- `blink.c`, `select.c`, `reset.c`, `tprotocol.c`: LED Morse status, SELECT-button handling, soft
  reset/jump-to-booster, transport protocol primitives.

### Memory layout (`rp/src/memmap_rp.ld`)

| Region | Origin | Length | Purpose |
| --- | --- | --- | --- |
| `FLASH` | `0x10000000` | 1024 K | App code |
| `ROM_TEMP` | `0x10100000` | 128 K | Scratch area for loaded ROMs |
| `BOOSTER_APP_FLASH` | `0x10120000` | 768 K | Reserved for the Booster app (do not write from this app) |
| `CONFIG_FLASH` | `0x101E0000` | 120 K | 30 sectors of per-app config |
| `GLOBAL_LOOKUP_FLASH` | `0x101FE000` | 4 K | UUID to config-sector lookup |
| `GLOBAL_CONFIG_FLASH` | `0x101FF000` | 4 K | Global config |
| `RAM` | `0x20000000` | 128 K | Normal RAM |
| `ROM_IN_RAM` | `0x20020000` | 128 K | ROM data mirrored to RAM for fast bus access |

The build assumes Core 0 owns flash writes (`PICO_FLASH_ASSUME_CORE0_SAFE=1`). The PIO bus emulation
runs hot, so Core 0 overclocks to 225 MHz at `VREG_VOLTAGE_1_10`.

### App identity
`CURRENT_APP_UUID_KEY` (set from the `APP_UUID_KEY` env var at CMake time, with a placeholder
default) is the app's UUID4. It must match the `uuid` field in `desc/app.json` and is the key into
`GLOBAL_LOOKUP_FLASH` that finds this app's config sector. A mismatch sends the app to the Booster.

### Orchestrator and gateway
The orchestrator is a **dumb byte relay** (D-02, D-04): each player's MIDI OUT goes verbatim to the
next player's IN, in insertion order, wrapping. It parses no MIDI and no game protocol on the relay
path; `--inspect` runs a read-only decoder off to the side for tracing, and it feeds the phase/master
badges in the status page. TCP (`:5005`) and WebSocket (`:5006`) listeners run at once and share the
rings. A room key selects a private ring, presented as `Authorization: Bearer <key>` or `?room=<key>`
on the WS handshake; rooms are pre-provisioned over the REST API on `:8080` and an unknown key is
refused. No TLS anywhere: terminate it at a reverse proxy.

The wire contract between firmware and server is `docs/epics/ORCHESTRATOR-CONTRACT.md`. Read it before
changing either side's framing.

### The constraint behind most decisions
MIDI Maze is **lock-step** (C-01): every machine must receive every other player's byte before it
computes the next frame, so ring latency sets the frame rate, and a late byte can freeze or desync
the game rather than merely slow it. That is why the byte stream stays opaque, why `TCP_NODELAY` is
on, why Wi-Fi power-save is banned, why `chandler_loop()` runs unconditionally, and why the per-byte
handshake had to go. Weigh any change on the MIDI path against it.

## Planning workflow (`docs/epics/`)

Unlike other Sidecartridge microfirmwares, the backlog **is committed to git** and is the planning
source of truth alongside the code.

- **Epic**: folder `EPIC-NN-<slug>/` with an `epic.md` carrying `iteration: N`.
- **Story**: `STORY-NN-<slug>.md` inside the epic folder, with YAML frontmatter
  (`id`, `epic`, `title`, `status`, optional `milestone`).
- **Task**: a `- [ ]` / `- [x]` checkbox inside a story. Checkboxes drive the percentages, `status`
  is read verbatim. Keep the two honest with each other.
- `templates/epic.md` and `templates/story.md` are the starting points.
- `ITERATIONS.md` is the narrative (goal plus outcome per iteration); `DECISIONS.md` holds
  cross-cutting decisions `D-NN` and constraints `C-NN` that stories cite instead of re-arguing;
  `ORCHESTRATOR-CONTRACT.md` is the firmware/server interface.
- **`STATUS.md` is generated. Never edit it by hand.** Run `./docs/epics/cockpit.sh` after changing
  any epic or story and commit the regenerated file with the change
  (`./docs/epics/cockpit.sh --stdout` previews).

Commits follow Conventional Commits with the affected area as the scope (`feat(firmware):`,
`fix(orchestrator):`, `perf(docker):`, `docs(epics):`) and name the epic/story they advance, for
example `fix(firmware): resolve MIDI_HOST via lwIP DNS (EPIC-18 STORY-01)`. `CHANGELOG.md` is
user-facing prose grouped by release, not a commit dump.

## Editing guardrails

- **Never modify** `pico-sdk/`, `pico-extras/`, `fatfs-sdk/`, or `midi-maze-js/`. They are git
  submodules pinned to specific upstream revisions, and the build re-pins them on every run. To
  change FatFs configuration, edit `rp/src/ff/ffconf.h` (project-owned override); the include path is
  set up so this file wins over the submodule's default.
- Don't touch `main.c` for feature work; start in `emul.c`.
- Keep the orchestrator and the gateway on the Python 3 standard library (D-10). No pip, ever.
- Match the existing C style (clang-format config in `.clang-format`, clang-tidy in `.clang-tidy`,
  both wired up via CMake when the binaries are on `PATH`).

---

## Working style

These behavioral guidelines bias toward caution over speed. For trivial tasks, use judgment.

### 1. Think before coding

Before implementing:
- State your assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them. Don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

### 2. Simplicity first

Minimum code that solves the problem. Nothing speculative.
- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

Ask: "Would a senior engineer say this is overcomplicated?" If yes, simplify.

### 3. Surgical changes

Touch only what you must. Clean up only your own mess.
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it. Don't delete it.
- When your changes orphan an import/variable/function, remove it. Don't remove pre-existing dead
  code unless asked.

The test: every changed line should trace directly to the user's request.

### 4. Goal-driven execution

Define success criteria. Loop until verified.
- "Add validation" becomes "write tests for invalid inputs, then make them pass"
- "Fix the bug" becomes "write a test that reproduces it, then make it pass"
- "Refactor X" becomes "ensure tests pass before and after"

For multi-step tasks, state a brief plan with a verification check per step.

### 5. Writing style

Write as a senior technical writer: precise, plain, substance first. In every artifact (code
comments, docs, commits, PRs, chat):
- **No em dashes or en dashes.** Use a comma, parentheses, a colon, or two sentences. This applies to
  scripts that generate committed text too: fix the generator, not just its output.
- Banned words: "genuine" / "genuinely".
- No rhetorical three-item series of the form "A, B, and C".
- No AI-flattery or terse-summary openers ("Great question", "Short answer:", "TL;DR:").
- No summary closers, no corporate hedging ("It's important to note that").

### 6. No AI attribution

Never add AI-tool attribution to commits, PR descriptions, code comments, docs, or any other
artifact. This means **no**:
- "Generated with Claude Code", "Co-authored by Claude", "Made with ChatGPT", or similar phrasing.
- `Co-Authored-By: Claude ...`, `Co-Authored-By: ChatGPT ...`, or any other AI co-author trailer.
- "AI-assisted", "written with the help of an LLM", etc., as comments or changelog entries.

Write the message as the human author. Do not mention AI tools used to produce the work.
