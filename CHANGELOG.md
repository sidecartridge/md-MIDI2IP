# Changelog

## v1.1.1beta (2026-06-23)

### Run your own server with Docker (new)

- A single Docker image now hosts the whole server side: the orchestrator (game,
  WebSocket, and status/REST ports) plus the `midi-maze-js` browser game on port 80,
  so any machine can host MIDI Maze over IP for browsers and hardware nodes alike. It
  ships with a one-argument launcher and a remote installer, and a single-port mode
  (everything over port 80) for servers behind a firewall or domain. See
  `docker/README.md`.

### Connect to the orchestrator by name (new)

- A node can now point at the orchestrator by **hostname** (e.g.
  `midimaze.sidecartridge.com`), not just a numeric IP address — the firmware
  resolves the name via DNS before connecting.

### More reliable multiplayer

- The server now notices when a WebSocket player drops without a clean close (lost
  network, closed browser tab) and removes it from the ring within about 30 seconds,
  instead of leaving a "ghost" player that stalled the game.

---

## v1.1.0beta (2026-06-22)

### More reliable Wi-Fi (network latency fix)

- Fixed a major source of network lag: the firmware now keeps the Pico W's Wi-Fi radio
  always awake. A power-save mode was letting the radio nap between beacons, so whenever the
  game wasn't flooding the link the round-trip time swung wildly — from a few milliseconds up
  to nearly a second, with occasional dropouts — enough to stall MIDI Maze's lock-step ring
  and time out a match start. Power management is now forced off (the old `WIFI_POWER` option
  is ignored), so latency stays flat.

---

## v1.0.0beta (2026-06-18)

MIDI-to-IP turns a real Atari ST (through the SidecarTridge Multi-device) or the Hatari
emulator into a network player for MIDI Maze, so people on different machines or networks
can play the classic ring deathmatch over IP. This beta is the first build where the whole
experience works end to end on real hardware.

### Play MIDI Maze over the network

- Bring up a real Atari ST with a SidecarTridge, or the Hatari emulator through the gateway,
  and play MIDI Maze with up to 16 players in one ring. Real and emulated machines mix
  freely.
- A small orchestrator wires everyone into the ring and relays the game between players. It
  is a single Python script with no dependencies to install.
- A live web view (the orchestrator's status page) draws the ring as players join and shows
  the bytes flowing to and from each node.

### Set it up from the Atari ST boot menu

- The MIDI-to-IP boot menu lets you point the ST at the orchestrator: press `[H]ost` for its
  address and `[P]ort` for its port. Your Wi-Fi state, local IP, and connection status are
  shown on screen, and the settings persist across reboots.
- Launch the firmware with `[E]xit to GEM`, or step back to the Booster with `[X]`. From GEM
  you just run MIDI Maze as usual.

### Connect over TCP or WebSocket (new)

- A node can reach the orchestrator over a plain socket or over **WebSocket**. WebSocket
  rides a standard web port and an HTTP upgrade, so you can reach an orchestrator that sits
  behind a reverse proxy, or a firewall that only allows web traffic. The game bytes are the
  same either way.
- Choose it per node: press `[T]ransport` on the ST to switch between `tcp` and `ws` (each
  carrier keeps its own port), or pass `--transport ws` to the Hatari gateway.

### Private play rooms (new)

- One orchestrator can host many separate games at once. A **room key** picks a private
  ring: everyone who enters the same key (for example `DIEGOROOM`) plays together, isolated
  from the other rooms. A node with no key joins a shared default ring.
- Enter the key with `[R]oom` on the Atari ST, or `--room` on the Hatari gateway.
- An operator creates rooms over a small REST API, so only the rooms you set up can be
  joined. A **lobby page** lists every room with its player count and current game phase,
  each one a link into its ring view, where the master node is highlighted.

### More reliable

- A node that disconnects leaves the ring promptly instead of lingering on screen.
- A reconnect no longer replays stale bytes left over from before the drop, so a player who
  drops and rejoins does not corrupt the match.

### Install

- Install MIDI-to-IP from the **Booster** app like any SidecarTridge microfirmware: open the
  Apps tab, download it, then launch. No manual flashing needed.
- The orchestrator and the Hatari gateway are Python 3 standard-library scripts, so they run
  anywhere Python does with nothing to install.

See the [README](README.md) for full setup, including the WebSocket and private-room
details.

---

## v1.0.0alpha

First playable cut: MIDI Maze running over IP between two nodes, with the Atari ST's MIDI
captured at the BIOS layer and carried to the orchestrator. The groundwork that v1.0.0beta
turns into a full, room-aware, multi-transport experience.
