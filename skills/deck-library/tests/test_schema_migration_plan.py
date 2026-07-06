import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "skills" / "deck-library" / "assets"


def load_module(name: str):
    sys.path.insert(0, str(ASSETS))
    spec = importlib.util.spec_from_file_location(name, ASSETS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class SchemaMigrationPlanTests(unittest.TestCase):
    def test_build_migration_plan_includes_material_views_and_operational_deck_views(self):
        migrate_schema = load_module("migrate_schema")

        plan = migrate_schema.build_migration_plan(
            base_token="base123",
            decks_table="tblDecks",
            materials_table="tblMaterials",
        )

        self.assertEqual(plan["operation"], "migrate_schema")
        self.assertNotIn("base_token", plan)
        self.assertEqual(plan["base_token_configured"], True)
        material_views = {view["name"]: view for view in plan["views"]["materials"]}
        deck_views = {view["name"]: view for view in plan["views"]["decks"]}
        self.assertIn("Grid View", material_views)
        self.assertIn("Slides Gallery", material_views)
        self.assertIn("Materials Gallery", material_views)
        self.assertIn("挑页｜按Deck", material_views)
        self.assertIn("挑页｜按行业", material_views)
        self.assertIn("挑页｜可复用", material_views)
        self.assertIn("表格", deck_views)
        self.assertIn("可直接使用", deck_views)
        self.assertIn("测试样本", deck_views)
        self.assertEqual(
            plan["visible_fields"]["materials"][0:8],
            ["thumbnail", "Deck中文名", "行业", "素材名称", "素材描述", "page_role", "reuse_status", "material_code"],
        )
        self.assertEqual(
            plan["visible_fields"]["decks"][0:8],
            ["cover_thumbnail", "中文名称", "行业", "中文描述", "适用场景", "推荐用法", "复用范围", "链接状态"],
        )
        self.assertTrue(any(field["name"] == "关联Deck" and field["type"] == "link" for field in plan["fields"]["materials"]))
        self.assertFalse(any(field["type"] == "lookup" for field in plan["fields"]["materials"]))
        self.assertIn("关联Deck", plan["visible_fields"]["materials"])
        deck_fields = {field["name"]: field for field in plan["fields"]["decks"]}
        material_fields = {field["name"]: field for field in plan["fields"]["materials"]}
        for field_name in ["online_url", "deck_type", "recommended_use", "reuse_scope", "last_checked_at", "owner"]:
            self.assertIn(field_name, deck_fields)
        for field_name in ["页面价值", "关键词", "edit_notes", "is_representative_page"]:
            self.assertIn(field_name, material_fields)
        self.assertEqual(deck_fields["适用场景"]["type"], "text")
        self.assertEqual(deck_fields["access_status"]["type"], "text")
        self.assertEqual(material_fields["reuse_status"]["type"], "text")
        self.assertEqual(material_fields["page_role"]["type"], "text")
        self.assertEqual(material_fields["is_representative_page"]["type"], "checkbox")
        self.assertEqual(deck_fields["行业"]["type"], "text")
        self.assertEqual(material_fields["行业"]["type"], "text")
        self.assertEqual(
            material_views["挑页｜按Deck"]["group"],
            {"group_config": [{"field": "Deck中文名", "desc": False}, {"field": "page_role", "desc": False}, {"field": "reuse_status", "desc": False}]},
        )
        self.assertEqual(
            material_views["挑页｜按行业"]["group"],
            {"group_config": [{"field": "行业", "desc": False}, {"field": "page_role", "desc": False}, {"field": "reuse_status", "desc": False}]},
        )
        self.assertEqual(material_views["挑页｜按Deck"]["sort"], [{"field": "Deck中文名", "desc": False}, {"field": "slide_index", "desc": False}])

    def test_noop_errors_are_reported_as_idempotent_success(self):
        migrate_schema = load_module("migrate_schema")

        result = migrate_schema.call_or_noop(lambda: (_ for _ in ()).throw(RuntimeError("no operation produced")))

        self.assertEqual(result["action"], "noop")
        self.assertIn("no operation produced", result["reason"])

    def test_migrate_schema_dry_run_prints_plan_without_configuration(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ASSETS / "migrate_schema.py"),
                "--dry-run",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["mode"], "dry-run")
        self.assertIn("fields", payload)


if __name__ == "__main__":
    unittest.main()
