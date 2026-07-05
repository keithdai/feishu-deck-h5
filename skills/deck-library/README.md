# deck-library

`deck-library` is the landing folder for a reusable deck and slide material
library built around `feishu-deck-h5`, Feishu Base, and Feishu Drive.

## Status

This folder provides the MVP contract plus executable commands. Dry-run is the
safe default; `archive.py --write` can upsert Feishu Base Material records,
upload cloud-reusable deck artifacts, replace preview attachments when local
page screenshots exist, and `compose_materials.py --write` can compose selected
material IDs/codes into a rendered HTML deck.

## Folder Layout

```text
skills/deck-library/
├── SKILL.md
├── README.md
├── assets/
│   ├── archive.py
│   ├── compose.py
│   ├── compose_materials.py
│   ├── deck_extract.py
│   ├── lark_base.py
│   ├── preflight.py
│   └── search.py
└── references/
    ├── base-schema.md
    └── workflows.md
```

## Quick Checks

```bash
python3 skills/deck-library/assets/preflight.py
python3 skills/deck-library/assets/archive.py runs/example/output --dry-run
python3 skills/deck-library/assets/search.py "客户提案" --dry-run
python3 skills/deck-library/assets/compose_materials.py M001 M002 --dry-run
```

To perform real operations, pass explicit intent and configuration:

```bash
python3 skills/deck-library/assets/archive.py runs/example/output --write \
  --base-token <base_token> --decks-table <tbl_decks> --slides-table <tbl_slides>

python3 skills/deck-library/assets/search.py "客户提案" \
  --base-token <base_token> --materials-table <tbl_materials>

python3 skills/deck-library/assets/compose_materials.py M001 M002 \
  --base-token <base_token> --materials-table <tbl_materials> \
  --decks-table <tbl_decks> \
  --output-dir runs/composed/output --write
```

## Implementation Direction

- `archive.py`: scan a deck output directory and write one Material record per page.
- `archive.py`: generates `material_id`, `material_code`, `page_description`,
  and `slide_payload_json` so agents can search and compose without parsing large HTML.
- `archive.py`: reuses `output/pages/page-XX.jpg|jpeg|png` as per-slide thumbnails
  and uploads them to Base attachment fields after normal record upserts.
- `archive.py`: uploads `deck.json`, `index.html`, and `assets.zip` to Decks
  attachment fields so other teammates do not depend on the archiver's local path.
- `search.py`: queries Materials by title, description, summary, visual summary,
  material ID/code, and slide key.
- `compose_materials.py`: accepts material IDs/codes, fetches Material records,
  composes their `slide_payload_json`, downloads `Decks.assets_zip` from Base,
  restores required `assets/` and `pages/`, and renders HTML.
- `compose.py`: merge local selected deck artifacts through `deck.json`, then render unless `--no-render` is set.
- `deck_extract.py`: extract slides by stable `slide_key` and preserve `lift_origin`.
- `lark_base.py`: build and execute explicit-profile `lark-cli base +...` commands.
- `preflight.py`: verify local renderer paths and optional `lark-cli` availability.

## Preview Fields

- `Decks.cover_thumbnail` is a Base attachment field for deck-level gallery cards.
- `Materials.thumbnail` is a Base attachment field for visual material picking.
- The sample Base includes `Deck Covers` and `Materials Gallery` gallery views whose
  card covers are bound to these attachment fields.
- Attachment upload uses replace semantics: old files in the target attachment
  cell are removed before the latest artifact or thumbnail is uploaded.

## Reusable vs Provenance Fields

- Reusable fields: `deck_json`, `inline_html`, `assets_zip`, `cover_thumbnail`, `thumbnail`.
- Search/compose fields: `material_id`, `material_code`, `page_description`, `slide_payload_json`.
- Provenance fields: `source_run_path` and any local `file://` path.
- Search and gallery views should expose reusable fields, not local provenance paths.
- Agents should ask for or return `material_code`/`material_id`; composition should
  use `slide_payload_json` first, and only use deck artifacts as dependency bundles.

## Cloud Compose Flow

Default team reuse should not pass local paths:

```bash
python3 skills/deck-library/assets/compose_materials.py M001 M002 \
  --title "客户反馈分析材料" \
  --write \
  --base-token <base_token> \
  --decks-table <tbl_decks> \
  --materials-table <tbl_materials> \
  --output-dir runs/customer-feedback/output
```

The command resolves each Material's `source_artifact_ref`, downloads the related
`Decks.assets_zip` attachment into `.deck-library-cache/material-assets/`, extracts
the bundle, copies `assets/` and `pages/` into the output directory, then runs the
deck renderer. `--asset-root` remains available only for local development when
the artifact bundle has already been extracted.

## Non-Goals

- This skill does not generate new decks from scratch.
- This skill does not publish to Magic Page or Miaoda.
- This skill does not concatenate rendered HTML pages into a new deck.
