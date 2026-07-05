---
name: deck-library
description: Use when a user wants to manage reusable Feishu deck page materials, search or visually pick slide/page素材 from a Base library, compose a new presentation from material numbers, or hand off/publish an HTML deck built from stored materials.
---

# deck-library

`deck-library` is the agent operating mode for a Feishu Base-backed page material
library. The main table is `Materials`: one row is one reusable page-level
material with a human/agent identifier, searchable material_description,
thumbnail, and the original low-level `deck.json` slide payload.

## Standalone Export Dependencies

`deck-library` can be exported as a standalone Skill, but it is an orchestration
layer and assumes the target environment already has the renderer Skill/toolchain:

- Required sibling Skill: `skills/feishu-deck-h5/`.
- Required renderer tools: `skills/feishu-deck-h5/deck-json/render-deck.py`,
  `skills/feishu-deck-h5/deck-json/deck-cli.py`, and
  `skills/feishu-deck-h5/assets/validate.py`.
- Required CLI: `lark-cli` with access to the target Feishu Base.
- Required Base schema: `Decks` and `Materials` tables matching
  `references/base-schema.md`, including attachment fields for `deck_json`,
  `inline_html`, `assets_zip`, `cover_thumbnail`, and `thumbnail`.
- Required configuration: pass flags explicitly or set
  `DECK_LIBRARY_BASE_TOKEN`, `DECK_LIBRARY_DECKS_TABLE`,
  `DECK_LIBRARY_SLIDES_TABLE`, and optionally `DECK_LIBRARY_LARK_PROFILE`.

If `feishu-deck-h5` is missing, this Skill may still document/archive/search
metadata, but it must not claim it can render or validate final H5 deliverables.

## When To Use

Use when the user asks to:

- Archive generated `feishu-deck-h5` pages into a reusable material library.
- Search reusable page materials by meaning, scene, title, description, or keywords.
- Return candidate material numbers for the user to review in Base thumbnails.
- Compose a new HTML presentation from material numbers such as `M001 M008`.
- Bulk ingest historical `runs/*/output/` decks into Feishu Base.

Do not use this skill for from-scratch deck generation. Use `feishu-deck-h5`
directly for new content creation, detailed page editing, validation, publishing,
or import after this skill has produced the composed `deck.json`/HTML handoff.

## Operating Model

- `Materials` is the primary human/agent table; `Decks` is the backend artifact table.
- `material_code` is the short human-facing selector, e.g. `M001`.
- `material_id` is the stable selector, e.g. `deck_demo:M001`.
- `page_description` / `material_description` is mandatory search text; do not rely on rendered HTML search.
- `thumbnail` is the visual preview field for Base gallery/manual picking.
- `slide_payload_json` is the reusable composition payload copied from `deck.json`.
- `source_artifact_ref` points to deck artifacts, usually `base://deck/<deck_id>`.
- `Decks.assets_zip` stores shared dependencies (`assets/` and `pages/`) for reuse.

## Material Description Contract

Agent owns search strategy. The skill does not prescribe one fixed search method:
the agent may use Base keyword search, field filters, gallery browsing, multiple
query rewrites, material codes supplied by the user, or its own retrieval plan.
The skill's job is to make every archived row easy for an agent or human to find.

Every Material row must have a searchable `material_description` (stored today as
`page_description`) that includes these parts when known:

- `scene`: the business/user scenario where this page is useful.
- `object`: the subject shown, such as customer feedback, AI meeting notes, VOC dashboard, action flow, or next-step plan.
- `value`: what the page helps explain or decide.
- `visual`: visible structure, e.g. cover, dashboard, timeline, table, workflow, comparison, case page.
- `keywords`: natural synonyms in Chinese and English when helpful, plus stable terms from the slide key.

For screenshot/replica pages, do not stop at `source slide 11`. Add a human
caption from the thumbnail or surrounding context before treating the material as
ready for reuse.

Store user-facing Chinese fields alongside technical fields. Required Chinese
fields are `素材名称`, `素材描述`, `适用场景`, `页面价值`, `视觉类型`, and `关键词`.
These fields are for humans browsing Base and for agents doing loose retrieval;
do not replace the stable technical fields such as `material_code`,
`page_description`, `slide_payload_json`, and `source_artifact_ref`.

## Material Quality

Material quality is part of the reusable Skill contract. Agents must disclose
quality when presenting candidates or composing a deck:

- `material_type=replica_screenshot`: a full-slide screenshot replica. It is good
  for fast preview, rough composition, and source reference, but it is not native
  H5 quality.
- `material_type=native_h5`: real HTML/CSS slide content that keeps text, layout,
  and styling layers available to the renderer.
- `quality_tier=draft` means the material is acceptable for quick preview or
  screenshot-based delivery only when the user accepts that tradeoff.
- `quality_tier=delivery` means the material is suitable as a delivery baseline
  after the normal `feishu-deck-h5` render/validation/publish gates.
