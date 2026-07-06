import importlib.util
import json
import sys
import tempfile
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


class UploadArtifactsTests(unittest.TestCase):
    def test_build_artifact_items_prepares_all_deck_level_files(self):
        uploader = load_module("upload_artifacts")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            pages = output / "pages"
            pages.mkdir()
            (pages / "page-01.png").write_bytes(b"page")
            (output / "deck.json").write_text(
                json.dumps({"deck": {"title": "Demo"}, "slides": [{"key": "intro", "layout": "raw"}]}),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            items = uploader.build_artifact_items(output, "deck_demo")

        self.assertEqual([item.field_id for item in items], ["deck_json", "inline_html", "assets_zip"])
        self.assertEqual({item.key_value for item in items}, {"deck_demo"})
        self.assertTrue(str(items[2].local_path).endswith("assets.zip"))

    def test_upload_artifact_item_skips_existing_attachment_when_requested(self):
        uploader = load_module("upload_artifacts")
        calls = {"find": 0, "tokens": 0, "upload": 0}

        def fake_find_record_id(config, *, table_id, key_field, key_value):
            calls["find"] += 1
            return "recDeck"

        def fake_get_attachment_tokens(config, *, table_id, record_id, field_id):
            calls["tokens"] += 1
            return ["file_existing"]

        def fake_upload_attachment(*args, **kwargs):
            calls["upload"] += 1
            raise AssertionError("skip-existing should not upload an existing artifact")

        uploader.lark_base.find_record_id = fake_find_record_id
        uploader.lark_base.get_attachment_tokens = fake_get_attachment_tokens
        uploader.lark_base.upload_attachment = fake_upload_attachment
        config = uploader.lark_base.BaseConfig(
            base_token="base",
            decks_table="tblDecks",
            slides_table="tblSlides",
        )
        with tempfile.TemporaryDirectory() as tmp:
            local_path = Path(tmp) / "deck.json"
            local_path.write_text("{}", encoding="utf-8")
            item = uploader.ArtifactItem(
                kind="deck_artifact",
                key_field="deck_id",
                key_value="deck_demo",
                field_id="deck_json",
                local_path=local_path,
            )

            result = uploader.upload_artifact_item(config, item, skip_existing=True)

        self.assertEqual(calls, {"find": 1, "tokens": 1, "upload": 0})
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "attachment already exists")

    def test_prior_failed_keys_uses_latest_manifest_status_per_field(self):
        uploader = load_module("upload_artifacts")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.jsonl"
            manifest.write_text(
                "\n".join(
                    [
                        json.dumps({"field_id": "deck_json", "key_value": "deck_demo", "status": "failed"}),
                        json.dumps({"field_id": "deck_json", "key_value": "deck_demo", "status": "uploaded"}),
                        json.dumps({"field_id": "assets_zip", "key_value": "deck_demo", "status": "failed"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(uploader.prior_failed_keys(manifest), {("assets_zip", "deck_demo")})


if __name__ == "__main__":
    unittest.main()
