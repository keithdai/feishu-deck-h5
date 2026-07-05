# Deck Library Workflows

This document defines the MVP behavior for archive, search, compose, and bulk
ingest. Each flow stays compatible with `feishu-deck-h5` by treating `deck.json`
as the source of truth and rendered HTML as derived output.

## Archive Flow

Input: a deck output directory, usually `runs/<deck>/output/`.

Required files:

- `deck.json`
- `index.html`

Optional files:

- `assets/`
- existing page screenshots under `pages/page-XX.jpg|jpeg|png`

Steps:

1. Verify local renderer availability with `assets/preflight.py`.
2. Parse `deck.json` for deck metadata and slide records.
3. Compute a content hash from `deck.json` and the artifact manifest.
4. Prepare an inline/self-contained HTML artifact for preview.
5. Reuse existing page screenshots as cover and per-slide thumbnails.
6. Zip `assets/` into `assets.zip` when local assets exist.
7. Upload `deck.json`, `index.html`, `assets.zip`, and thumbnails to Base attachment fields.
8. Upsert the Decks record by `deck_id` or `content_hash`.
9. Upsert Slides records by `slide_id`, using `base://deck/<deck_id>` as `source_artifact_ref`.

MVP behavior: `--dry-run` prints the write plan as JSON; `--write` calls
`lark-cli base +record-upsert` for one deck record and its slide records after
explicit Base/table configuration is provided. Attachment fields are not written
as normal cell values; `cover_thumbnail` and `thumbnail` are uploaded through
`lark-cli base +record-upload-attachment` when matching local screenshots exist.
Reusable deck artifacts are also uploaded as Base attachments, while
`source_run_path` remains provenance only. Attachment upload uses replace
semantics, so repeated archive runs do not append duplicate files.

## Search Flow

Input: a natural-language query plus optional filters.

Common filters:

- `--tag`
- `--layout`
- `--scene`
- `--source`
- `--limit`

Steps:

1. Convert user intent into Base filters and a text query.
2. Retrieve matching slide/deck records from Base.
3. Rank locally by exact fields first: title, tag, layout, scene, slide key.
4. Return a compact shortlist with thumbnail references, Base attachment data,
   and `source_artifact_ref`.
5. Ask the user to confirm selected slides before composition.

MVP behavior: `--dry-run` prints the planned filter object and result shape;
without `--dry-run`, the command calls `lark-cli base +record-search` when a
Base token and Slides table are configured.

## Compose Flow

Input: a manifest that lists selected `slide_id` values in output order.

Manifest shape:

```json
{
  "title": "Composed Deck",
  "slides": [
    {
      "slide_id": "deck_20260704_001:intro",
      "deck_id": "deck_20260704_001",
      "slide_key": "intro",
      "source_deck_json": "/local/path/to/source/deck.json"
    }
  ]
}
```

Steps:

1. Download each source `deck.json` and its required assets.
2. Extract slides by stable `slide_key`, not by old label text.
3. Preserve provenance in each output slide under metadata fields.
4. Normalize style conflicts only when explicitly requested.
5. Write a new composed `deck.json`.
6. Render with `skills/feishu-deck-h5/deck-json/render-deck.py`.
7. Run the appropriate `feishu-deck-h5` validation gate before delivery.

MVP behavior: `--dry-run` validates manifest shape and prints planned render
steps; `--write` supports local `source_deck_json` or `file://...` references,
writes a composed `deck.json`, and renders unless `--no-render` is passed.
Cloud-backed `source_artifact_ref` is the canonical team reuse anchor, but
automatic attachment download/cache for compose is still a follow-up.

## Bulk Ingest Flow

Input: a parent `runs/` directory.

Steps:

1. Find candidate `output/deck.json` and `output/index.html` pairs.
2. Skip candidates with unchanged `content_hash`.
3. Archive each changed deck through the normal archive flow.
4. Report successes, skips, and failures separately.

## Failure Policy

- Missing `deck.json`: fail the archive flow; do not infer a source of truth from HTML.
- Missing `index.html`: report as render-needed and offer to run the renderer.
- Missing page screenshots: archive metadata still writes; preview attachment upload is skipped for those records.
- Missing renderer: fail preflight and ask the user to mount or install `feishu-deck-h5`.
- Attachment upload failure: keep the Base metadata write, record the failed upload reason, and continue other thumbnails.
- Large assets: prefer Base attachment for MVP; migrate to Drive URL references if attachment limits are exceeded.
- Mixed-style composition: warn and ask before applying a normalization pass.
- Unsupported Drive source refs: fail clearly until Drive download/cache support is implemented.
