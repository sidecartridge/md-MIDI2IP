---
id: STORY-03
epic: EPIC-14
title: Orchestrator REST provisioning API (admin-key writes, reject unknown)
status: done
---

## Goal

An operator provisions rooms through a small REST API on the HTTP port. Writes need an
admin key; reads are open. A join to a room that was not provisioned is refused.

## Tasks

- [x] Add REST routes to the HTTP server: `GET /rooms` (list, open), `POST /rooms` with a JSON or form body carrying the key (create, admin), `DELETE /rooms/{key}` (delete, admin)
- [x] Admin auth: writes require an `X-Admin-Key` header matching `--admin-key`; when `--admin-key` is unset, writes return 403 (the default room still works without provisioning)
- [x] Enforce pre-provisioned rooms: a WS join with a key that is not provisioned is rejected at the handshake (HTTP 403, connection closed); the default room is always present
- [x] Deleting a room closes its players' connections and removes the ring
- [x] Normalize keys (uppercase) on create / delete / lookup so the menu, the gateway, and REST agree
- [x] selftest: `POST /rooms` (with the admin key) creates a room and a WS node then joins it; a join with an unknown key is refused; `POST` without the admin key returns 403; `GET /rooms` lists rooms

## Acceptance

Rooms are created, listed, and deleted over REST with admin-guarded writes; a join to an
unprovisioned room is refused; the default room needs no provisioning. selftest covers it.

## Notes

REST shares the existing hand-rolled HTTP server (EPIC-04 STORY-03 / EPIC-13). Keep it
stdlib only. For an exposed deployment, a reverse proxy adds TLS and can guard the admin
routes.
