---
id: STORY-07
epic: EPIC-03
title: Remove unused HTTP/HTTPS/TLS plumbing
status: todo
---

## Goal

Strip the HTTP/HTTPS firmware-download client the template ships but MIDI-to-IP
never uses: `rp/src/download.c` (~350 lines), `rp/src/httpc/` (~140 lines), and
the mbedTLS / `altcp_tls` stack behind them. The RP talks a **raw byte stream
over TCP** to the orchestrator (D-02), and app install/update is the **Booster**
app's job — nothing in this app calls the HTTP client. Removing it frees flash
and drops the TLS/crypto dependency.

## Tasks

- [ ] Confirm no app path calls `download.c` / `httpc` (grep shows no callers; firmware update lives in Booster)
- [ ] Remove `download.c` and the `httpc/` subdir from the build (`rp/src/CMakeLists.txt`: `target_sources`, `add_subdirectory(httpc)`, the `httpc` link, the HTTPS/HTTP download toggle)
- [ ] Drop mbedTLS / `altcp_tls` bits (CMake links, any `LWIP_ALTCP*` leftovers in `lwipopts.h`) — keep raw `tcp_*` (`LWIP_TCP`) for the MIDI client
- [ ] Delete the orphaned files and any now-dead includes/references
- [ ] Build: confirm UF2 shrinks, still boots, and MIDI-over-IP (STORY-01–05) still works

## Acceptance

The firmware builds with no `httpc` / `download.c` / mbedTLS, the UF2 is smaller,
MIDI-over-IP still works end to end, and no HTTPS/TLS references remain in the app.

## Notes

D-02 (raw bytes, no protocol/TLS layer) is why none of this is needed.
Complements EPIC-04's general template-cleanup story — this is the
network-specific slice. **Risk:** make sure nothing relies on in-app firmware
self-download; that capability belongs to the Booster app, not this microfirmware.
