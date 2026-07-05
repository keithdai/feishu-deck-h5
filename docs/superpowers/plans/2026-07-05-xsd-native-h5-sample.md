# XSD Native H5 Sample Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate that selected screenshot replica materials can be upgraded into real `native_h5` DeckJSON slides and published.

**Architecture:** Convert two source HTML pages from the XSD project into raw DeckJSON slides by extracting body markup and CSS, renaming reserved classes, scoping CSS to each slide key, copying only required assets, rendering with `render-deck.py --final`, and publishing the resulting HTML through the existing Magic Page publisher.

**Tech Stack:** Python 3 standard library, DeckJSON raw slides, `skills/feishu-deck-h5/deck-json/render-deck.py`, Magic Page publisher.

## Global Constraints

- This is a two-page proof, not a 36-page rebuild.
- Output must be standard `deck.json`; do not hand-assemble final `index.html`.
- Preserve the reusable Skill direction: document whether the path can become a `replica_screenshot -> native_h5` upgrade flow.
- Avoid framework reserved class collisions such as `.stage` and `.slide`.
- Run the renderer delivery gate before publishing.

---

### Task 1: Build Native H5 Sample Deck

- [ ] Generate `runs/deck-library-native-h5-xsd-sample/output/deck.json` with two raw slides: `native-toc` and `native-model-to-application`.
- [ ] Extract source HTML/CSS from the XSD `page-00-table-of-contents` and `page-03-ai-competition-second-half` pages.
- [ ] Rename reserved classes and scope CSS to each slide key.
- [ ] Copy required shared asset `assets/logos/feishu.svg`.

### Task 2: Render And Validate

- [ ] Run `render-deck.py <deck.json> <output-dir> --final`.
- [ ] Confirm 2 slides, 0 errors, and 0 warnings.
- [ ] Inspect generated `deck.json` to ensure each slide is `layout:"raw"` with real HTML/CSS, not a full-slide image.

### Task 3: Publish

- [ ] Publish the rendered HTML to Magic Page with the existing publisher.
- [ ] Record the URL and any publisher self-check caveat.

### Task 4: Report Skill Implications

- [ ] Report whether the native H5 upgrade path is viable.
- [ ] List what would need to become a reusable `deck-library` command or Skill section.
