# deck-library

`deck-library` is the landing folder for a reusable complete-deck and page
material library built around `feishu-deck-h5`, Feishu Base, and Feishu Drive.
`Decks` is the complete online deck registry; `Materials` is the page-level
material library.

## Status

This folder provides the MVP contract plus executable commands. Dry-run is the
safe default; `archive.py --write` can upsert Feishu Base Deck and Material
records, upload cloud-reusable deck artifacts, replace preview attachments when
local page screenshots exist, and `compose_materials.py --write` can compose
selected material IDs/codes into a rendered HTML deck.

## Folder Layout

```text
skills/deck-library/
├── SKILL.md
├── README.md
├── assets/
│   ├── archive.py
│   ├── check_links.py
│   ├── compose.py
│   ├── compose_materials.py
│   ├── deck_extract.py
│   ├── lark_base.py
│   ├── list_deck_materials.py
│   ├── migrate_schema.py
│   ├── preflight.py
│   ├── search.py
│   ├── search_decks.py
│   ├── update_deck_metadata.py
│   └── update_material_metadata.py
└── references/
    ├── base-schema.md
    └── workflows.md
```

## Quick Checks

```bash
python3 skills/deck-library/assets/preflight.py
python3 skills/deck-library/assets/archive.py runs/example/output --dry-run
python3 skills/deck-library/assets/archive.py runs/example/output --limit-slides 3 --dry-run
python3 skills/deck-library/assets/migrate_schema.py --dry-run
python3 skills/deck-library/assets/search_decks.py "客户提案 pitch deck" --dry-run
python3 skills/deck-library/assets/list_deck_materials.py deck_20260704_001 --dry-run
python3 skills/deck-library/assets/search.py "客户提案" --dry-run
python3 skills/deck-library/assets/update_deck_metadata.py deck_20260704_001 --set access_status=ready
python3 skills/deck-library/assets/update_material_metadata.py deck_20260704_001:M001 --set reuse_status=可直接复用
python3 skills/deck-library/assets/compose_materials.py M001 M002 --dry-run
python3 skills/deck-library/assets/check_links.py --dry-run
```

To perform real operations, pass explicit intent and configuration:

```bash
python3 skills/deck-library/assets/archive.py runs/example/output --write \
  --base-token <base_token> --decks-table <tbl_decks> --slides-table <tbl_slides>

python3 skills/deck-library/assets/migrate_schema.py --write \
  --base-token <base_token> --decks-table <tbl_decks> --materials-table <tbl_materials>

python3 skills/deck-library/assets/search_decks.py "客户提案 pitch deck" \
  --access-status ready \
  --base-token <base_token> --decks-table <tbl_decks>

python3 skills/deck-library/assets/list_deck_materials.py deck_20260704_001 \
  --base-token <base_token> --materials-table <tbl_materials>

python3 skills/deck-library/assets/search.py "客户提案" \
  --base-token <base_token> --materials-table <tbl_materials>

python3 skills/deck-library/assets/update_deck_metadata.py deck_20260704_001 \
  --set 中文名称=客户提案完整材料 \
  --set 中文描述=面向客户提案场景的完整H5演示材料 \
  --set online_url=https://example.com/deck \
  --set access_status=ready \
  --write \
  --base-token <base_token> --decks-table <tbl_decks>

python3 skills/deck-library/assets/update_material_metadata.py deck_20260704_001:M001 \
  --set reuse_status=可直接复用 \
  --set edit_notes=替换客户名后可复用 \
  --write \
  --base-token <base_token> --materials-table <tbl_materials>

python3 skills/deck-library/assets/compose_materials.py M001 M002 \
  --base-token <base_token> --materials-table <tbl_materials> \
  --decks-table <tbl_decks> \
  --output-dir runs/composed/output --write

python3 skills/deck-library/assets/compose_materials.py \
  --deck-id deck_20260704_001 \
  --page-role 封面 --page-role 案例 --page-role 收尾 \
  --base-token <base_token> --materials-table <tbl_materials> \
  --decks-table <tbl_decks> \
  --output-dir runs/composed-by-role/output --write

python3 skills/deck-library/assets/check_links.py --write \
  --base-token <base_token> --decks-table <tbl_decks>
```

