---
id: STORY-06
epic: EPIC-17
title: Build, validate end-to-end, and document deployment
status: todo
---

## Goal

A built image, validated for the full browser + remote-node flow, with deploy docs.

## Tasks

- [ ] Build the image (`docker build`) including the submodule; confirm the image
      size is reasonable.
- [ ] Run locally and verify: a browser loads the app on :80, provisions/lists a
      room, connects over WebSocket, and plays.
- [ ] Verify a remote node reaches the server: a TCP node on :5005 and/or a Hatari
      `--transport ws` node on :5006 join the same room.
- [ ] Verify rooms persist across a container restart (volume mounted).
- [ ] Write `docker/README.md`: build, run, parameters, ports, volume, and a
      one-liner deploy example for any server.
- [ ] Update the top-level `README.md` to point at the Docker deployment.

## Acceptance

On a clean host with Docker, `docker run` (with the documented params) yields a
working deployment: browser play via :80 + the orchestrator, and remote nodes can
join the same rooms. Documented end to end.

## Notes

This closes the iteration: a single image anyone can `docker run` to host MIDI Maze
over IP for browsers and hardware alike.
