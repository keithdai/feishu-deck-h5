# deck-library Material Quality Design

## Goal

Make `deck-library` a reusable Skill/workflow for page-level material reuse, not a one-off export script for the XSD deck. The immediate improvement is to make material fidelity explicit so agents and humans know whether a composed deck is a fast screenshot replica or a high-quality native H5 deck.

## Problem

The current archive/compose loop works end to end, but screenshot-based materials are exported as valid `deck.json` slides that visually behave like full-slide images. This can mislead users into expecting native `feishu-deck-h5` quality: sharp text, live CSS layout, component-level styling, motion, and better Magic Page rendering. The Skill needs to preserve the fast replica path while clearly labeling its quality limits.

## Scope

This iteration stabilizes the reusable Skill contract:

- Add material fidelity fields to the library schema and Skill guidance.
- Detect image-only replica slides during archive planning.
- Include quality metadata in Material records.
- Include quality warnings in composed deck output and `deck.json.notes`.
- Keep the existing Base-backed archive, search, compose, render, and publish handoff flow intact.

This iteration does not rebuild selected pages into native H5, parse arbitrary source HTML DOM into editable slides, or improve the visual design of any single XSD page.

## Material Quality Model

Each Material should carry these concepts:

- `material_type`: stable machine-readable type such as `replica_screenshot` or `native_h5`.
- `quality_tier`: user-facing quality tier such as `draft`, `standard`, or `delivery`.
- `fidelity_notes`: concise explanation of reuse limits.

Initial classification:

- `replica_screenshot`: slide body is primarily one full-slide image such as `pages/page-08.png`; useful for fast preview, rough composition, and source reference.
- `native_h5`: slide body contains real HTML/CSS layout and text/components; suitable for higher-quality delivery after normal validation.

## Archive Behavior

`archive.py` should classify each slide while building Material records:

- If `data.html` contains a full-bleed image replica pattern, mark `material_type=replica_screenshot`.
- Otherwise mark `material_type=native_h5` by default.
- For `replica_screenshot`, set `quality_tier=draft` and explain that formal delivery should upgrade or rebuild the page as native H5.
- For `native_h5`, set `quality_tier=delivery` unless later validation adds a more nuanced tier.

## Compose Behavior

`compose_materials.py` should preserve existing composition behavior but surface quality:

- Select and compose from `slide_payload_json` exactly as today.
- Read material quality fields from Base.
- Add `quality_summary` to the command JSON output.
- Add `quality_warnings` when one or more selected materials are `replica_screenshot`.
- Add a concise `deck.json.notes` message when the composed deck contains draft replica pages.

The command should not block replica export by default. Warnings are enough for this iteration because fast screenshot composition is still a valid use case.

## Skill Contract

`skills/deck-library/SKILL.md` should teach future agents:

- The library can contain both fast replica materials and native H5 materials.
- Search results and user handoff should disclose material quality, not only thumbnail and material code.
- If the user asks for high-quality client delivery and selected materials are replicas, the agent should propose native H5 upgrade before publishing.
- Publishing a replica deck is allowed only when the user accepts it as quick preview, draft, or screenshot-based delivery.

## Tests

Add or update focused tests:

- `archive.py` classifies image-only full-slide pages as `replica_screenshot`.
- `archive.py` classifies normal raw HTML pages as `native_h5`.
- `compose_materials.py` includes quality warnings when selected records contain `replica_screenshot`.
- `compose_materials.py` emits no replica warning for all-native records.
- `SKILL.md` contract mentions material quality disclosure and native H5 upgrade guidance.

## Acceptance Criteria

- Existing archive and compose tests still pass.
- New tests prove screenshot replica detection and warning output.
- Composed `deck.json` remains renderer-compatible.
- The Skill remains about reusable material-library operation, not one-off visual reconstruction.
