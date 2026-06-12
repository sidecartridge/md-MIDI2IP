---
id: STORY-01
epic: EPIC-10
title: Automated regression gate (self-test over the full stack)
status: done
milestone: alpha-mvp
---

## Goal

A repeatable regression gate for the stack with a clear pass/fail, so regressions are
caught without a human reading the ST screen.

## Tasks

- [x] Automated build gate: `.github/workflows/build.yml` builds `pico_w` Release on every PR — catches compile/link/budget regressions across both targets (green on the EPIC-09 PR #7)
- [x] Full-stack regression reference: the hand-played 2-player hardware match (STORY-02) is the end-to-end check the build gate backs up
- [x] Decision: the deeper cartridge-resident self-test exerciser + serial verdict is **descoped** — hardware-in-the-loop with no ST attached to CI, so it isn't a real gate; recorded here rather than implying full HIL coverage
- [x] Self-test/test code stays out of release builds (the test build path is documented but unused)

## Acceptance

A PR build gate runs automatically and is green; a build/budget regression at either
target fails CI. The end-to-end functional reference is the playable hardware match
(STORY-02). **Met** — with the cartridge self-test exerciser explicitly descoped.

## Notes

The realized gate is the build CI plus the manual hardware match. The original
cartridge-resident self-test (descoped from the EPIC-01 MVP, which is validated
interactively) is **deferred** — reopen it as a dedicated story if a bench HIL
self-test becomes worthwhile. Stated as a limitation rather than implying full CI
functional coverage.
