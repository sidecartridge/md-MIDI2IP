# Orchestrator

The central server that connects MIDI Maze players into a ring by relaying raw bytes.
Python 3 standard library only, no third-party packages.

```sh
python3 orchestrator/orchestrator.py            # game on 0.0.0.0:5005, status on :8080
python3 orchestrator/orchestrator.py --port 6000 --http-port 8081
```

Flags: `--host`, `--port`, `--http-port`, `--inspect` (decode and log the MIDI Maze
protocol as it passes, read-only), `--no-http` (drop the status page so a status poll
cannot add jitter to the lock-step ring).

Status page: open <http://localhost:8080/> for the live SVG ring view, which polls
`/status.json` every 2 seconds. <http://localhost:8080/status.json> serves the raw
per-node telemetry.

Self-test (spawns its own server on test ports, exit 0 = PASS):

```sh
python3 orchestrator/selftest.py
```

Each connecting client (a ST+RP, or a Hatari gateway) is a *player*. The RP firmware
points here via its configured orchestrator host and port.

## How it works

The orchestrator is a dumb byte relay. Each player's MIDI OUT is forwarded verbatim to
the next player's MIDI IN (insertion order, wrapping); a ring of one echoes to itself.
The firmware owns the ring protocol, so the relay path stays opaque and does no parsing.
`--inspect` adds an off-path decoder for debugging only.

`status.json` reports, per node in ring order: `id`, `ip`, reverse-DNS `host`, `peer`,
`connected_s`, `idle_s`, `bytes_out` (bytes received from the node), `bytes_in` (bytes
sent to it). The server enforces one connection per private IP. A reconnect from the
same IP supersedes the prior connection when that connection is a private-LAN node or
has stalled, and the reconnection takes a fresh node id. TCP keepalive plus a slow-player
drop keep one stuck node from freezing the ring.
