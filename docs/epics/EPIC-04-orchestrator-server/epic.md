---
id: EPIC-04
title: Orchestrator server
status: todo
---

## Goal

A central **server** that connects players into a MIDI Maze ring by relaying raw
bytes, with an HTTP interface for status. It lives **in this repo** under
`orchestrator/` (revises D-04/D-08 — no longer a separate repo) and is written in
**Python 3 using the standard library only** — no third-party packages, ever
(`asyncio`, `http.server`/`http`, `socket`, etc.). `tools/echo_peer.py` is the
starting reference.

This is the second node D-09 requires: with the orchestrator wiring the ring,
real players (a ST+RP, or a Hatari gateway from EPIC-05) can actually play.

## Scope (MVP)

- **In:** an asyncio TCP server that accepts player connections; a **dumb ring
  relay** (each player's OUT bytes → the next player's IN); **low-level connection
  tracking** (who's connected, since when, byte counters); and an HTTP status
  interface.
- **Out (deferred):** **MIDI-Maze protocol awareness** — the MVP does *not* parse
  the byte stream. So "gameplays disputing / disputed" (game-session detection and
  history) needs a later **smart** epic; the MVP HTTP shows connections + the
  current ring, not parsed game sessions. No server-side fake/drone player —
  solo play is covered by running a Hatari player (EPIC-05).

## Stories

- STORY-01 — asyncio TCP server + connection registry
- STORY-02 — Ring relay (single global ring; re-forms on join/leave)
- STORY-03 — HTTP status interface (HTML page + JSON, separate port)
- STORY-04 — Robustness: half-open detection, bounded buffers, clean shutdown
- STORY-05 — Validate: two clients form a ring and exchange bytes

## Notes

The firmware connects to a plain `host:port` with no room concept, so for the MVP
all connected players form **one ring** (multi-game/rooms is a later concern). The
relay is byte-agnostic (D-02) — it never interprets MIDI Maze, it just wires the
ring and counts bytes. Stdlib-only keeps it trivially runnable anywhere Python 3
is installed.
