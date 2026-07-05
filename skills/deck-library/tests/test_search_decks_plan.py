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


class SearchDecksPlanTests(unittest.TestCase):
    def test_search_decks_selects_complete_deck_registry_fields(self):
        search_decks = load_module("search_decks")

        self.assertIn("online_url", search_decks.SELECT_FIELDS)
        self.assertIn("中文名称", search_decks.SELECT_FIELDS)
        self.assertIn("中文描述", search_decks.SELECT_FIELDS)
        self.assertIn("推荐用法", search_decks.SELECT_FIELDS)
        self.assertIn("cover_thumbnail", search_decks.SELECT_FIELDS)
        self.assertIn("recommended_use", search_decks.SELECT_FIELDS)
        self.assertIn("reuse_scope", search_decks.SELECT_FIELDS)
        self.assertIn("access_status", search_decks.SELECT_FIELDS)
        self.assertIn("link_health", search_decks.SELECT_FIELDS)

    def test_search_decks_plan_contains_filters_and_result_shape(self):
        search_decks = load_module("search_decks")
        parser = search_decks.build_parser()
        args = parser.parse_args(
            [
                "AI pitch deck",
                "--scene",
                "客户提案",
                "--deck-type",
                "pitch deck",
                "--tag",
                "AI",
                "--deck-id",
                "deck_20260704_001",
                "--quality-tier",
                "delivery",
                "--access-status",
                "ready",
                "--reuse-scope",
                "完整复用",
            ]
        )

        plan = search_decks.build_search_plan(args)

        self.assertEqual(plan["operation"], "search_decks")
        self.assertEqual(plan["base_filters"]["query"], "AI pitch deck")
        self.assertEqual(plan["base_filters"]["deck_id"], "deck_20260704_001")
        self.assertEqual(plan["base_filters"]["scene"], "客户提案")
        self.assertEqual(plan["base_filters"]["deck_type"], "pitch deck")
        self.assertEqual(plan["base_query"]["filter_json"]["logic"], "and")
        self.assertIn(["deck_id", "==", "deck_20260704_001"], plan["base_query"]["filter_json"]["conditions"])
        self.assertEqual(plan["result_shape"]["online_url"], "https://example.com/deck")
        self.assertIn("中文名称", plan["result_shape"])
        self.assertIn("中文描述", plan["result_shape"])
        self.assertEqual(plan["result_shape"]["access_status"], "ready")

    def test_search_decks_tag_filter_matches_text_schema(self):
        search_decks = load_module("search_decks")
        args = argparse.Namespace(
            tag=["AI", "客户"],
            deck_id=None,
            scene=None,
            deck_type=None,
            quality_tier=None,
            access_status="ready",
            reuse_scope=None,
            status=None,
        )

        self.assertEqual(
            search_decks.build_filter_json(args),
            {
                "logic": "and",
                "conditions": [
                    ["tags", "intersects", "AI"],
                    ["tags", "intersects", "客户"],
                    ["access_status", "==", "ready"],
                ],
            },
        )


if __name__ == "__main__":
    unittest.main()
