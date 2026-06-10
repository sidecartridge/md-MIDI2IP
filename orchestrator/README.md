# Orchestrator (EPIC-04)

The central server that connects MIDI Maze players into a ring by relaying raw
bytes. **Python 3 standard library only** — no third-party packages, ever.

```sh
python3 orchestrator/orchestrator.py            # listen on 0.0.0.0:5005
python3 orchestrator/orchestrator.py --port 6000
```

Each connecting client (a ST+RP, or a Hatari gateway from EPIC-05) is a *player*.
The RP firmware's `MIDI_NET_HOST`/`PORT` (EPIC-03) points here.

## Status

- **STORY-01 (done here):** asyncio TCP server + connection registry (id, peer,
  connect time, byte counters), `TCP_NODELAY`, connect/disconnect logging.
  Incoming bytes are counted and discarded — no relay yet.
- STORY-02 — ring relay (forward each player's OUT to the next player's IN)
- STORY-03 — HTTP status (HTML + JSON, separate port)
- STORY-04 — robustness (keepalive, bounded buffers, clean shutdown)
