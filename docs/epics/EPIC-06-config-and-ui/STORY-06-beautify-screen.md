---
id: STORY-06
epic: EPIC-06
title: Beautify the screen
status: done
---

## Goal

Polish the setup/menu screen so it looks intentional and clean — consistent
spacing and alignment, a clear visual hierarchy (title → endpoint → options →
status → bottom bar), no leftover template clutter.

## Tasks

- [x] Define the final layout: header/title, endpoint (host/port), menu options, the minimal status block, and the bottom info bar
- [x] Consistent alignment + column spacing across the menu lines and labels
- [x] Clear visual grouping/separators so each section reads distinctly
- [x] Make the bottom bar and the `[E]`/`[X]`/`[H]`/`[P]`/`[S]` hints visually consistent
- [x] Verify it reads cleanly on real hardware at the ST resolution (320×200)

## Acceptance

The setup screen looks considered and readable on the ST — aligned, grouped, and
free of raw-template clutter.

## Notes

Builds on STORY-02 (menu + countdown bar) and STORY-05 (minimal status). The exact
look is to be pinned down with the user; this story is the placeholder to make the
screen tidy once the functional pieces are in.
