# Deck Library Workflows

This document defines the MVP behavior for archive, complete deck registry
search, page material search, deck-to-material drill-down, compose, safe metadata
updates, and bulk ingest. Each flow stays compatible with `feishu-deck-h5` by
treating `deck.json` as the source of truth and rendered HTML as derived output.

## Schema Migration Flow

Input: target Base token plus Decks and Materials table IDs.

Steps:

1. Run `migrate_schema.py --dry-run` to review fields, views, filters, and visible-field order.
2. Run `migrate_schema.py --write` only after the Base/table IDs are unambiguous.
3. Create missing human/agent fields, including optional `关联Deck` for Materials.
4. Keep the writable text `deck_id` field as the automation key; do not destructively convert it into a link field.
5. Create or update operational views: `可直接使用`, `待补链接`, `测试样本`, `Materials Gallery`, `挑页｜按Deck`, `挑页｜按行业`, `挑页｜可复用`, `按Deck下钻`, `可直接复用页面`, and `代表页`.
6. Put thumbnails, `Deck中文名`, `page_role`, `reuse_status`, and `行业` before technical artifact fields.

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

For large PPT/H5 batches, prefer two-phase ingest:

1. Run `archive.py <output_dir> --metadata-only --write` to upsert Decks and
   Materials records without creating `assets.zip` or uploading attachments.
2. Run `upload_artifacts.py <output_dir> --deck-id <deck_id> --skip-existing
   --resume` to fill `Decks.deck_json`, `Decks.inline_html`, and
   `Decks.assets_zip`.
3. Run `upload_thumbnails.py <output_dir> --deck-id <deck_id> --skip-existing
   --resume` to fill `Decks.cover_thumbnail` and `Materials.thumbnail` from
   existing `pages/page-XX.*` files.
4. Keep the generated JSONL manifest and use `--retry-failed` for interrupted or
   flaky attachment batches.

Use `--limit-slides <N>` for smoke tests when the source deck is large. This
limits the generated plan and writes to the first N source slides without manually
copying or editing a temporary `deck.json`.

`upload_artifacts.py` and `upload_thumbnails.py` never create Decks or Materials
rows. They locate existing records by `deck_id` or `slide_id`, then upload or
replace attachment cells. Use `--skip-existing` when you only want to fill missing
attachments and avoid touching existing Base attachment tokens.

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

## Complete Deck Registry Flow

Input: a natural-language query plus optional deck-level filters.

The `Decks` table is the complete deck library entry. Miaoda is optional: the
registry can store Miaoda links, Magic Page links, Lark document links, or any
other stable online H5 URL in `online_url`, but a separate Miaoda page is not
required for the MVP.

Common filters:

- `--scene`
- `--deck-type`
- `--tag`
- `--quality-tier`
- `--access-status`
- `--reuse-scope`
- `--limit`

Steps:

1. Search `Decks` first when the user asks for complete pitch decks, complete
   H5 materials, examples, or directly usable online content.
2. Return `title`, `online_url`, `cover_thumbnail`, `deck_type`, `scene`, `tags`,
   `recommended_use`, `reuse_scope`, `quality_tier`, `access_status`,
   `link_health`, and `deck_id`.
3. Prefer `access_status=ready` when the user needs content that can be opened
   or reused immediately.
4. If the user wants to reuse pages from a complete deck, drill down from Decks
   to Materials by `deck_id`.
5. Only fall back to broad Materials search when no complete deck is a good fit
   or when the user explicitly asks for page-level materials.

## Deck-To-Materials Drill-Down Flow

Input: a `deck_id` from the Decks table.

Steps:

1. Query `Materials` where `deck_id` equals the selected complete deck.
2. Sort or present by `slide_index` so the source deck story remains visible.
3. Return human browsing fields first: `thumbnail`, `material_code`, `素材名称`,
   `素材描述`, `适用场景`, `页面价值`, `视觉类型`, `关键词`.
4. Return reuse decision fields: `material_type`, `quality_tier`, `reuse_status`,
   `edit_notes`, `page_role`, `is_representative_page`, `motion_tier`.
5. Keep technical fields available for composition: `slide_payload_json`,
   `source_artifact_ref`, `slide_key`, and `content_hash`.

The `Materials` table may expose `关联Deck` for manual relationship management,
while `deck_id` remains the stable automation key. Do not rely on default lookup
field creation for Deck title/link mirroring until the target Base proves lookup
filters are persisted correctly.

## Safe Metadata Update Flow

Input: a target record ID or business key plus user-maintained field updates.

Allowed Decks updates:

- `title`
- `online_url`
- `deck_type`
- `scene`
- `tags`
- `content_summary`
- `recommended_use`
- `reuse_scope`
- `quality_tier`
- `access_status`
- `link_health`
- `last_checked_at`
- `owner`
- `status`

Allowed Materials updates:

- `素材名称`
- `素材描述`
- `适用场景`
- `页面价值`
- `视觉类型`
- `关键词`
- `title`
- `page_description`
- `content_summary`
- `visual_summary`
- `tags`
- `scene`
- `quality_tier`
- `reuse_status`
- `edit_notes`
- `page_role`
- `is_representative_page`
- `status`

Protected fields must not be edited through metadata update commands:
`deck_json`, `inline_html`, `assets_zip`, `slide_payload_json`,
`source_artifact_ref`, and `content_hash`. To change real content, edit and
render with `feishu-deck-h5`, validate, then archive again.

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
Cloud-backed `source_artifact_ref` is the canonical team reuse anchor.
`compose_materials.py` resolves it to the related Decks row, downloads
`assets_zip`, and restores `assets/` plus `pages/` before rendering.

`compose_materials.py` supports two selection modes:

- Explicit material IDs/codes: `compose_materials.py M001 M008 M012 ...`.
- Story-slot selection: `compose_materials.py --deck-id <deck_id> --page-role 封面 --page-role 案例 ...`.

When selecting by role, query Materials by `deck_id` and optional `page_role`,
sort by `slide_index`, then compose from the returned `slide_payload_json`.

## Link Health Flow

Input: Decks rows with optional `online_url`.

Steps:

1. Run `check_links.py --dry-run` to confirm selected fields and update plan.
2. Query Decks records excluding deprecated entries.
3. Reject unsafe targets before probing: only `http`/`https` public URLs are checked; localhost/private IP targets are marked failed.
4. Check each safe `online_url` using HEAD with GET fallback.
5. Write machine status to `link_health` and `last_checked_at`.
6. Write human status to `链接状态`.
7. Set `access_status=ready` only when the URL is reachable, `broken` when a provided URL fails, and `draft` when no URL exists.
8. Update existing Decks records by `record_id`; do not create new records during link checks.

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
