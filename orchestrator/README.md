# Orchestrator

The central server that connects MIDI Maze players into a ring by relaying raw bytes.
Python 3 standard library only, no third-party packages.

```sh
python3 orchestrator/orchestrator.py            # TCP game on 0.0.0.0:5005, status on :8080
python3 orchestrator/orchestrator.py --ws --admin-key secret --rooms-file rooms.json
```

Flags: `--host`, `--port`, `--http-port`, `--inspect` (decode and log the MIDI Maze
protocol as it passes, read-only), `--no-http` (drop the status page so a status poll
cannot add jitter to the lock-step ring), `--ws` / `--ws-port 5006` (also accept WebSocket
nodes), `--admin-key <key>` (enable the rooms REST API; writes need it), `--rooms-file
<path>` (persist provisioned rooms across restarts), `--room-ttl 600` (reclaim an empty
room after this many seconds).

Status page: open <http://localhost:8080/> for the live SVG ring view, which polls
`/status.json` every 2 seconds and offers a room dropdown. <http://localhost:8080/lobby>
lists every room. <http://localhost:8080/status.json> serves the raw per-node telemetry
(`?room=KEY` scopes it to one room).

## Transports

A node reaches the orchestrator over plain TCP (default, port 5005) or, with `--ws`, over
WebSocket (port 5006). Both listeners run at once and feed the same rings, so TCP and
WebSocket nodes mix. WebSocket exists to traverse HTTP reverse proxies and firewalls that
only allow web ports; the byte stream is unchanged. `wss` / TLS is not supported here,
terminate TLS at a reverse proxy and speak `ws` internally.

## Rooms (private rings)

One orchestrator hosts many private rings keyed by a room key. A WebSocket node presents
its key as `Authorization: Bearer <key>`; a TCP or keyless node joins the default room.
Rooms are pre-provisioned over REST (an unknown key is refused), each ring caps at 16
players, and an empty room is reclaimed after `--room-ttl`.

```sh
curl http://localhost:8080/rooms                                            # list (open)
curl -X POST http://localhost:8080/rooms -H "X-Admin-Key: secret" -d '{"key":"DIEGOROOM"}'
curl -X POST http://localhost:8080/rooms -H "X-Admin-Key: secret"           # auto code
curl -X DELETE http://localhost:8080/rooms/DIEGOROOM -H "X-Admin-Key: secret"
```

Writes (`POST` / `DELETE`) require an `X-Admin-Key` header matching `--admin-key`, and are
refused when it is unset; reads are open. The room key gates a ring, it does not secure the
traffic.

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

`status.json` is scoped to one room (`?room=KEY`, default room otherwise) and reports the
room key, game `phase`, `master` node id, and per node in ring order: `id`, `ip`,
reverse-DNS `host`, `peer`, `transport` (`tcp` / `ws`), `connected_s`, `idle_s`,
`bytes_out` (bytes received from the node), `bytes_in` (bytes sent to it). The phase and
master come from the read-only `--inspect` decoder running per room, off the relay path.
The server enforces one connection per private IP within a room. A reconnect from the same
IP supersedes the prior connection when that connection is a private-LAN node or has
stalled, and the reconnection takes a fresh node id. TCP keepalive plus a slow-player drop
keep one stuck node from freezing the ring.

On a disconnect, the orchestrator holds nothing to replay: it relays directly (no per-player
byte queue), the per-connection write buffer is bounded and discarded when the socket
closes, and the WebSocket frame decoder state is dropped with the connection. So a node
joining later sees only traffic sent after it joined. The firmware does its part too: it
flushes both its IN and OUT queues on a link drop (EPIC-15), so a reconnect cannot replay
pre-drop bytes.