- `fidelity_notes` should explain the practical reuse limit in user-facing terms.

If the user asks for high-quality client delivery and selected materials include
`replica_screenshot`, propose a native H5 upgrade before publishing. Do not present
a screenshot replica deck as if it has the same fidelity as a native H5 deck.

## Motion Quality

Motion quality is part of native H5 delivery quality, not a cosmetic afterthought:

- `has_motion=true` means the material contains validated CSS-only bespoke motion
  in `slide.custom_css`.
- `motion_tier=none` means no bespoke motion. This is the default for
  `replica_screenshot`, `draft`, iframe/live demo, or unsafe pages.
- `motion_tier=subtle` is the default target for `native_h5` + `delivery`
  materials: business-safe title focus, card stagger reveal, restrained pulse, or
  ambient decor.
- `motion_tier=expressive` is opt-in only when the user asks for stronger
  technology feel.
- `motion_notes` must explain what moves or why motion was excluded.

Motion must be CSS-only, scoped to `.slide-frame.is-current
.slide[data-slide-key="<key>"]`, wrapped in `@media (prefers-reduced-motion:
no-preference)`, and stored in `slide.custom_css`. Never add per-slide
`<script>` for motion. If a page is `replica_screenshot`, do not add default
motion; propose a native H5 upgrade first.

## Base View Layout

User-facing fields first. Materials views should put human browsing fields before
technical fields so the Base is easy to scan:

- Front: `thumbnail`, `material_code`, `素材名称`, `素材描述`, `适用场景`, `页面价值`, `视觉类型`, `关键词`.
- Search support: `page_description`, `title`, `scene`, `tags`, `visual_summary`, `content_summary`.
- Middle: `status`, `material_type`, `quality_tier`, `has_motion`, `motion_tier`, `material_id`, `slide_index`, `screen_label`, `layout`, `slide_key`.
- Technical fields last: `deck_id`, `source_artifact_ref`, `source`, `theme`, `accent`, `content_hash`, `slide_payload_json`.

Gallery views should use `thumbnail` as the card cover and show `material_code`
plus `素材名称` / `素材描述` near the top. The primary field may be forced first
by Base; if so, keep the user-facing fields immediately after it.

## Agent Workflow

Commands are dry-run safe by default. Real writes require explicit flags and
Base/table configuration.

Archive finished decks into reusable Materials:

```bash
python3 skills/deck-library/assets/archive.py <run-output-dir> --write \
  --base-token <base_token> \
  --decks-table <tbl_decks> \
  --materials-table <tbl_materials>
```

Search by need using the agent's own strategy, then present `material_code`,
`material_id`, `page_description`, `material_type`, `quality_tier`, and
`motion_tier`, plus thumbnail/Base gallery context so the user can pick visually.
`search.py` is only one helper, not the search strategy:

```bash
python3 skills/deck-library/assets/search.py "客户反馈 总结页" \
  --base-token <base_token> \
  --materials-table <tbl_materials>
```

Compose from the user's selected numbers/codes. This command reads
`slide_payload_json`, resolves `source_artifact_ref`, downloads `assets_zip`,
restores `assets/` and `pages/`, writes a new `deck.json`, and calls
`render-deck.py --final` to produce `index.html`:

```bash
python3 skills/deck-library/assets/compose_materials.py M001 M008 M012 \
  --title "客户反馈分析材料" \
  --write \
  --base-token <base_token> \
  --decks-table <tbl_decks> \
  --materials-table <tbl_materials> \
  --output-dir runs/composed/output
```

## Delivery And Publishing

- Default delivery is the rendered local HTML at `<output-dir>/index.html`.
- Before saying done, validate through `render-deck.py --final` output or the
  `feishu-deck-h5` validator; never hand-edit generated `index.html`.
- If the user asks for 发布, treat publishing as a separate handoff step: use the
  appropriate `feishu-deck-h5`, Magic Page, Miaoda, or Lark publishing workflow,
  then optionally write the share URL back to Base if requested.
- If the user only asks for composition/delivery, do not invent an online publish
  target; report the local HTML deliverable path.

## Hard Rules

- Never search or compose by parsing a large rendered `index.html`.
- Never hand-assemble final HTML from archived fragments.
- Always compose from `slide_payload_json` into `deck.json`.
- Always render with `skills/feishu-deck-h5/deck-json/render-deck.py`.
- Preserve `lift_origin`, `material_code`, `material_id`, and `source_artifact_ref`.
- Keep candidate search results small enough for review, usually 5-8 materials.
- Local paths are provenance only; reusable dependencies must come from Base
  attachments such as `assets_zip`.

## References

- `references/base-schema.md` defines the `Decks` and `Materials` fields.
- `references/workflows.md` defines archive, search, compose, and bulk ingest flows.
- `../feishu-deck-h5/SKILL.md` remains the rendering and validation authority.
