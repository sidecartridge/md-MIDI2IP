---
id: STORY-01
epic: EPIC-05
title: Loopback against a desktop network-MIDI bridge
status: todo
milestone: alpha-mvp
---

## Goal

Stand up a desktop peer that bridges the network stream to a host MIDI port, and
verify a real ST app can play a synth/DAW through it (and receive).

## Tasks

- [ ] Pick/build a desktop bridge matching the STORY EPIC-03/01 transport
- [ ] OUT path: ST MIDI app → bridge → host DAW receives notes
- [ ] IN path: host MIDI source → bridge → ST app receives notes
- [ ] Document the setup steps in this folder for repeatability

## Acceptance

A note played on the ST sounds on the host DAW, and vice-versa, reliably.

## Notes

Document exact bridge config so anyone can reproduce the test.
