import importlib.util
import json
import sys
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


class LarkBaseTests(unittest.TestCase):
    def test_record_upsert_command_uses_explicit_profile_identity_and_json(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblSlides",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_record_upsert_command(
            config=config,
            table_id="tblDecks",
            fields={"deck_id": "deck_1", "title": "Demo"},
        )

        self.assertEqual(
            command[:5],
            ["lark-cli", "--profile", "bytedance", "base", "+record-upsert"],
        )
        self.assertIn("--as", command)
        self.assertEqual(command[command.index("--as") + 1], "user")
        self.assertEqual(command[command.index("--base-token") + 1], "base123")
        self.assertEqual(command[command.index("--table-id") + 1], "tblDecks")
        self.assertEqual(
            json.loads(command[command.index("--json") + 1]),
            {"deck_id": "deck_1", "title": "Demo"},
        )

    def test_record_search_command_limits_results_and_projects_fields(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblSlides",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_record_search_command(
            config=config,
            table_id="tblSlides",
            keyword="客户提案",
            search_fields=["title", "content_summary"],
            select_fields=["slide_id", "title", "layout"],
            limit=8,
        )

        self.assertEqual(
            command[:5],
            ["lark-cli", "--profile", "bytedance", "base", "+record-search"],
        )
        self.assertEqual(command[command.index("--keyword") + 1], "客户提案")
        self.assertEqual(command.count("--search-field"), 2)
        self.assertEqual(command.count("--field-id"), 3)
        self.assertEqual(command[command.index("--limit") + 1], "8")
        self.assertEqual(command[command.index("--format") + 1], "json")

    def test_config_requires_base_and_table_ids_for_write_mode(self):
        lark_base = load_module("lark_base")

        errors = lark_base.BaseConfig(
            base_token="",
            decks_table="tblDecks",
            slides_table="",
            profile="bytedance",
            identity="user",
        ).validation_errors()

        self.assertEqual(errors, ["base_token is required", "slides_table is required"])

    def test_extract_single_record_id_returns_record_id_from_search_result(self):
        lark_base = load_module("lark_base")
        result = {
            "ok": True,
            "data": {
                "record_id_list": ["rec123"],
                "data": [["deck_1"]],
            },
        }

        self.assertEqual(lark_base.extract_single_record_id(result), "rec123")

    def test_extract_single_record_id_returns_none_when_not_found(self):
        lark_base = load_module("lark_base")
        result = {
            "ok": True,
            "data": {
                "record_id_list": [],
                "data": [],
            },
        }

        self.assertIsNone(lark_base.extract_single_record_id(result))

    def test_find_record_command_filters_by_business_key_with_record_list_filter(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblSlides",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_find_record_command(
            config=config,
            table_id="tblDecks",
            key_field="deck_id",
            key_value="deck_1",
        )

        self.assertIn("+record-list", command)
        self.assertNotIn("--keyword", command)
        body = json.loads(command[command.index("--filter-json") + 1])
        self.assertEqual(body, {"logic": "and", "conditions": [["deck_id", "==", "deck_1"]]})
        self.assertEqual(command[command.index("--field-id") + 1], "deck_id")
        self.assertEqual(command[command.index("--limit") + 1], "2")

    def test_find_record_command_uses_full_business_key_in_filter(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblSlides",
            profile="bytedance",
            identity="user",
        )
        long_value = "deck_vipshop_c_feedback_20260704:vipshop-pilot-cover"

        command = lark_base.build_find_record_command(
            config=config,
            table_id="tblSlides",
            key_field="slide_id",
            key_value=long_value,
        )

        body = json.loads(command[command.index("--filter-json") + 1])
        self.assertEqual(body["conditions"], [["slide_id", "==", long_value]])

    def test_material_lookup_command_matches_material_id_or_code(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblMaterials",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_material_lookup_command(
            config=config,
            table_id="tblMaterials",
            identifier="M001",
            select_fields=["material_id", "material_code", "slide_payload_json"],
        )

        self.assertIn("+record-list", command)
        body = json.loads(command[command.index("--filter-json") + 1])
        self.assertEqual(
            body,
            {
                "logic": "or",
                "conditions": [["material_id", "==", "M001"], ["material_code", "==", "M001"]],
            },
        )
        projected_fields = [command[index + 1] for index, value in enumerate(command) if value == "--field-id"]
        self.assertEqual(projected_fields, ["material_id", "material_code", "slide_payload_json"])
        self.assertEqual(command[command.index("--limit") + 1], "2")

    def test_list_materials_role_filter_uses_text_or_conditions(self):
        lark_base = load_module("lark_base")
        calls = []
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblMaterials",
            profile="bytedance",
            identity="user",
        )

        def fake_run_json(command):
            calls.append(command)
            return {"ok": True}

        lark_base.run_json = fake_run_json
        lark_base.list_materials(
            config,
            deck_id="deck_demo",
            page_roles=["封面", "案例"],
            select_fields=["material_id", "page_role"],
            limit=10,
        )

        body = json.loads(calls[0][calls[0].index("--filter-json") + 1])
        self.assertEqual(
            body,
            {
                "logic": "and",
                "conditions": [
                    ["deck_id", "==", "deck_demo"],
                    {"logic": "or", "conditions": [["page_role", "==", "封面"], ["page_role", "==", "案例"]]},
                ],
            },
        )

    def test_upload_attachment_command_appends_file_to_attachment_field(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblSlides",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_upload_attachment_command(
            config=config,
            table_id="tblSlides",
            record_id="rec123",
            field_id="thumbnail",
            files=["/tmp/page-01.jpg"],
        )

        self.assertEqual(
            command[:5],
            ["lark-cli", "--profile", "bytedance", "base", "+record-upload-attachment"],
        )
        self.assertEqual(command[command.index("--record-id") + 1], "rec123")
        self.assertEqual(command[command.index("--field-id") + 1], "thumbnail")
        self.assertEqual(command[command.index("--file") + 1], "/tmp/page-01.jpg")

    def test_remove_attachment_command_removes_existing_file_tokens(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblSlides",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_remove_attachment_command(
            config=config,
            table_id="tblSlides",
            record_id="rec123",
            field_id="thumbnail",
            file_tokens=["tok1", "tok2"],
        )

        self.assertEqual(command[:5], ["lark-cli", "--profile", "bytedance", "base", "+record-remove-attachment"])
        self.assertEqual(command.count("--file-token"), 2)
        self.assertIn("--yes", command)

    def test_download_attachment_command_downloads_selected_file_token(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblMaterials",
            profile="bytedance",
            identity="user",
        )

        command = lark_base.build_download_attachment_command(
            config=config,
            table_id="tblDecks",
            record_id="rec123",
            file_tokens=["tok1"],
            output="downloads/assets.zip",
            overwrite=True,
        )

        self.assertEqual(command[:5], ["lark-cli", "--profile", "bytedance", "base", "+record-download-attachment"])
        self.assertEqual(command[command.index("--record-id") + 1], "rec123")
        self.assertEqual(command[command.index("--file-token") + 1], "tok1")
        self.assertEqual(command[command.index("--output") + 1], "downloads/assets.zip")
        self.assertIn("--overwrite", command)

    def test_field_and_view_commands_support_schema_migration(self):
        lark_base = load_module("lark_base")
        config = lark_base.BaseConfig(
            base_token="base123",
            decks_table="tblDecks",
            slides_table="tblMaterials",
            profile="bytedance",
            identity="user",
        )

        field_command = lark_base.build_field_create_command(
            config=config,
            table_id="tblMaterials",
            field={"name": "复用状态", "type": "select", "multiple": False},
            dry_run=True,
        )
        visible_command = lark_base.build_view_set_visible_fields_command(
            config=config,
            table_id="tblMaterials",
            view_id="vewMain",
            visible_fields=["material_id", "thumbnail", "素材名称"],
        )
        filter_command = lark_base.build_view_set_filter_command(
            config=config,
            table_id="tblDecks",
            view_id="vewReady",
            filter_json={"logic": "and", "conditions": [["access_status", "intersects", ["ready"]]]},
        )

        self.assertIn("+field-create", field_command)
        self.assertEqual(json.loads(field_command[field_command.index("--json") + 1])["name"], "复用状态")
        self.assertIn("--dry-run", field_command)
        self.assertIn("+view-set-visible-fields", visible_command)
        self.assertEqual(
            json.loads(visible_command[visible_command.index("--json") + 1]),
            {"visible_fields": ["material_id", "thumbnail", "素材名称"]},
        )
        self.assertIn("+view-set-filter", filter_command)
        self.assertEqual(
            json.loads(filter_command[filter_command.index("--json") + 1])["conditions"],
            [["access_status", "intersects", ["ready"]]],
        )

    def test_extract_attachment_tokens_from_record_get_result(self):
        lark_base = load_module("lark_base")
        result = {
            "data": {
                "data": [
                    [[
                        {"file_token": "tok1", "name": "page-01.jpg"},
                        {"file_token": "tok2", "name": "page-02.jpg"},
                    ]]
                ]
            }
        }

        self.assertEqual(lark_base.extract_attachment_tokens(result), ["tok1", "tok2"])

    def test_extract_record_id_from_upsert_result_supports_common_shapes(self):
        lark_base = load_module("lark_base")

        self.assertEqual(lark_base.extract_upsert_record_id({"data": {"record_id": "rec1"}}), "rec1")
        self.assertEqual(lark_base.extract_upsert_record_id({"data": {"record": {"record_id": "rec2"}}}), "rec2")
        self.assertEqual(lark_base.extract_upsert_record_id({"record_id": "rec3"}), "rec3")

    def test_extract_record_id_from_upsert_result_supports_nested_record_id_list(self):
        lark_base = load_module("lark_base")
        result = {
            "data": {
                "created": True,
                "record": {
                    "record_id_list": ["rec4"],
                    "data": [["deck_1"]],
                },
            }
        }

        self.assertEqual(lark_base.extract_upsert_record_id(result), "rec4")

    def test_replace_attachment_uploads_new_file_before_removing_old_tokens(self):
        lark_base = load_module("lark_base")
        calls = []
        config = lark_base.BaseConfig(base_token="base", decks_table="tblDecks", slides_table="tblSlides")

        def fake_get_tokens(config, *, table_id, record_id, field_id):
            calls.append("get")
            return ["old-token"]

        def fake_upload(config, *, table_id, record_id, field_id, files):
            calls.append("upload")
            return {"ok": True}

        def fake_remove(config, *, table_id, record_id, field_id, file_tokens):
            calls.append("remove")
            self.assertEqual(file_tokens, ["old-token"])
            return {"ok": True}

        lark_base.get_attachment_tokens = fake_get_tokens
        lark_base.upload_attachment = fake_upload
        lark_base.remove_attachment = fake_remove

        result = lark_base.replace_attachment(
            config,
            table_id="tblDecks",
            record_id="rec1",
            field_id="deck_json",
            files=["runs/demo/output/deck.json"],
        )

        self.assertEqual(calls, ["get", "upload", "remove"])
        self.assertEqual(result["removed"], 1)


if __name__ == "__main__":
    unittest.main()
