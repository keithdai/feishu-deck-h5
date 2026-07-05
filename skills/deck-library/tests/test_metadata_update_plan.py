import importlib.util
import sys
import unittest
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


class MetadataUpdatePlanTests(unittest.TestCase):
    def test_deck_metadata_allows_only_registry_fields(self):
        update_deck = load_module("update_deck_metadata")
        parser = update_deck.build_parser()
        args = parser.parse_args(
            [
                "deck_20260704_001",
                "--set",
                "online_url=https://example.com/deck",
                "--set",
                "中文名称=客户提案完整材料",
                "--set",
                "access_status=ready",
                "--set",
                "recommended_use=完整客户提案参考",
            ]
        )

        plan = update_deck.build_update_plan(args)

        self.assertEqual(plan["operation"], "update_deck_metadata")
        self.assertEqual(plan["deck_id"], "deck_20260704_001")
        self.assertEqual(plan["fields"]["online_url"], "https://example.com/deck")
        self.assertEqual(plan["fields"]["中文名称"], "客户提案完整材料")
        self.assertEqual(plan["fields"]["access_status"], "ready")
        self.assertEqual(plan["write_requires"], ["base_token", "decks_table"])

    def test_deck_metadata_rejects_artifact_fields(self):
        update_deck = load_module("update_deck_metadata")

        with self.assertRaises(ValueError) as ctx:
            update_deck.parse_set_values(["deck_json=/tmp/deck.json"])

        self.assertIn("protected field", str(ctx.exception))

    def test_material_metadata_allows_only_human_fields(self):
        update_material = load_module("update_material_metadata")
        parser = update_material.build_parser()
        args = parser.parse_args(
            [
                "deck_20260704_001:M001",
                "--set",
                "reuse_status=可直接复用",
                "--set",
                "edit_notes=替换客户名后可复用",
            ]
        )

        plan = update_material.build_update_plan(args)

        self.assertEqual(plan["operation"], "update_material_metadata")
        self.assertEqual(plan["identifier"], "deck_20260704_001:M001")
        self.assertEqual(plan["fields"]["reuse_status"], "可直接复用")
        self.assertEqual(plan["fields"]["edit_notes"], "替换客户名后可复用")
        self.assertEqual(plan["write_requires"], ["base_token", "slides_table"])

    def test_material_metadata_parses_checkbox_fields_as_booleans(self):
        update_material = load_module("update_material_metadata")

        self.assertEqual(update_material.parse_set_values(["is_representative_page=true"])["is_representative_page"], True)
        self.assertEqual(update_material.parse_set_values(["is_representative_page=false"])["is_representative_page"], False)
        with self.assertRaises(ValueError):
            update_material.parse_set_values(["is_representative_page=maybe"])

    def test_material_metadata_rejects_payload_fields(self):
        update_material = load_module("update_material_metadata")

        with self.assertRaises(ValueError) as ctx:
            update_material.parse_set_values(["slide_payload_json={}"])

        self.assertIn("protected field", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
