import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"


class SkillContractTests(unittest.TestCase):
    def test_skill_describes_material_agent_workflow(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("Use when", text)
        self.assertIn("Materials", text)
        self.assertIn("material_code", text)
        self.assertIn("page_description", text)
        self.assertIn("compose_materials.py", text)
        self.assertIn("assets_zip", text)
        self.assertIn("render-deck.py", text)
        self.assertIn("发布", text)

    def test_skill_requires_searchable_material_descriptions(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("Agent owns search strategy", text)
        self.assertIn("material_description", text)
        self.assertIn("scene", text)
        self.assertIn("object", text)
        self.assertIn("value", text)
        self.assertIn("visual", text)
        self.assertIn("keywords", text)

    def test_skill_requires_user_facing_fields_first(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("User-facing fields first", text)
        self.assertIn("thumbnail", text)
        self.assertIn("material_code", text)
        self.assertIn("page_description", text)
        self.assertIn("Technical fields last", text)

    def test_skill_requires_chinese_user_fields(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("素材名称", text)
        self.assertIn("素材描述", text)
        self.assertIn("适用场景", text)
        self.assertIn("页面价值", text)
        self.assertIn("视觉类型", text)
        self.assertIn("关键词", text)

    def test_skill_requires_material_quality_disclosure(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("material_type", text)
        self.assertIn("quality_tier", text)
        self.assertIn("fidelity_notes", text)
        self.assertIn("replica_screenshot", text)
        self.assertIn("native_h5", text)
        self.assertIn("native H5", text)

    def test_skill_requires_motion_quality_disclosure(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("has_motion", text)
        self.assertIn("motion_tier", text)
        self.assertIn("motion_notes", text)
        self.assertIn("subtle", text)
        self.assertIn("expressive", text)
        self.assertIn("prefers-reduced-motion", text)

    def test_skill_declares_standalone_export_dependencies(self):
        text = SKILL.read_text(encoding="utf-8")

        self.assertIn("Standalone Export Dependencies", text)
        self.assertIn("feishu-deck-h5", text)
        self.assertIn("lark-cli", text)
        self.assertIn("DECK_LIBRARY_BASE_TOKEN", text)
        self.assertIn("DECK_LIBRARY_DECKS_TABLE", text)
        self.assertIn("DECK_LIBRARY_SLIDES_TABLE", text)
        self.assertIn("base-schema.md", text)


if __name__ == "__main__":
    unittest.main()
