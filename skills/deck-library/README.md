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
│   ├── update_material_metadata.py
│   ├── upload_artifacts.py
│   └── upload_thumbnails.py
└── references/
    ├── base-schema.md
    └── workflows.md
```

## Quick Checks

```bash
python3 skills/deck-library/assets/preflight.py
python3 skills/deck-library/assets/archive.py runs/example/output --dry-run
python3 skills/deck-library/assets/archive.py runs/example/output --limit-slides 3 --dry-run
python3 skills/deck-library/assets/archive.py runs/example/output --metadata-only --dry-run
python3 skills/deck-library/assets/upload_artifacts.py runs/example/output --deck-id deck_20260704_001 --dry-run
python3 skills/deck-library/assets/upload_thumbnails.py runs/example/output --deck-id deck_20260704_001 --dry-run
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

python3 skills/deck-library/assets/archive.py runs/example/output --metadata-only --write \
  --base-token <base_token> --decks-table <tbl_decks> --slides-table <tbl_slides>

python3 skills/deck-library/assets/upload_thumbnails.py runs/example/output \
  --deck-id deck_20260704_001 --skip-existing --resume --command-timeout 90 \
  --base-token <base_token> --decks-table <tbl_decks> --slides-table <tbl_slides>

python3 skills/deck-library/assets/upload_artifacts.py runs/example/output \
  --deck-id deck_20260704_001 --skip-existing --resume --command-timeout 180 \
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
- `archive.py --metadata-only`: write only Decks/Materials metadata and skip all
  artifact/thumbnail uploads. Use this first for large PPT/H5 batches so Base
  records become searchable even if attachment upload is slow.
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
- `upload_thumbnails.py`: uploads `Decks.cover_thumbnail` and
  `Materials.thumbnail` after metadata records already exist; supports
  `--skip-existing`, `--resume`, `--retry-failed`, `--command-timeout`, and a
  JSONL manifest for resumable large batches.
- `upload_artifacts.py`: uploads Deck-level reusable source attachments
  `deck_json`, `inline_html`, and `assets_zip` after metadata records already
  exist; supports the same skip/resume/retry pattern as thumbnail upload.
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
- `Decks.deck_json`, `Decks.inline_html`, and `Decks.assets_zip` are the reusable
  source package for compose/handoff; they are not normal text cells and must be
  written through attachment upload.
- The sample Base includes `Deck Covers` and `Materials Gallery` gallery views whose
  card covers are bound to these attachment fields.
- Operational views should include complete deck states such as `可直接使用`,
  `待补链接`, and `测试样本`, plus material picking views such as `挑页｜按Deck`,
  `挑页｜按行业`, `挑页｜可复用`, `按Deck下钻`, `可直接复用页面`, and `代表页`.
- Attachment upload uses replace semantics: old files in the target attachment
  cell are removed before the latest artifact or thumbnail is uploaded.
- Large archive runs should use two phases: first `archive.py --metadata-only
  --write`, then `upload_artifacts.py --skip-existing --resume` and
  `upload_thumbnails.py --skip-existing --resume`. This prevents slow attachment
  uploads from blocking searchable Decks/Materials records.

## Reusable vs Provenance Fields

- Reusable fields: `deck_json`, `inline_html`, `assets_zip`, `cover_thumbnail`, `thumbnail`.
- Complete deck browsing fields: `中文名称`, `中文描述`, `online_url`, `适用场景`,
  `推荐用法`, `复用范围`, `链接状态`, plus technical aliases such as `recommended_use`.
- Search/compose fields: `material_id`, `material_code`, `deck_id`, `Deck中文名`,
  `行业`, `page_role`, `reuse_status`, `page_description`, `slide_payload_json`.
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
the artifact bundle has already been extracted. The output is a `feishu-deck-h5`
HTML deck; exporting to a native `.pptx` is a separate downstream step.

## Non-Goals

- This skill does not generate new decks from scratch.
- This skill does not publish to Magic Page or Miaoda.
- This skill does not concatenate rendered HTML pages into a new deck.

## Q&A

**Q: `Decks` 和 `Materials` 分别解决什么问题？**

`Decks` 存完整 deck，用来找“这份材料能不能整体看、整体复用、有没有线上链接”。
`Materials` 存每一页，用来按页面角色、关键词、行业、场景检索和拆页复用。一个
`Decks.deck_id` 会对应多条 `Materials.deck_id`。`Materials.关联Deck` 是给人工浏览
用的 link 字段；自动化和组合流程以 `deck_id` 为稳定主键。

**Q: `Materials.Deck中文名` 是什么？为什么不只用 `关联Deck`？**

`Deck中文名` 是从 `Decks.中文名称` 冗余到每一页的文本字段，方便在 Materials 视图里
直接分辨页面来自哪份中文 deck，也方便搜索、筛选和导出。`关联Deck` 仍保留，用来在
Base UI 里跳转回完整 deck；两者不是互斥关系。

**Q: `行业` 字段怎么来？挑页时看哪个视图？**

`行业` 会优先按 `Deck中文名` 的行业后缀或关键词自动推断，例如 `医院 -> 医疗`、
`教育 -> 教育`、`制造 -> 制造`、`电商 -> 电商`、`汽车产业链 -> 汽车`。推断结果会同时
写入 `Decks.行业` 和 `Materials.行业`；没有命中规则的先标为 `未分类`，后续可人工修正。

