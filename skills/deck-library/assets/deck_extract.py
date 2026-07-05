#!/usr/bin/env python3
"""Extract selected slides from source deck.json files into a composed deck."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


def load_deck(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        deck = json.load(handle)
    if not isinstance(deck, dict):
        raise ValueError(f"{path} must contain a JSON object")
    slides = deck.get("slides")
    if not isinstance(slides, list):
        raise ValueError(f"{path} must contain a slides array")
    return deck


def source_path_for(selection: dict[str, Any]) -> Path:
    if selection.get("source_deck_json"):
        return Path(str(selection["source_deck_json"])).expanduser().resolve()
    ref = str(selection.get("source_artifact_ref") or "")
    if ref.startswith("file://"):
        return Path(ref.removeprefix("file://")).expanduser().resolve()
    if ref:
        raise ValueError(f"unsupported source_artifact_ref: {ref}")
    raise ValueError(f"manifest slide {selection.get('slide_id', '<unknown>')} is missing source_deck_json")


def extract_slide(selection: dict[str, Any]) -> dict[str, Any]:
    source_path = source_path_for(selection)
    deck = load_deck(source_path)
    wanted_key = str(selection["slide_key"])

    for index, slide in enumerate(deck["slides"], start=1):
        if isinstance(slide, dict) and slide.get("key") == wanted_key:
            extracted = copy.deepcopy(slide)
            deck_id = str(selection["deck_id"])
            extracted["lifted"] = f"{deck_id}#{wanted_key}"
            extracted["lift_origin"] = {
                "src_deck": deck_id,
                "src_path": str(source_path),
                "src_key": wanted_key,
                "src_index": index,
            }
            return extracted

    raise ValueError(f"slide_key {wanted_key} not found in {source_path}")


def build_composed_deck(manifest: dict[str, Any]) -> dict[str, Any]:
    title = str(manifest.get("title") or "Composed Deck")
    slides = manifest.get("slides")
    if not isinstance(slides, list) or not slides:
        raise ValueError("manifest.slides must be a non-empty array")

    return {
        "version": "1.0",
        "deck": {"title": title},
        "slides": [extract_slide(selection) for selection in slides],
        "notes": "Composed by deck-library from archived slide selections.",
    }


def write_deck(deck: dict[str, Any], output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    deck_path = output_dir / "deck.json"
    deck_path.write_text(
        json.dumps(deck, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return deck_path
