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


class ListDeckMaterialsPlanTests(unittest.TestCase):
    def test_list_deck_materials_selects_human_and_compose_fields(self):
        list_deck_materials = load_module("list_deck_materials")

        self.assertIn("material_code", list_deck_materials.SELECT_FIELDS)
        self.assertIn("素材名称", list_deck_materials.SELECT_FIELDS)
        self.assertIn("素材描述", list_deck_materials.SELECT_FIELDS)
        self.assertIn("slide_index", list_deck_materials.SELECT_FIELDS)
        self.assertIn("reuse_status", list_deck_materials.SELECT_FIELDS)
        self.assertIn("edit_notes", list_deck_materials.SELECT_FIELDS)
        self.assertIn("slide_payload_json", list_deck_materials.SELECT_FIELDS)

    def test_list_deck_materials_plan_filters_by_deck_id(self):
        list_deck_materials = load_module("list_deck_materials")
        parser = list_deck_materials.build_parser()
        args = parser.parse_args(["deck_20260704_001"])

        plan = list_deck_materials.build_list_plan(args)

        self.assertEqual(plan["operation"], "list_deck_materials")
        self.assertEqual(plan["deck_id"], "deck_20260704_001")
        self.assertEqual(
            plan["base_query"]["filter_json"],
            {
                "logic": "and",
                "conditions": [["deck_id", "==", "deck_20260704_001"], ["status", "==", "active"]],
            },
        )
        self.assertEqual(plan["base_query"]["sort_json"], [{"field": "slide_index", "desc": False}])
        self.assertEqual(plan["presentation_order"], "slide_index ascending")

    def test_include_hidden_removes_status_filter(self):
        list_deck_materials = load_module("list_deck_materials")
        parser = list_deck_materials.build_parser()
        args = parser.parse_args(["deck_20260704_001", "--include-hidden"])

        plan = list_deck_materials.build_list_plan(args)

        self.assertEqual(
            plan["base_query"]["filter_json"],
            {"logic": "and", "conditions": [["deck_id", "==", "deck_20260704_001"]]},
        )


if __name__ == "__main__":
    unittest.main()
