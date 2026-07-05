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


if __name__ == "__main__":
    unittest.main()
