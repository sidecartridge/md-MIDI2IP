---
id: STORY-05
epic: EPIC-17
title: Rooms persistence + configuration surface
status: todo
---

## Goal

Provisioned rooms survive container restarts, and the full configuration surface is
documented and easy to set.

## Tasks

- [ ] Point `--rooms-file` at a path on a declared `VOLUME` so the rooms JSON
      persists across `docker run` / restarts.
- [ ] Document the admin-key flow for provisioning rooms over the REST API.
- [ ] Provide a `.env.example` (or documented env vars) for every parameter.
- [ ] Provide a `docker run` example (and an optional compose snippet for
      convenience, even though the deliverable is the single image).

## Acceptance

Rooms created via the REST API persist after the container is recreated (with the
volume mounted); every orchestrator parameter is reachable via an env var.

## Notes

`--rooms-file ""` is in-memory; the image defaults it to the volume path so rooms
persist out of the box.
