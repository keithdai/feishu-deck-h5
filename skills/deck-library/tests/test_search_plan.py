import importlib.util
import argparse
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


class SearchPlanTests(unittest.TestCase):
    def test_search_selects_source_artifact_ref_for_reuse(self):
        search = load_module("search")

        self.assertIn("source_artifact_ref", search.SELECT_FIELDS)

    def test_search_uses_material_fields_for_agent_and_human_selection(self):
        search = load_module("search")

        self.assertIn("page_description", search.SEARCH_FIELDS)
        self.assertIn("material_id", search.SELECT_FIELDS)
        self.assertIn("material_code", search.SELECT_FIELDS)
        self.assertIn("thumbnail", search.SELECT_FIELDS)
        self.assertIn("slide_payload_json", search.SELECT_FIELDS)

    def test_search_filters_match_text_schema(self):
        search = load_module("search")
        args = argparse.Namespace(tag=["AI", "客户"], layout=["raw"], scene="客户提案", source="feishu-deck-h5", status="active")

        self.assertEqual(
            search.build_filter_json(args),
            {
                "logic": "and",
                "conditions": [
                    ["tags", "intersects", "AI"],
                    ["tags", "intersects", "客户"],
                    ["layout", "==", "raw"],
                    ["scene", "==", "客户提案"],
                    ["source", "==", "feishu-deck-h5"],
                    ["status", "==", "active"],
                ],
            },
        )

if __name__ == "__main__":
    unittest.main()
