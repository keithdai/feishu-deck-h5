# Deck Library Motion Quality Design

## Goal

Make `deck-library` outputs feel more like high-quality H5 decks by adding a reusable motion contract for `native_h5` delivery materials, without pretending screenshot replicas are native animated pages.

## Scope

This spec covers:

- Motion metadata in Materials and composed deck outputs.
- Safe CSS-only motion defaults for `native_h5` / `delivery` materials.
- No-motion behavior for `replica_screenshot` / `draft` materials.
- Verification of rendered and animated output using existing `feishu-deck-h5` gates.
- A two-slide XSD native H5 sample as the first proof.

This spec does not cover:

- Rebuilding all 36 XSD pages.
- Per-slide JavaScript animation slots.
- GSAP authoring inside material payloads.
- Full iframe/prototype animation preservation.

## Product Rule

Use the user's chosen policy: **high-quality default**.

- `native_h5` + `delivery` materials should ship with subtle CSS motion by default unless excluded for safety.
- `replica_screenshot` + `draft` materials should not receive motion by default.
- If a selected deck mixes native and screenshot materials, add motion only to eligible native pages and disclose the mixed quality.
- If the user asks for a premium/client-facing deck and selected materials are screenshots, propose a `native_h5` upgrade before motion.

## Motion Tiers

`motion_tier` defines how much motion a material carries:

- `none`: no bespoke motion. Default for `replica_screenshot` and unsafe pages.
- `subtle`: default for `native_h5` / `delivery`. Business-safe entrance and ambient effects.
- `expressive`: opt-in only when the user asks for a stronger technology feel.

`motion_notes` explains what moved and why. `has_motion` is true only when custom motion was applied and validated.

## Allowed Motion

Motion must be CSS-only and stored in `slide.custom_css`.

Allowed primitives:

- Title focus: blur/opacity reveal on title blocks.
- Stagger reveal: `.reveal` elements use `--i` ordering for cards, list rows, and panels.
- Ambient decor: slow pulse/rotate on decorative orbit/glow elements only.
- Emphasis pulse: restrained pulse on arrows, portals, or key transition symbols.
- Path/data grow: SVG lines or CSS bars grow into their final state when authored safely.

All motion must:

- Be scoped to `.slide-frame.is-current .slide[data-slide-key="<key>"]`.
- Be wrapped in `@media (prefers-reduced-motion: no-preference)`.
- Keep resting state visible and readable.
- Use unique keyframe names prefixed by the slide key or a stable slug.
- Avoid moving long body text continuously.

## Exclusions

Do not add default motion when:

- `material_type=replica_screenshot`.
- `quality_tier` is not `delivery`.
- The slide is iframe/prototype/live demo content.
- The page already has complex or fragile animation.
- Motion would create validator, geometry, overflow, or settled-frame failures.

In excluded cases, set `motion_tier=none` and write `motion_notes` with the reason.

## Composition Behavior

When composing materials:

- Preserve existing `custom_css` motion in `slide_payload_json`.
- Report `motion_summary` grouped by `motion_tier` and `has_motion`.
- Report `motion_warnings` when native delivery pages have no motion or when screenshots are selected for a premium output.
- Do not mutate archived payloads during ordinary composition.

## Native Upgrade Behavior

When upgrading a screenshot replica into native H5:

- Author the page as real HTML/CSS first.
- Pass `render-deck.py --final` with 0 errors and 0 warnings.
- Add subtle motion only after static layout passes.
- Capture mid and settled frames with `capture-frames.py`.
- Re-render and archive the upgraded material as `native_h5`, `delivery`, `has_motion=true`, `motion_tier=subtle`.

## XSD Proof

Use the existing XSD native sample:

- `native-toc`: title focus, three directory cards stagger reveal, background orbit ambient motion.
- `native-model-to-application`: header reveal, left/right panels stagger reveal, portal arrow pulse, right stack cards stagger reveal.

Success criteria:

- Output remains standard `deck.json`.
- `render-deck.py --final` returns 0.
- `capture-frames.py` returns 0 for both slide keys.
- Base compose of the archived native materials reports `native_h5`, `delivery`, `has_motion=true`, `motion_tier=subtle`, and no screenshot quality warning.

## Skill Contract Updates

Update `deck-library` so future agents:

- Disclose motion quality alongside material quality.
- Do not add motion to screenshot replicas by default.
- Treat motion as part of native H5 delivery quality.
- Verify motion using render and frame capture before claiming animated delivery.

## Risks

- CSS scoping can break if selectors omit `[data-slide-key]`.
- Animation can leave delayed elements hidden if `both` or final keyframes are wrong.
- Over-animated business decks can feel cheap.
- Capture-frame tooling may fail in some environments; if it does, the agent must report the limitation and not claim motion verification.