## Implementation Direction

- `archive.py`: scan a deck output directory and write one Material record per page; use `--limit-slides` for smoke-test sampling.
- `archive.py`: generates `material_id`, `material_code`, `page_description`,
  and `slide_payload_json` so agents can search and compose without parsing large HTML.
- `archive.py`: reuses `output/pages/page-XX.jpg|jpeg|png` as per-slide thumbnails
  and uploads them to Base attachment fields after normal record upserts.
- `archive.py`: uploads `deck.json`, `index.html`, and `assets.zip` to Decks
  attachment fields so other teammates do not depend on the archiver's local path.
- `search_decks.py`: queries complete deck registry records in `Decks`, preferring
  directly usable `access_status=ready` materials with `online_url`.
- `list_deck_materials.py`: drills down from one `deck_id` to all page materials
  in source order.
- `search.py`: queries Materials by title, description, summary, visual summary,
  material ID/code, and slide key.
- `update_deck_metadata.py`: safely updates human-maintained Decks metadata such
  as `中文名称`, `中文描述`, `推荐用法`, `online_url`, `reuse_scope`, and `access_status`.
- `update_material_metadata.py`: safely updates human-maintained Materials metadata
  such as `素材描述`, `reuse_status`, and `edit_notes`.
- `compose_materials.py`: accepts material IDs/codes, fetches Material records,
  composes their `slide_payload_json`, downloads `Decks.assets_zip` from Base,
  restores required `assets/` and `pages/`, and renders HTML.
- `compose_materials.py`: can also select pages by `--deck-id` plus repeated
  `--page-role` values, preserving the source deck order.
- `migrate_schema.py`: creates missing operational fields/views and keeps
  Decks/Materials view order human-first.
- `check_links.py`: checks `Decks.online_url` and writes `link_health`,
  `链接状态`, `last_checked_at`, and `access_status=ready` when reachable.
- `compose.py`: merge local selected deck artifacts through `deck.json`, then render unless `--no-render` is set.
- `deck_extract.py`: extract slides by stable `slide_key` and preserve `lift_origin`.
- `lark_base.py`: build and execute explicit-profile `lark-cli base +...` commands.
- `preflight.py`: verify local renderer paths and optional `lark-cli` availability.

## Preview Fields

- `Decks.cover_thumbnail` is a Base attachment field for deck-level gallery cards.
- `Materials.thumbnail` is a Base attachment field for visual material picking.
- The sample Base includes `Deck Covers` and `Materials Gallery` gallery views whose
  card covers are bound to these attachment fields.
- Operational views should include complete deck states such as `可直接使用`,
  `待补链接`, and `测试样本`, plus material views such as `按Deck下钻`,
  `可直接复用页面`, and `代表页`.
- Attachment upload uses replace semantics: old files in the target attachment
  cell are removed before the latest artifact or thumbnail is uploaded.

## Reusable vs Provenance Fields

- Reusable fields: `deck_json`, `inline_html`, `assets_zip`, `cover_thumbnail`, `thumbnail`.
- Complete deck browsing fields: `中文名称`, `中文描述`, `online_url`, `适用场景`,
  `推荐用法`, `复用范围`, `链接状态`, plus technical aliases such as `recommended_use`.
- Search/compose fields: `material_id`, `material_code`, `page_description`, `slide_payload_json`.
- Provenance fields: `source_run_path` and any local `file://` path.
- Search and gallery views should expose reusable fields, not local provenance paths.
- Agents should ask for or return `material_code`/`material_id`; composition should
  use `slide_payload_json` first, and only use deck artifacts as dependency bundles.
- Metadata update commands must not mutate artifact fields such as `deck_json`,
  `inline_html`, `assets_zip`, `slide_payload_json`, `source_artifact_ref`, or
  `content_hash`; edit real content in `feishu-deck-h5`, validate, then archive again.

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
