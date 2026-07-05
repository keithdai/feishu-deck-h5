import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ASSETS = Path(__file__).resolve().parents[1] / "assets"


def load_module(name: str):
    sys.path.insert(0, str(ASSETS))
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ComposeMaterialsTests(unittest.TestCase):
    def test_build_deck_from_material_records_uses_slide_payload_json(self):
        compose_materials = load_module("compose_materials")
        records = [
            {
                "material_id": "deck_demo:M001",
                "material_code": "M001",
                "slide_key": "intro",
                "material_type": "native_h5",
                "slide_payload_json": json.dumps({"key": "intro", "layout": "raw", "data": {"html": "<div>Intro</div>"}}),
            },
            {
                "material_id": "deck_demo:M002",
                "material_code": "M002",
                "slide_key": "plan",
                "material_type": "native_h5",
                "slide_payload_json": json.dumps({"key": "plan", "layout": "raw", "data": {"html": "<div>Plan</div>"}}),
            },
        ]

        deck = compose_materials.build_deck_from_material_records(records, "客户反馈材料")

        self.assertEqual(deck["deck"]["title"], "客户反馈材料")
        self.assertEqual([slide["key"] for slide in deck["slides"]], ["intro", "plan"])
        self.assertEqual(deck["slides"][0]["lifted"], "deck_demo:M001")
        self.assertEqual(deck["slides"][1]["lift_origin"]["material_code"], "M002")
        self.assertIn("Composed by deck-library", deck["notes"])

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

    def test_quality_warnings_accept_base_select_list_values(self):
        compose_materials = load_module("compose_materials")
        records = [
            {
                "material_id": "deck_demo:M001",
                "material_code": "M001",
                "material_type": ["replica_screenshot"],
                "quality_tier": ["draft"],
            }
        ]

        summary = compose_materials.quality_summary(records)
        warnings = compose_materials.quality_warnings(records)

        self.assertEqual(summary["by_material_type"]["replica_screenshot"], 1)
        self.assertEqual(summary["by_quality_tier"]["draft"], 1)
        self.assertTrue(any("M001" in warning for warning in warnings))

    def test_motion_summary_counts_motion_tiers_and_has_motion(self):
        compose_materials = load_module("compose_materials")
        records = [
            {
                "material_code": "M001",
                "material_type": ["native_h5"],
                "quality_tier": ["delivery"],
                "has_motion": True,
                "motion_tier": ["subtle"],
            },
            {
                "material_code": "M002",
                "material_type": ["replica_screenshot"],
                "quality_tier": ["draft"],
                "has_motion": False,
                "motion_tier": ["none"],
            },
        ]

        summary = compose_materials.motion_summary(records)

        self.assertEqual(summary["total"], 2)
        self.assertEqual(summary["with_motion"], 1)
        self.assertEqual(summary["by_motion_tier"]["subtle"], 1)
        self.assertEqual(summary["by_motion_tier"]["none"], 1)

    def test_motion_warnings_report_replica_motion_exclusion(self):
        compose_materials = load_module("compose_materials")
        records = [
            {
                "material_code": "M002",
                "material_type": ["replica_screenshot"],
                "quality_tier": ["draft"],
                "has_motion": False,
                "motion_tier": ["none"],
            }
        ]

        warnings = compose_materials.motion_warnings(records)

        self.assertTrue(any("M002" in warning for warning in warnings))
        self.assertTrue(any("截图" in warning for warning in warnings))

    def test_write_deck_creates_deck_json(self):
        compose_materials = load_module("compose_materials")
        deck = {"version": "1.0", "deck": {"title": "Demo"}, "slides": []}
        with tempfile.TemporaryDirectory() as tmp:
            path = compose_materials.write_deck(deck, Path(tmp))

            self.assertEqual(path, Path(tmp) / "deck.json")
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["deck"]["title"], "Demo")

    def test_copy_asset_roots_copies_pages_and_assets(self):
        compose_materials = load_module("compose_materials")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "source"
            output = Path(tmp) / "output"
            (source / "pages").mkdir(parents=True)
            (source / "assets").mkdir()
            (source / "pages" / "page-01.jpg").write_bytes(b"page")
            (source / "assets" / "style.txt").write_text("asset", encoding="utf-8")

            compose_materials.copy_asset_roots([source], output)

            self.assertEqual((output / "pages" / "page-01.jpg").read_bytes(), b"page")
            self.assertEqual((output / "assets" / "style.txt").read_text(encoding="utf-8"), "asset")

    def test_deck_ids_from_material_records_reads_base_source_refs(self):
        compose_materials = load_module("compose_materials")
        records = [
            {"source_artifact_ref": "base://deck/deck_alpha"},
            {"source_artifact_ref": "base://deck/deck_alpha"},
            {"source_artifact_ref": "base://deck/deck_beta"},
        ]

        self.assertEqual(compose_materials.deck_ids_from_material_records(records), ["deck_alpha", "deck_beta"])

    def test_extract_asset_zip_safely_restores_pages(self):
        compose_materials = load_module("compose_materials")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "assets.zip"
            output = Path(tmp) / "out"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("pages/page-01.jpg", b"page")

            compose_materials.extract_asset_zip(zip_path, output)

            self.assertEqual((output / "pages" / "page-01.jpg").read_bytes(), b"page")

    def test_extract_asset_zip_rejects_path_traversal(self):
        compose_materials = load_module("compose_materials")
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "assets.zip"
            output = Path(tmp) / "out"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../evil.txt", "bad")

            with self.assertRaises(ValueError):
                compose_materials.extract_asset_zip(zip_path, output)

    def test_download_asset_roots_fetches_deck_assets_zip(self):
        compose_materials = load_module("compose_materials")
        calls = []

        class FakeBase:
            decks_table = "tblDecks"

        def fake_find_record_id(config, *, table_id, key_field, key_value):
            calls.append(("find", table_id, key_field, key_value))
            return "recDeck"

        def fake_get_attachment_tokens(config, *, table_id, record_id, field_id):
            calls.append(("tokens", table_id, record_id, field_id))
            return ["tokAssets"]

        def fake_download_attachment(config, *, table_id, record_id, file_tokens, output, overwrite):
            calls.append(("download", table_id, record_id, file_tokens, output, overwrite))
            self.assertFalse(Path(output).is_absolute())
            with zipfile.ZipFile(output, "w") as archive:
                archive.writestr("pages/page-01.jpg", b"page")
            return {"ok": True}

        compose_materials.lark_base.find_record_id = fake_find_record_id
        compose_materials.lark_base.get_attachment_tokens = fake_get_attachment_tokens
        compose_materials.lark_base.download_attachment = fake_download_attachment

        with tempfile.TemporaryDirectory() as tmp:
            roots = compose_materials.download_asset_roots(
                FakeBase(),
                ["deck_demo"],
                Path(tmp),
            )

            self.assertEqual(len(roots), 1)
            self.assertEqual((roots[0] / "pages" / "page-01.jpg").read_bytes(), b"page")
            self.assertEqual(calls[0], ("find", "tblDecks", "deck_id", "deck_demo"))
            self.assertEqual(calls[1], ("tokens", "tblDecks", "recDeck", "assets_zip"))

if __name__ == "__main__":
    unittest.main()
