# Deck Library Motion Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a reusable motion quality contract to `deck-library` so `native_h5` delivery materials can carry safe CSS motion by default while screenshot replicas remain static.

**Architecture:** Extend archive planning and composition summaries with motion metadata, document the contract in `SKILL.md` and `base-schema.md`, then prove the flow by adding CSS-only motion to the existing XSD native H5 sample and re-archiving it. Keep motion in `slide.custom_css`; no per-slide JavaScript.

**Tech Stack:** Python 3 standard library, `unittest`, DeckJSON raw slides, `render-deck.py`, `capture-frames.py`, Feishu Base attachment workflow.

## Global Constraints

- `native_h5` + `delivery` materials should ship with subtle CSS motion by default unless excluded for safety.
- `replica_screenshot` + `draft` materials should not receive motion by default.
- Motion must be CSS-only and stored in `slide.custom_css`.
- Motion must be scoped to `.slide-frame.is-current .slide[data-slide-key="<key>"]`.
- Motion must be wrapped in `@media (prefers-reduced-motion: no-preference)`.
- Resting state must remain visible and readable.
- Ordinary composition must not mutate archived payloads.

---

### Task 1: Archive Motion Metadata

**Files:**
- Modify: `skills/deck-library/assets/archive.py`
- Modify: `skills/deck-library/tests/test_archive_plan.py`

**Interfaces:**
- Consumes: existing `classify_material_quality(slide: dict[str, object]) -> dict[str, str]`
- Produces: `classify_motion_quality(slide: dict[str, object], quality_fields: dict[str, str]) -> dict[str, object]`

- [x] **Step 1: Write failing tests**

Add tests asserting native delivery slides get `has_motion`, `motion_tier`, and `motion_notes`, while screenshot replicas get `none`.

- [x] **Step 2: Run red test**

Run: `python3 -m unittest skills/deck-library/tests/test_archive_plan.py`

Expected: FAIL because motion fields are missing.

- [x] **Step 3: Implement metadata**

Add `classify_motion_quality()` and merge its fields into each Material record:

```python
def classify_motion_quality(slide: dict[str, object], quality_fields: dict[str, str]) -> dict[str, object]:
    css = slide.get("custom_css") if isinstance(slide.get("custom_css"), str) else ""
    has_motion = "animation:" in css or "@keyframes" in css
    if quality_fields.get("material_type") != "native_h5" or quality_fields.get("quality_tier") != "delivery":
        return {
            "has_motion": False,
            "motion_tier": "none",
            "motion_notes": "截图或非交付素材默认不加动效；如需高级动效，先升级为 native H5。",
        }
    if has_motion:
        return {
            "has_motion": True,
            "motion_tier": "subtle",
            "motion_notes": "native H5 素材包含 CSS-only 动效，适合高质量 H5 交付。",
        }
    return {
        "has_motion": False,
        "motion_tier": "none",
        "motion_notes": "native H5 素材当前无 bespoke motion；可在高质量交付前添加 subtle CSS motion。",
    }
```

- [x] **Step 4: Run green test**

Run: `python3 -m unittest skills/deck-library/tests/test_archive_plan.py`

Expected: PASS.

- [x] **Step 5: Commit**

Run: `git add skills/deck-library/assets/archive.py skills/deck-library/tests/test_archive_plan.py && git commit -m "feat(deck-library): classify material motion quality"`

### Task 2: Compose Motion Summary

**Files:**
- Modify: `skills/deck-library/assets/compose_materials.py`
- Modify: `skills/deck-library/tests/test_compose_materials.py`

**Interfaces:**
- Consumes: `scalar_cell(value: Any, default: str = "unknown") -> str`
- Produces: `motion_summary(records: list[dict[str, Any]]) -> dict[str, Any]`
- Produces: `motion_warnings(records: list[dict[str, Any]]) -> list[str]`

- [x] **Step 1: Write failing tests**

Add tests for `motion_summary()` and `motion_warnings()`:

