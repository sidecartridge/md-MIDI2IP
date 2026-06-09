---
id: STORY-01
epic: EPIC-05
title: Desktop test peer / network-MIDI bridge
status: todo
milestone: alpha-mvp
---

## Goal

Stand up a desktop peer that connects to the firmware over the network. It serves
two roles: a **stand-in second player** so single-ST MIDI Maze can be validated
(EPIC-03 STORY-05) without a second machine, and a **bridge to a host MIDI port**
so a real ST app can drive a synth/DAW (and receive) — the general MIDI-to-IP
use case.

## Tasks

- [ ] Pick/build a desktop bridge matching the STORY EPIC-03/01 transport
- [ ] OUT path: ST MIDI app → bridge → host DAW receives notes
- [ ] IN path: host MIDI source → bridge → ST app receives notes
- [ ] Document the setup steps in this folder for repeatability

## Acceptance

A note played on the ST sounds on the host DAW, and vice-versa, reliably.

## Notes

Document exact bridge config so anyone can reproduce the test.
