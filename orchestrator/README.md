# Orchestrator (EPIC-04)

The central server that connects MIDI Maze players into a ring by relaying raw
bytes. **Python 3 standard library only** — no third-party packages, ever.

```sh
python3 orchestrator/orchestrator.py            # game on 0.0.0.0:5005, status on :8080
python3 orchestrator/orchestrator.py --port 6000 --http-port 8081
```

Status: open <http://localhost:8080/> (auto-refreshing HTML) or
<http://localhost:8080/status.json> (machine-readable).

Self-test (spawns its own server on test ports, exit 0 = PASS):

```sh
python3 orchestrator/selftest.py
```

Each connecting client (a ST+RP, or a Hatari gateway from EPIC-05) is a *player*.
The RP firmware's `MIDI_NET_HOST`/`PORT` (EPIC-03) points here.

## Status

- **STORY-01:** asyncio TCP server + connection registry (id, peer, connect time,
  byte counters), `TCP_NODELAY`, connect/disconnect logging.
- **STORY-02:** ring relay — each player's OUT bytes go to the next player's IN
  (insertion order, wrapping); a ring of one echoes to self.
- **STORY-03:** HTTP status on a separate port (HTML page + `/status.json`),
  served in the same asyncio loop (race-free).
- **STORY-04:** robustness — keepalive, slow-player drop, clean shutdown, and
  **one connection per private IP** (a reconnect supersedes a node's stale
  connection; public/NAT and loopback exempt).
- **STORY-05:** validated end to end via `selftest.py` (ring relay, status,
  drop/reconnect).
