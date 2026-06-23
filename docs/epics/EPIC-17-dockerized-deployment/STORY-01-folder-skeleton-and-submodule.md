---
id: STORY-01
epic: EPIC-17
title: Deploy folder skeleton + midi-maze-js submodule
status: done
---

## Goal

A `docker/` folder that holds every deployment file, and `midi-maze-js` available
to the build as a pinned git submodule.

## Tasks

- [x] Create the top-level `docker/` folder (Dockerfile, `nginx/`, `supervisor/`,
      `entrypoint.sh`, `README.md` live here).
- [x] Add `midi-maze-js` as a git submodule (URL provided by Diego); pin a ref and
      commit `.gitmodules`.
- [x] Decide where the build reads the web app from (the submodule path) and
      whether it needs a build step (npm/vite) or ships ready-to-serve static files.
- [x] Add a short `docker/README.md` stub describing the layout.

## Acceptance

`git submodule update --init` fetches midi-maze-js; the `docker/` layout is in
place and documented.

## Notes

If midi-maze-js needs a build (npm/vite), STORY-03 adds a multi-stage Node build
stage; if it ships prebuilt static files, nginx serves them directly. Submodule
URL is the one blocking input.
