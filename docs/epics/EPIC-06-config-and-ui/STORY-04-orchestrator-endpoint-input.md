---
id: STORY-04
epic: EPIC-06
title: Input screens for the orchestrator endpoint (host/IP + port)
status: done
---

## Goal

Let the user set the orchestrator endpoint from the device UI: one **input screen
to enter the orchestrator host** (an IP address or a hostname) and another to
enter the **port** — reusing md-drives-emulator's RTC **hostname** and **port**
input screens. Values persist in per-app config (STORY-01).

## Tasks

- [x] Port md-drives-emulator's RTC **hostname** input screen to enter the orchestrator host (accepts a dotted IP **or** a DNS hostname)
- [x] Port md-drives-emulator's RTC **port** input screen to enter the orchestrator port
- [x] Persist both into STORY-01's per-app config keys (`aconfig`), with basic validation (non-empty host, port in 1..65535)
- [x] Reach the screens from the boot menu (STORY-02); **cancel** leaves the stored value unchanged, **confirm** saves
- [x] The network client (EPIC-03) picks up the new host/port on its next connect

## Acceptance

The user can enter/edit the orchestrator host and port on-screen; the values save
to per-app config and the RP connects to the new endpoint on the next attempt.

## Notes

Direct reuse of md-drives-emulator's RTC config input screens (it sets an NTP/RTC
hostname + port the same way) — the same field-entry widget and key handling. The
host field accepts both a dotted IP and a DNS name (lwIP resolves it). Backed by
STORY-01's config keys.
