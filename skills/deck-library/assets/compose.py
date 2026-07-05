#!/usr/bin/env python3
"""Plan or compose selected archived slides into a new deck."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import deck_extract


def load_manifest(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if not isinstance(manifest, dict):
        raise ValueError("manifest must be a JSON object")
    slides = manifest.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("manifest.slides must be a non-empty array")
    for index, slide in enumerate(slides, start=1):
        if not isinstance(slide, dict):
            raise ValueError(f"manifest slide {index} must be an object")
        for field in ("slide_id", "deck_id", "slide_key"):
            if not slide.get(field):
                raise ValueError(f"manifest slide {index} is missing {field}")
    return manifest


def build_compose_plan(manifest_path: Path, output_dir: Path, renderer_root: Path) -> dict[str, object]:
    manifest = load_manifest(manifest_path)
    slides = manifest["slides"]
    title = manifest.get("title") or "Composed Deck"
    render_deck = renderer_root / "deck-json" / "render-deck.py"

    return {
        "mode": "dry-run",
        "operation": "compose",
        "title": title,
        "manifest": str(manifest_path),
        "output_dir": str(output_dir),
        "slide_count": len(slides),
        "planned_steps": [
            "download source deck.json and assets for each unique deck_id",
            "extract selected slides by slide_key",
            "write composed output/deck.json",
            f"render with {render_deck}",
            "run feishu-deck-h5 validation gate before delivery",
        ],
        "source_slides": slides,
    }


def default_renderer_root() -> Path:
    return Path(__file__).resolve().parents[2] / "feishu-deck-h5"


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan composing archived slides into a new deck.")
    parser.add_argument("--manifest", required=True, type=Path, help="JSON file listing selected slides.")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/deck-library-compose/output"))
    parser.add_argument("--renderer-root", type=Path, default=default_renderer_root())
    parser.add_argument("--dry-run", action="store_true", help="Print the compose plan without writing files.")
    parser.add_argument("--write", action="store_true", help="Write output/deck.json and render unless --no-render is set.")
    parser.add_argument("--no-render", action="store_true", help="With --write, only write deck.json.")
    args = parser.parse_args()

    if args.dry_run and args.write:
        print("compose.py: choose either --dry-run or --write, not both", file=sys.stderr)
        return 2

    try:
        plan = build_compose_plan(
            args.manifest.resolve(),
            args.output_dir,
            args.renderer_root.resolve(),
        )
    except Exception as exc:
        print(f"compose.py: {exc}", file=sys.stderr)
        return 1

    if not args.write:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    try:
        manifest = load_manifest(args.manifest.resolve())
        deck = deck_extract.build_composed_deck(manifest)
        deck_path = deck_extract.write_deck(deck, args.output_dir)
    except Exception as exc:
        print(f"compose.py: failed to write composed deck: {exc}", file=sys.stderr)
        return 1

    render_result: dict[str, object] | None = None
    if not args.no_render:
        render_deck = args.renderer_root.resolve() / "deck-json" / "render-deck.py"
        command = [sys.executable, str(render_deck), str(deck_path), str(args.output_dir), "--final"]
        completed = subprocess.run(command, check=False, capture_output=True, text=True)
        render_result = {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-4000:],
        }
        if completed.returncode != 0:
            print(f"compose.py: render failed with exit {completed.returncode}", file=sys.stderr)
            print(completed.stderr, file=sys.stderr)
            return completed.returncode

    print(
        json.dumps(
            {
                "mode": "write",
                "operation": "compose",
                "deck_json": str(deck_path),
                "slide_count": len(deck["slides"]),
                "render": render_result or "skipped",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