```python
records = [
    {"material_code": "M001", "material_type": ["native_h5"], "quality_tier": ["delivery"], "has_motion": True, "motion_tier": ["subtle"]},
    {"material_code": "M002", "material_type": ["replica_screenshot"], "quality_tier": ["draft"], "has_motion": False, "motion_tier": ["none"]},
]
```

Expected summary counts `subtle: 1`, `none: 1`, and warning mentions screenshot motion exclusion.

- [x] **Step 2: Run red test**

Run: `python3 -m unittest skills/deck-library/tests/test_compose_materials.py`

Expected: FAIL because motion helpers are missing.

- [x] **Step 3: Implement helpers and output fields**

Add `MATERIAL_FIELDS` entries `has_motion`, `motion_tier`, `motion_notes`. Add helper functions and include their output in dry-run/write JSON.

- [x] **Step 4: Run green test**

Run: `python3 -m unittest skills/deck-library/tests/test_compose_materials.py`

Expected: PASS.

- [x] **Step 5: Commit**

Run: `git add skills/deck-library/assets/compose_materials.py skills/deck-library/tests/test_compose_materials.py && git commit -m "feat(deck-library): summarize motion quality on compose"`

### Task 3: Skill And Schema Contract

**Files:**
- Modify: `skills/deck-library/SKILL.md`
- Modify: `skills/deck-library/references/base-schema.md`
- Modify: `skills/deck-library/tests/test_skill_contract.py`

**Interfaces:**
- Produces documented fields: `has_motion`, `motion_tier`, `motion_notes`

- [x] **Step 1: Write failing contract test**

Assert `SKILL.md` contains `has_motion`, `motion_tier`, `motion_notes`, `subtle`, `expressive`, and `prefers-reduced-motion`.

- [x] **Step 2: Run red test**

Run: `python3 -m unittest skills/deck-library/tests/test_skill_contract.py`

Expected: FAIL until docs are updated.

- [x] **Step 3: Update docs**

Add a `Motion Quality` section to `SKILL.md` and add the three fields to `base-schema.md`.

- [x] **Step 4: Run green test**

Run: `python3 -m unittest skills/deck-library/tests/test_skill_contract.py`

Expected: PASS.

- [x] **Step 5: Commit**

Run: `git add skills/deck-library/SKILL.md skills/deck-library/references/base-schema.md skills/deck-library/tests/test_skill_contract.py && git commit -m "docs(deck-library): document motion quality contract"`

### Task 4: XSD Native Motion Proof

**Files:**
- Modify generated artifact: `runs/deck-library-native-h5-xsd-sample/output/deck.json`
- Write Base records using: `skills/deck-library/assets/archive.py`

**Interfaces:**
- Consumes existing two-slide XSD native H5 sample.
- Produces archived materials under deck ID `deck_xsd_ai_business_native_h5_motion_sample_20260705`.

- [x] **Step 1: Add CSS-only motion to sample deck**

Add `.reveal` hooks and per-slide `@media (prefers-reduced-motion: no-preference)` animations to `native-toc` and `native-model-to-application`.

- [x] **Step 2: Render final**

Run: `python3 skills/feishu-deck-h5/deck-json/render-deck.py runs/deck-library-native-h5-xsd-sample/output/deck.json runs/deck-library-native-h5-xsd-sample/output --final`

Expected: PASS with 0 errors and 0 warnings.

- [x] **Step 3: Capture motion frames**

Run: `python3 skills/feishu-deck-h5/assets/capture-frames.py runs/deck-library-native-h5-xsd-sample/output/index.html native-toc native-model-to-application --settle-ms 4500`

Expected: PASS and frame images for both slide keys.

- [x] **Step 4: Archive to Base**

Run archive with deck ID `deck_xsd_ai_business_native_h5_motion_sample_20260705`.

- [x] **Step 5: Compose from Base**

Run `compose_materials.py` for the two new material IDs and confirm `motion_summary` reports `subtle: 2`, `has_motion: 2`, and no screenshot quality warning.

- [x] **Step 6: Run all tests and commit plan updates**

Run: `python3 -m unittest discover -s skills/deck-library/tests -p 'test_*.py'`

Expected: PASS.
