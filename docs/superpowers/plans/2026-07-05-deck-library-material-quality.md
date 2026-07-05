# deck-library Material Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reusable material-quality metadata and export warnings to `deck-library` so screenshot replica materials are not mistaken for native H5 delivery assets.

**Architecture:** Keep the existing Base-backed archive/search/compose flow. Add quality classification during archive planning, fetch quality fields during composition, surface warnings in composed command output and `deck.json.notes`, and update Skill/schema docs so future agents disclose material fidelity.

**Tech Stack:** Python 3 standard library, `unittest`, Feishu Base via existing `lark_base.py`, `feishu-deck-h5` DeckJSON renderer.

## Global Constraints

- The main task is to improve a reusable `deck-library` Skill/workflow, not build a one-off export script.
- Do not rebuild selected pages into native H5 in this iteration.
- Do not parse arbitrary source HTML DOM into editable slides in this iteration.
- Do not improve the visual design of any single XSD page in this iteration.
- Existing compose behavior must still compose from `slide_payload_json` into renderer-compatible `deck.json`.
- Screenshot replica export must remain allowed by default, but must emit visible warnings.

---

## File Structure

- Modify `skills/deck-library/assets/archive.py`: classify archived slides and write `material_type`, `quality_tier`, and `fidelity_notes` into Material records.
- Modify `skills/deck-library/assets/compose_materials.py`: fetch quality fields, summarize them, warn on screenshot replicas, and update composed deck notes.
- Modify `skills/deck-library/SKILL.md`: teach future agents to disclose quality and propose native H5 upgrade for high-quality delivery.
- Modify `skills/deck-library/references/base-schema.md`: document new fields.
- Modify `skills/deck-library/tests/test_archive_plan.py`: cover replica and native classification.
- Modify `skills/deck-library/tests/test_compose_materials.py`: cover quality warning and no-warning paths.
- Modify `skills/deck-library/tests/test_skill_contract.py`: cover Skill contract wording.

---

### Task 1: Archive Material Quality Classification

**Files:**
- Modify: `skills/deck-library/assets/archive.py`
- Test: `skills/deck-library/tests/test_archive_plan.py`

**Interfaces:**
- Produces: `classify_material_quality(slide: dict[str, object]) -> dict[str, str]`
- Produces Material fields: `material_type`, `quality_tier`, `fidelity_notes`
- Consumes: existing `slide_records(deck_id, deck, output_dir)`

- [ ] **Step 1: Write failing tests**

Add these tests to `skills/deck-library/tests/test_archive_plan.py`:

```python
    def test_slide_records_mark_full_bleed_image_pages_as_replica_screenshot(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "page-08-demo",
                    "layout": "raw",
                    "data": {
                        "title": "模型到应用",
                        "html": '<section class="material-replica"><img class="material-image" src="pages/page-08.png" alt="模型到应用"></section>',
                    },
                    "custom_css": ".material-image{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}",
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["material_type"], "replica_screenshot")
        self.assertEqual(records[0]["quality_tier"], "draft")
        self.assertIn("截图", records[0]["fidelity_notes"])
        self.assertIn("native H5", records[0]["fidelity_notes"])

    def test_slide_records_mark_normal_raw_html_pages_as_native_h5(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "native-summary",
                    "layout": "raw",
                    "data": {
                        "title": "客户反馈总结",
                        "html": "<section><h1>客户反馈总结</h1><p>保留真实文本和布局。</p></section>",
                    },
                    "custom_css": "h1{font-size:48px}",
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["material_type"], "native_h5")
        self.assertEqual(records[0]["quality_tier"], "delivery")
        self.assertIn("真实 HTML/CSS", records[0]["fidelity_notes"])
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest skills/deck-library/tests/test_archive_plan.py
```

Expected: FAIL because `material_type`, `quality_tier`, and `fidelity_notes` are not present.

- [ ] **Step 3: Implement minimal classification**

In `skills/deck-library/assets/archive.py`, add:

```python
def is_full_bleed_image_replica(slide: dict[str, object]) -> bool:
    data = slide.get("data") if isinstance(slide.get("data"), dict) else {}
    html_value = data.get("html") if isinstance(data, dict) else ""
    if not isinstance(html_value, str):
        return False
    normalized = html_value.lower()
    return (
        "material-replica" in normalized
        and "<img" in normalized
        and "pages/page-" in normalized
    )


def classify_material_quality(slide: dict[str, object]) -> dict[str, str]:
    if is_full_bleed_image_replica(slide):
        return {
            "material_type": "replica_screenshot",
            "quality_tier": "draft",
            "fidelity_notes": "截图 replica 素材：适合快速预览和组合，正式交付前建议升级为 native H5。",
        }
    return {
        "material_type": "native_h5",
        "quality_tier": "delivery",
        "fidelity_notes": "真实 HTML/CSS 素材：保留文本、布局和样式层，可作为较高质量 H5 交付基础。",
    }
```

Then update `slide_records()` record construction:

```python
            quality_fields = classify_material_quality(slide)
```

and include:

```python
                    **quality_fields,
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest skills/deck-library/tests/test_archive_plan.py
```

