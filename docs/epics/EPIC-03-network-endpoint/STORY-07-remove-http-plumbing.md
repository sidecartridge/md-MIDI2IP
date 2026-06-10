---
id: STORY-07
epic: EPIC-03
title: Remove unused HTTP/HTTPS/TLS plumbing
status: done
---

## Goal

Strip the HTTP/HTTPS firmware-download client the template ships but MIDI-to-IP
never uses: `rp/src/download.c` (~350 lines), `rp/src/httpc/` (~140 lines), and
the mbedTLS / `altcp_tls` stack behind them. The RP talks a **raw byte stream
over TCP** to the orchestrator (D-02), and app install/update is the **Booster**
app's job — nothing in this app calls the HTTP client. Removing it drops the
TLS/crypto build dependency and ~489 lines of dead source.

## Tasks

- [x] Confirm no app path calls `download.c` / `httpc` (grep showed no callers; firmware update lives in Booster)
- [x] Remove `download.c` and the `httpc/` subdir from the build (`rp/src/CMakeLists.txt`: `target_sources`, `add_subdirectory(httpc)`, the `httpc` link, the `APP_DOWNLOAD_HTTPS` toggle)
- [x] Drop the mbedTLS link (it came in via `httpc` → `pico_lwip_mbedtls`/`pico_mbedtls`); `LWIP_ALTCP*` stay at 0 (lwIP default), comment refreshed — raw `tcp_*` only
- [x] Delete the orphaned files (`download.c`, `download.h`, `httpc/`, `mbedtls_config.h`)
- [x] Clean rebuild succeeds; ELF has **0** mbedtls/httpc/altcp symbols

## Acceptance

The firmware builds with no `httpc` / `download.c` / mbedTLS and no HTTPS/TLS
references remain; MIDI-over-IP still works end to end.

**Outcome (honest):** the **UF2 size is unchanged** — `--gc-sections` had already
dead-stripped the unused HTTP/TLS code, so there was no flash to reclaim (ELF
confirms 0 TLS symbols). The win is **source + build cleanliness**: −489 lines,
no mbedTLS dependency in the build graph, faster compile.

## Notes

D-02 (raw bytes, no protocol/TLS layer) is why none of this is needed.
Complements EPIC-06's general template-cleanup story — this is the
network-specific slice. The MIDI path was untouched, so MIDI-over-IP behaviour is
unchanged (flash to re-confirm). Firmware self-download lives in the Booster app.
