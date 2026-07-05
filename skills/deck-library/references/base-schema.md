# Deck Library Base Schema

The MVP uses Feishu Base as the searchable index and Feishu Drive as artifact
storage. Keep deck-level records separate from slide-level records so single-slide
search and composition remain reliable.

## Table: Decks

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `deck_id` | Text | Yes | Stable ID such as `deck_20260704_001`. |
| `title` | Text | Yes | Human-readable deck title. |
| `source` | Single select | Yes | `feishu-deck-h5`, `external-html`, `pptx-import`, `keynote-import`. |
| `scene` | Single select | No | Example: `客户提案`, `季度汇报`, `内训`, `产品发布`. |
| `tags` | Multi select | No | Controlled vocabulary for business domain and visual style. |
| `slide_count` | Number | Yes | Count from `deck.json.slides`. |
| `theme` | Text | No | Short palette/style summary, e.g. `dark-blue`. |
| `accent` | Text | No | Primary accent color if known. |
| `content_summary` | Long text | No | AI-generated abstract for coarse search. |
| `source_run_path` | Text | No | Original local path for provenance/debug only; not a reusable team artifact. |
| `content_hash` | Text | Yes | Hash of `deck.json` and artifact manifest for dedupe. |
| `validation_status` | Single select | Yes | `unknown`, `passed`, `warning`, `failed`. |
| `deck_json` | Attachment | Yes | Original source of truth; cloud-accessible reuse entry. |
| `assets_zip` | Attachment or URL | No | Zipped `assets/`; use Drive link when too large for Base attachment. |
| `inline_html` | Attachment or URL | Yes | Rendered preview/handoff HTML; cloud-accessible reuse entry. |
| `cover_thumbnail` | Attachment | No | First-slide thumbnail for gallery view. |
| `created_at` | Date | Yes | Archive time. |
| `created_by` | Person | No | User who archived the deck. |
| `version` | Number | Yes | Starts at `1`; increments on replacement. |
| `status` | Single select | Yes | `draft`, `final`, `archived`, `deprecated`. |

## Table: Materials

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `material_id` | Text | Yes | Stable material ID: `<deck_id>:<material_code>`. |
| `material_code` | Text | Yes | Short human-facing selector such as `M001`. |
| `素材名称` | Text | Yes | Chinese human-facing material name for Base browsing. |
| `素材描述` | Long text | Yes | Chinese material description for human browsing and agent search. |
| `适用场景` | Text | No | Chinese usage scenarios such as `客户汇报`, `售前方案`, `VOC 项目复盘`. |
| `页面价值` | Long text | No | Chinese explanation of what this page helps communicate or decide. |
| `视觉类型` | Text | No | Chinese visual type such as `封面`, `看板页`, `流程图`, `案例页`. |
| `关键词` | Text | No | Chinese/English keywords and synonyms for retrieval. |
| `slide_id` | Text | Yes | Stable ID: `<deck_id>:<slide_key>`. |
| `deck_id` | Link | Yes | Link to the Decks table. |
| `slide_key` | Text | Yes | Value from `data-slide-key` / `deck.json.slides[].key`. |
| `slide_index` | Number | Yes | 1-based frame index in the source deck. |
| `title` | Text | No | Visible slide title when available. |
| `page_description` | Long text | Yes | Searchable description; should mirror or complement `素材描述`. |
| `layout` | Single select | Yes | `raw`, `canvas`, `cover`, or schema layout name. |
| `screen_label` | Text | No | Stored for display only; not canonical page identity. |
| `tags` | Multi select | No | Slide-specific tags. |
| `scene` | Single select | No | Slide-specific usage scenario. |
| `content_summary` | Long text | No | Compact summary for search/ranking. |
| `visual_summary` | Long text | No | Visual description from screenshot or layout metadata. |
| `material_type` | Single select | Yes | `replica_screenshot` for image-only replicas, `native_h5` for real H5 slide content. |
| `quality_tier` | Single select | Yes | `draft`, `standard`, or `delivery`; screenshot replicas start as `draft`. |
| `fidelity_notes` | Long text | No | User-facing explanation of reuse limits and whether native H5 upgrade is recommended. |
| `has_motion` | Checkbox | No | True when the material has validated CSS-only bespoke motion in `slide.custom_css`. |
| `motion_tier` | Single select | No | `none`, `subtle`, or `expressive`; `subtle` is the default target for native H5 delivery materials. |
| `motion_notes` | Long text | No | User-facing explanation of what moves or why motion was excluded. |
| `theme` | Text | No | Palette/style summary inherited or overridden. |
| `accent` | Text | No | Slide accent color if known. |
| `thumbnail` | Attachment | No | Per-slide screenshot. |
| `slide_payload_json` | Long text | Yes | Low-level slide JSON copied from `deck.json`; compose from this, not rendered HTML. |
| `source_artifact_ref` | Text or URL | Yes | Stable reference such as `base://deck/<deck_id>`; do not store local paths here. |
| `content_hash` | Text | Yes | Hash of slide payload and dependencies. |
| `status` | Single select | Yes | `active`, `hidden`, `deprecated`. |

## Search Strategy

- Base filters handle coarse selection: status, source, scene, tags, layout, date.
- Text search handles Chinese fields, `page_description`, title, summaries, and slide keys.
- AI ranking receives only the top 5-8 candidates, including thumbnails and compact metadata.
- Later semantic search can add an embedding sidecar without changing the MVP tables.

## Storage Strategy

- Keep `deck.json` and `inline_html` on every deck record.
- Store `assets_zip` in Drive when it exceeds the practical Base attachment limit.
- Prefer per-slide thumbnails for search UX; cover thumbnail alone is only a deck-level fallback.
- Record `content_hash` before upload so repeated archive runs can skip duplicates.
- Treat `source_run_path` as provenance only; all team reuse should go through
  attachment fields or stable Base references.
- Attachment writes should replace old cell attachments before uploading new files
  to avoid duplicate previews after repeated archive runs.

## Reusable vs Provenance Fields

- Reusable fields: `deck_json`, `inline_html`, `assets_zip`, `cover_thumbnail`, `thumbnail`.
- Provenance fields: `source_run_path` and any local `file://` path.
- Search and gallery views should expose thumbnail, material code, Chinese description
  fields, and reusable fields, not local provenance paths.
- Search and compose responses should expose `material_type`, `quality_tier`, and
  `fidelity_notes` so screenshot replica materials are not mistaken for native H5.
- Search and compose responses should also expose `has_motion`, `motion_tier`, and
  `motion_notes` so animated native H5 materials are distinguishable from static ones.
- Compose may accept local paths for development fallback, but team reuse should
  download cloud attachments from the deck record referenced by `source_artifact_ref`.