Expected: PASS.

- [ ] **Step 5: Commit task**

Run:

```bash
git add skills/deck-library/assets/archive.py skills/deck-library/tests/test_archive_plan.py
git commit -m "feat(deck-library): classify material fidelity on archive"
```

---

### Task 2: Compose Quality Warnings

**Files:**
- Modify: `skills/deck-library/assets/compose_materials.py`
- Test: `skills/deck-library/tests/test_compose_materials.py`

**Interfaces:**
- Consumes Material fields: `material_type`, `quality_tier`, `fidelity_notes`
- Produces: `quality_summary(records: list[dict[str, Any]]) -> dict[str, Any]`
- Produces: `quality_warnings(records: list[dict[str, Any]]) -> list[str]`
- Updates: `build_deck_from_material_records(records, title)` notes behavior

- [ ] **Step 1: Write failing tests**

Add these tests to `skills/deck-library/tests/test_compose_materials.py`:

```python
    def test_quality_warnings_report_replica_screenshot_materials(self):
        compose_materials = load_module("compose_materials")
        records = [
            {
                "material_id": "deck_demo:M001",
                "material_code": "M001",
                "material_type": "replica_screenshot",
                "quality_tier": "draft",
                "fidelity_notes": "截图 replica 素材：适合快速预览。",
            },
            {
                "material_id": "deck_demo:M002",
                "material_code": "M002",
                "material_type": "native_h5",
                "quality_tier": "delivery",
                "fidelity_notes": "真实 HTML/CSS 素材。",
            },
        ]

        summary = compose_materials.quality_summary(records)
        warnings = compose_materials.quality_warnings(records)

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["by_material_type"]["replica_screenshot"], 1)
        self.assertEqual(summary["by_material_type"]["native_h5"], 1)
        self.assertEqual(summary["by_quality_tier"]["draft"], 1)
        self.assertTrue(any("M001" in warning for warning in warnings))
        self.assertTrue(any("native H5" in warning for warning in warnings))

    def test_quality_warnings_empty_for_all_native_materials(self):
        compose_materials = load_module("compose_materials")
        records = [
            {
                "material_id": "deck_demo:M002",
                "material_code": "M002",
                "material_type": "native_h5",
                "quality_tier": "delivery",
                "fidelity_notes": "真实 HTML/CSS 素材。",
            }
        ]

        self.assertEqual(compose_materials.quality_warnings(records), [])
```

Also update `test_build_deck_from_material_records_uses_slide_payload_json` records to include `material_type` and assert notes:

```python
        self.assertIn("Composed by deck-library", deck["notes"])
```

- [ ] **Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest skills/deck-library/tests/test_compose_materials.py
```

Expected: FAIL because `quality_summary` and `quality_warnings` do not exist.

- [ ] **Step 3: Implement minimal quality helpers**

In `skills/deck-library/assets/compose_materials.py`, extend `MATERIAL_SELECT_FIELDS`:

```python
    "material_type",
    "quality_tier",
    "fidelity_notes",
```

Add:

```python
def quality_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    by_material_type: dict[str, int] = {}
    by_quality_tier: dict[str, int] = {}
    for record in records:
        material_type = str(record.get("material_type") or "unknown")
        quality_tier = str(record.get("quality_tier") or "unknown")
        by_material_type[material_type] = by_material_type.get(material_type, 0) + 1
        by_quality_tier[quality_tier] = by_quality_tier.get(quality_tier, 0) + 1
    return {
        "total": len(records),
        "by_material_type": by_material_type,
        "by_quality_tier": by_quality_tier,
    }


def quality_warnings(records: list[dict[str, Any]]) -> list[str]:
    replica_codes = [
        str(record.get("material_code") or record.get("material_id") or "<unknown>")
        for record in records
        if record.get("material_type") == "replica_screenshot"
    ]
    if not replica_codes:
        return []
    return [
        "包含截图 replica 素材 "
        + ", ".join(replica_codes)
        + "；适合快速预览/草稿组合，正式客户交付前建议升级为 native H5。"
    ]
```

Update `build_deck_from_material_records()` notes:

```python
    warnings = quality_warnings(records)
    notes = "Composed by deck-library from Material records."
    if warnings:
        notes += " " + " ".join(warnings)
```

and return `"notes": notes`.

Update dry-run JSON and write-mode JSON to include:

```python
                    "quality_summary": quality_summary(records),
                    "quality_warnings": quality_warnings(records),
