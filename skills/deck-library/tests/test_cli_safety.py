import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "skills" / "deck-library" / "assets"


class CliSafetyTests(unittest.TestCase):
    def test_archive_write_requires_base_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "deck.json").write_text(
                json.dumps({"title": "Demo", "slides": []}, ensure_ascii=False),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ASSETS / "archive.py"),
                    str(output),
                    "--write",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("base_token is required", completed.stderr)
        self.assertIn("slides_table is required", completed.stderr)

    def test_search_real_query_requires_base_configuration(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ASSETS / "search.py"),
                "客户提案",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 2)
        self.assertIn("base_token is required", completed.stderr)
        self.assertIn("slides_table is required", completed.stderr)

    def test_search_dry_run_still_prints_plan_without_configuration(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ASSETS / "search.py"),
                "客户提案",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["operation"], "search")
        self.assertEqual(payload["base_filters"]["query"], "客户提案")

    def test_compose_write_no_render_creates_deck_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.deck.json"
            source.write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "deck": {"title": "Source"},
                        "slides": [
                            {"key": "intro", "layout": "raw", "data": {"html": "<div>Intro</div>"}}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            manifest = root / "manifest.json"
            manifest.write_text(
                json.dumps(
                    {
                        "title": "Composed",
                        "slides": [
                            {
                                "slide_id": "deck_a:intro",
                                "deck_id": "deck_a",
                                "slide_key": "intro",
                                "source_deck_json": str(source),
                            }
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            output = root / "output"

            completed = subprocess.run(
                [
                    sys.executable,
                    str(ASSETS / "compose.py"),
                    "--manifest",
                    str(manifest),
                    "--output-dir",
                    str(output),
                    "--write",
                    "--no-render",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            deck = json.loads((output / "deck.json").read_text(encoding="utf-8"))
            self.assertEqual(deck["deck"]["title"], "Composed")
            self.assertEqual(deck["slides"][0]["key"], "intro")


if __name__ == "__main__":
    unittest.main()
