import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def load_module(name: str):
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class DeckExtractTests(unittest.TestCase):
    def test_build_composed_deck_extracts_slides_by_key_and_records_origin(self):
        deck_extract = load_module("deck_extract")
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "source.deck.json"
            source_path.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "deck": {"title": "Source Deck"},
                        "slides": [
                            {"key": "intro", "layout": "raw", "data": {"html": "<div>Intro</div>"}},
                            {"key": "stats", "layout": "raw", "data": {"html": "<div>Stats</div>"}},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest = {
                "title": "Composed Deck",
                "slides": [
                    {
                        "slide_id": "deck_a:stats",
                        "deck_id": "deck_a",
                        "slide_key": "stats",
                        "source_deck_json": str(source_path),
                    }
                ],
            }

            composed = deck_extract.build_composed_deck(manifest)

        self.assertEqual(composed["version"], "1.0")
        self.assertEqual(composed["deck"]["title"], "Composed Deck")
        self.assertEqual(len(composed["slides"]), 1)
        slide = composed["slides"][0]
        self.assertEqual(slide["key"], "stats")
        self.assertEqual(slide["data"]["html"], "<div>Stats</div>")
        self.assertEqual(slide["lifted"], "deck_a#stats")
        self.assertEqual(
            slide["lift_origin"],
            {
                "src_deck": "deck_a",
                "src_path": str(source_path.resolve()),
                "src_key": "stats",
                "src_index": 2,
            },
        )

    def test_build_composed_deck_fails_when_slide_key_is_missing(self):
        deck_extract = load_module("deck_extract")
        with tempfile.TemporaryDirectory() as tmp:
            source_path = Path(tmp) / "source.deck.json"
            source_path.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "deck": {"title": "Source Deck"},
                        "slides": [{"key": "intro", "layout": "raw", "data": {"html": "Intro"}}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest = {
                "title": "Broken",
                "slides": [
                    {
                        "slide_id": "deck_a:missing",
                        "deck_id": "deck_a",
                        "slide_key": "missing",
                        "source_deck_json": str(source_path),
                    }
                ],
            }

            with self.assertRaisesRegex(ValueError, "slide_key missing not found"):
                deck_extract.build_composed_deck(manifest)


if __name__ == "__main__":
    unittest.main()