挑页优先看 3 个 Materials 视图：`挑页｜按Deck` 按 `Deck中文名 -> page_role ->
reuse_status` 分组，适合从一份 deck 里拆页；`挑页｜按行业` 按 `行业 -> page_role ->
reuse_status` 分组，适合先找行业案例；`挑页｜可复用` 按 `reuse_status -> 行业 ->
page_role` 分组，适合快速找可直接复用页面。

**Q: 大批量 PPT/H5 入库为什么推荐先 `--metadata-only`？**

附件上传比记录写入慢，也更容易受路径、网络、Base 附件接口影响。`--metadata-only`
先保证 `Decks` 和 `Materials` 可搜索、可下钻、可组合；缩略图和 artifact 后续用
专门脚本补，不会阻塞主体入库。

**Q: 缩略图附件应该怎么补？**

先确保本地存在 `output/pages/page-XX.png|jpg|jpeg`，再跑：

```bash
python3 skills/deck-library/assets/upload_thumbnails.py <run-output-dir> \
  --deck-id <deck_id> \
  --skip-existing \
  --resume \
  --command-timeout 90 \
  --base-token <base_token> \
  --decks-table <tbl_decks> \
  --materials-table <tbl_materials>
```

脚本会上传 `Decks.cover_thumbnail` 和 `Materials.thumbnail`。`--skip-existing`
避免覆盖已有附件，`--resume` 会根据 manifest 跳过已成功项。

**Q: 素材包附件应该怎么补？**

素材包指 Decks 表里的 `deck_json`、`inline_html`、`assets_zip`。先确保本地
`output/deck.json`、`output/index.html`、`output/assets|pages` 存在，再跑：

```bash
python3 skills/deck-library/assets/upload_artifacts.py <run-output-dir> \
  --deck-id <deck_id> \
  --skip-existing \
  --resume \
  --command-timeout 180 \
  --base-token <base_token> \
  --decks-table <tbl_decks> \
  --materials-table <tbl_materials>
```

`assets_zip` 会由脚本从 `assets/` 和 `pages/` 重新打包。已有附件不会重复堆叠；
如果只补缺，用 `--skip-existing`。

**Q: 缩略图上传中断怎么办？**

保留同一个 manifest，再跑 `--retry-failed` 只补失败项：

```bash
python3 skills/deck-library/assets/upload_thumbnails.py <run-output-dir> \
  --deck-id <deck_id> \
  --retry-failed \
  --manifest <thumbnail-upload-manifest.jsonl> \
  --base-token <base_token> \
  --decks-table <tbl_decks> \
  --materials-table <tbl_materials>
```

如果只是继续未完成批次，用 `--resume`；如果只想重试失败项，用 `--retry-failed`。
如果单个附件命令长时间无返回，降低 `--command-timeout`，让该项写入 `failed`
后继续处理后面的缩略图。

**Q: 为什么缩略图脚本会创建 `.deck-library-cache/upload-thumbnails/`？**

`lark-cli` 的附件上传只接受当前工作目录内的安全路径。若源图片在另一个目录，脚本会
临时复制到 `.deck-library-cache/upload-thumbnails/<hash>/page-XX.png`，再把这个
相对路径交给 `lark-cli`。Base 里显示的附件名仍是干净的 `page-XX.png`。

**Q: `validation_status=validator_failed` 是不是表示不能入库？**

不是。它表示这份 H5 没有通过 `feishu-deck-h5` 的交付级 validator，仍可作为草稿、
案例索引或拆页素材参考。正式对外使用前，应回到 `deck.json` 修复视觉/规范问题并重新
归档。

**Q: `online_url` 为空时怎么使用完整 deck？**

`online_url` 为空表示还没有稳定线上访问地址。此时可以在 `Decks` 里先用中文名称、描述、
行业、标签检索完整 deck；需要线上浏览时，再通过发布流程生成地址并用
`update_deck_metadata.py` 写回 `online_url`、`access_status`、`链接状态`。

**Q: `source_run_path` 能不能当作可复用地址？**

不能。`source_run_path` 是归档来源和排障线索，只对当前机器可靠。跨团队复用应依赖
`deck_json`、`inline_html`、`assets_zip`、`cover_thumbnail`、`thumbnail` 这些 Base
附件字段，或稳定的 `online_url`。

**Q: 重复归档或重复上传会不会堆很多附件？**

`archive.py`、`upload_artifacts.py` 和 `upload_thumbnails.py` 都通过替换或跳过语义
避免附件无限堆叠。默认替换会先移除旧 token，再上传新文件；若只是补缺，不想碰已有
附件，使用 `--skip-existing`。

**Q: 如果我要组合生成一份 PPT，怎么操作？**

当前一等能力是组合生成新的 H5 deck：先在 `Materials` 按关键词、`Deck中文名`、页面角色
或 `material_code` 选页，再用 `compose_materials.py` 输出新的 `deck.json` 和 `index.html`。
如果需要原生 `.pptx`，应把这个 H5 deck 再交给独立 PPTX 导出链路；不要把当前 compose
理解成直接生成可编辑 PowerPoint。
