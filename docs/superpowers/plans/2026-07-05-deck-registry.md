# Deck Registry Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `deck-library` from a page-material-only workflow into a two-layer library where `Decks` is the complete online deck registry and `Materials` is the page-level material library.

**Architecture:** Keep Feishu Base as the source of library metadata. Add deck-level search and deck-to-material drill-down commands while reusing `lark_base.py` command builders. Restrict metadata update commands to safe human-maintained fields and keep `deck_json`, `inline_html`, `assets_zip`, and `slide_payload_json` as artifact fields updated by archive flows.

**Tech Stack:** Python 3 standard library, `lark-cli`, Feishu Base, existing `unittest` suite.

## Global Constraints

- Do not build a required Miaoda page; `Decks` table is the complete deck library entry.
- Commands remain dry-run safe by default where they mutate data; real Base writes require `--write`.
- `Decks` stores complete online deck records; `Materials` stores one page per row.
- Base metadata may be adjusted in table rows, but source artifacts and payloads are updated through archive/render flows only.
- Do not touch the unrelated local `.diagram-drafts/` HTML drafts.

---

### Task 1: Deck Registry Schema And Docs

**Files:**
- Modify: `skills/deck-library/references/base-schema.md`
- Modify: `skills/deck-library/references/workflows.md`
- Modify: `skills/deck-library/SKILL.md`
- Test: `skills/deck-library/tests/test_skill_contract.py`

**Interfaces:**
- Consumes: Current `Decks` and `Materials` table definitions.
- Produces: Documented Deck Registry fields and agent workflow rules.

- [ ] **Step 1: Write contract tests**

Add assertions that `SKILL.md` names `Decks` as the complete deck library entry, says Miaoda is optional, and documents deck-to-material drill-down.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m unittest skills.deck-library.tests.test_skill_contract`
Expected: FAIL because the new contract text is missing.

- [ ] **Step 3: Update docs**

Update docs to add deck-level fields: `online_url`, `deck_type`, `recommended_use`, `reuse_scope`, `quality_tier`, `access_status`, `link_health`, `last_checked_at`, and `owner`.

- [ ] **Step 4: Run tests**

Run: `python3 -m unittest discover -s skills/deck-library/tests -p 'test_*.py'`
Expected: PASS.

### Task 2: Deck Search Command

**Files:**
- Modify: `skills/deck-library/assets/lark_base.py`
- Create: `skills/deck-library/assets/search_decks.py`
- Create: `skills/deck-library/tests/test_search_decks_plan.py`
- Modify: `skills/deck-library/tests/test_cli_safety.py`

**Interfaces:**
- Consumes: `lark_base.BaseConfig`, `lark_base.build_record_search_command()`.
- Produces: `search_decks.py` with `build_search_plan(args)` and CLI command.

- [ ] **Step 1: Write tests**

Test dry-run output includes `operation=search_decks`, deck search/select fields, `online_url`, `access_status`, and `recommended_use`. Test real search requires `base_token` and `decks_table`.

- [ ] **Step 2: Implement command**

Add deck search constants and CLI filters: `--scene`, `--deck-type`, `--tag`, `--quality-tier`, `--access-status`, `--reuse-scope`, `--limit`.

- [ ] **Step 3: Run targeted tests**

Run: `python3 -m unittest skills/deck-library/tests/test_search_decks_plan.py skills/deck-library/tests/test_cli_safety.py`
Expected: PASS.

### Task 3: Deck Materials Drill-Down Command

**Files:**
- Create: `skills/deck-library/assets/list_deck_materials.py`
- Create: `skills/deck-library/tests/test_list_deck_materials_plan.py`
- Modify: `skills/deck-library/tests/test_cli_safety.py`

**Interfaces:**
- Consumes: `lark_base.search_slides()`.
- Produces: CLI for listing all page materials under one `deck_id`.

- [ ] **Step 1: Write tests**

Test dry-run output includes `operation=list_deck_materials`, `deck_id`, filter on `deck_id`, `slide_index`, `material_code`, human fields, and `slide_payload_json`.

- [ ] **Step 2: Implement command**

Add CLI args: `deck_id`, `--status active`, `--include-hidden`, `--limit 100`, Base config flags.

- [ ] **Step 3: Run targeted tests**

Run: `python3 -m unittest skills/deck-library/tests/test_list_deck_materials_plan.py skills/deck-library/tests/test_cli_safety.py`
Expected: PASS.

### Task 4: Safe Metadata Update Commands

**Files:**
- Modify: `skills/deck-library/assets/lark_base.py`
- Create: `skills/deck-library/assets/update_deck_metadata.py`
- Create: `skills/deck-library/assets/update_material_metadata.py`
- Create: `skills/deck-library/tests/test_metadata_update_plan.py`
- Modify: `skills/deck-library/tests/test_cli_safety.py`

**Interfaces:**
- Consumes: `lark_base.build_record_upsert_command()`.
- Produces: safe update planners and `--write` commands.

- [ ] **Step 1: Write tests**

Test protected fields are rejected: `deck_json`, `inline_html`, `assets_zip`, `slide_payload_json`, `source_artifact_ref`, `content_hash`. Test allowed fields generate upsert plans.

- [ ] **Step 2: Implement deck metadata updater**

Allow only deck fields such as `title`, `online_url`, `scene`, `tags`, `deck_type`, `recommended_use`, `reuse_scope`, `quality_tier`, `access_status`, `link_health`, `last_checked_at`, `owner`, `status`.

- [ ] **Step 3: Implement material metadata updater**

Allow only material fields such as `素材名称`, `素材描述`, `适用场景`, `页面价值`, `视觉类型`, `关键词`, `tags`, `scene`, `quality_tier`, `reuse_status`, `edit_notes`, `status`.

- [ ] **Step 4: Run targeted tests**

Run: `python3 -m unittest skills/deck-library/tests/test_metadata_update_plan.py skills/deck-library/tests/test_cli_safety.py`
Expected: PASS.

### Task 5: README And Full Test

**Files:**
- Modify: `README.md`
- Modify: `skills/deck-library/SKILL.md`
- Modify: `skills/deck-library/references/workflows.md`

**Interfaces:**
- Consumes: New commands from Tasks 2-4.
- Produces: user-facing workflow: search complete decks, drill into pages, adjust metadata, compose.

- [ ] **Step 1: Update README usage**

Add command examples for `search_decks.py`, `list_deck_materials.py`, `update_deck_metadata.py`, and `update_material_metadata.py`.

- [ ] **Step 2: Run full tests**

Run: `python3 -m unittest discover -s skills/deck-library/tests -p 'test_*.py'`
Expected: PASS.

- [ ] **Step 3: Inspect git diff**

Run: `git status --short && git diff --stat`
Expected: only deck-library docs/tests/assets and README changes, plus existing untracked `.diagram-drafts/` ignored from commit decisions.