```

- [ ] **Step 4: Run tests to verify GREEN**

Run:

```bash
python3 -m unittest skills/deck-library/tests/test_compose_materials.py
```

Expected: PASS.

- [ ] **Step 5: Commit task**

Run:

```bash
git add skills/deck-library/assets/compose_materials.py skills/deck-library/tests/test_compose_materials.py
git commit -m "feat(deck-library): warn when composing replica materials"
```

---

### Task 3: Skill And Schema Contract

**Files:**
- Modify: `skills/deck-library/SKILL.md`
- Modify: `skills/deck-library/references/base-schema.md`
- Test: `skills/deck-library/tests/test_skill_contract.py`

**Interfaces:**
- Documents fields: `material_type`, `quality_tier`, `fidelity_notes`
- Documents behavior: disclose material quality in search handoff and compose results

- [ ] **Step 1: Write failing contract tests**

Add tests to `skills/deck-library/tests/test_skill_contract.py`:

```python
    def test_skill_requires_material_quality_disclosure(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("material_type", text)
        self.assertIn("quality_tier", text)
        self.assertIn("fidelity_notes", text)
        self.assertIn("replica_screenshot", text)
        self.assertIn("native_h5", text)
        self.assertIn("native H5", text)
```

- [ ] **Step 2: Run test to verify RED**

Run:

```bash
python3 -m unittest skills/deck-library/tests/test_skill_contract.py
```

Expected: FAIL because the Skill does not yet mention these fields and rules.

- [ ] **Step 3: Update Skill contract**

In `skills/deck-library/SKILL.md`, add a `## Material Quality` section after `## Material Description Contract`:

```markdown
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
```

Update search result guidance to include material quality:

```markdown
Search by need using the agent's own strategy, then present `material_code`,
`material_id`, `page_description`, `material_type`, `quality_tier`, and
thumbnail/Base gallery context so the user can pick visually.
```

- [ ] **Step 4: Update schema reference**

In `skills/deck-library/references/base-schema.md`, add rows after `visual_summary`:

```markdown
| `material_type` | Single select | Yes | `replica_screenshot` for image-only replicas, `native_h5` for real H5 slide content. |
| `quality_tier` | Single select | Yes | `draft`, `standard`, or `delivery`; screenshot replicas start as `draft`. |
| `fidelity_notes` | Long text | No | User-facing explanation of reuse limits and whether native H5 upgrade is recommended. |
```

Add storage/search note:

```markdown
- Search and compose responses should expose `material_type`, `quality_tier`, and
  `fidelity_notes` so screenshot replica materials are not mistaken for native H5.
```

- [ ] **Step 5: Run test to verify GREEN**

Run:

```bash
python3 -m unittest skills/deck-library/tests/test_skill_contract.py
```

Expected: PASS.

- [ ] **Step 6: Commit task**

Run:

```bash
git add skills/deck-library/SKILL.md skills/deck-library/references/base-schema.md skills/deck-library/tests/test_skill_contract.py
git commit -m "docs(deck-library): document material fidelity contract"
```

---

### Task 4: End-To-End Verification

**Files:**
- Read: `runs/deck-library-xsd-ai-business-export-check/output/deck.json`
- Modify only if tests reveal a defect: files from Tasks 1-3

**Interfaces:**
- Validates: archive classification tests, compose warning tests, Skill contract tests, full deck-library suite.

- [ ] **Step 1: Run full deck-library test suite**

Run:

```bash
python3 -m unittest discover -s skills/deck-library/tests -p 'test_*.py'
```

Expected: all tests pass.

- [ ] **Step 2: Compose a sample deck with known replica materials**

Run:

```bash
python3 skills/deck-library/assets/compose_materials.py \
  deck_xsd_ai_business_final_20260701:M002 \
  deck_xsd_ai_business_final_20260701:M008 \
  --title 'XSD AI Business 质量提示验证' \
  --write \
  --base-token JiPybKsQ6aItgfs2FGycq4Rqnfe \
  --decks-table tbltWglzO4Avgtqs \
  --materials-table tblQMAkChkqzEVsa \
  --output-dir runs/deck-library-quality-check/output
```

Expected:

- Command exits `0`.
- JSON output includes `quality_summary`.
- JSON output includes `quality_warnings` if Base rows have been backfilled with `material_type=replica_screenshot`.
- Render output reports `errors: 0` and `warnings: 0`.

- [ ] **Step 3: Inspect composed deck notes**

Run:

```bash
python3 - <<'PY'
import json
from pathlib import Path
deck = json.loads(Path('runs/deck-library-quality-check/output/deck.json').read_text(encoding='utf-8'))
print(deck.get('notes', ''))
PY
```

Expected: notes include `Composed by deck-library`; if selected Base records include replica metadata, notes also include the screenshot replica warning.

- [ ] **Step 4: Report residual risk**

Report:

- Existing already-archived Base rows may need a one-time backfill for `material_type`, `quality_tier`, and `fidelity_notes`.
- Newly archived materials will be classified automatically after Task 1.
- This iteration warns about quality; it does not block screenshot export or rebuild pages.

- [ ] **Step 5: Commit verification artifacts only if needed**

If no source/docs files changed after Task 3, do not commit generated `runs/` outputs.

---

## Self-Review

- Spec coverage: Tasks 1-3 implement quality fields, archive detection, compose warnings, Skill guidance, and schema docs. Task 4 verifies renderer compatibility and residual risk.
- Placeholder scan: no unresolved placeholder markers or unspecified test steps.
- Type consistency: `material_type`, `quality_tier`, `fidelity_notes`, `quality_summary()`, and `quality_warnings()` are consistently named across tasks.
- Scope check: plan stays within reusable `deck-library` Skill/workflow and explicitly excludes one-off visual reconstruction.
