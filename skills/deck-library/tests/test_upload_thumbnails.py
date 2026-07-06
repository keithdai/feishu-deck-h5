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


class UploadThumbnailsTests(unittest.TestCase):
    def test_build_thumbnail_items_uses_archive_plan_paths_and_limit(self):
        uploader = load_module("upload_thumbnails")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            pages = output / "pages"
            pages.mkdir()
            (pages / "page-01.png").write_bytes(b"one")
            (pages / "page-02.png").write_bytes(b"two")
            (output / "deck.json").write_text(
                json.dumps(
                    {
                        "deck": {"title": "Demo"},
                        "slides": [
                            {"key": "intro", "layout": "raw", "data": {"title": "Intro"}},
                            {"key": "body", "layout": "raw", "data": {"title": "Body"}},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            items = uploader.build_thumbnail_items(output, "deck_demo", limit=1, include_cover=True)

        self.assertEqual([item.kind for item in items], ["deck_cover", "slide_thumbnail"])
        self.assertEqual(items[0].table_attr, "decks_table")
        self.assertEqual(items[0].key_field, "deck_id")
        self.assertEqual(items[0].key_value, "deck_demo")
        self.assertEqual(items[0].field_id, "cover_thumbnail")
        self.assertEqual(items[1].table_attr, "slides_table")
        self.assertEqual(items[1].key_field, "slide_id")
        self.assertEqual(items[1].key_value, "deck_demo:intro")
        self.assertEqual(items[1].field_id, "thumbnail")
        self.assertTrue(str(items[1].local_path).endswith("page-01.png"))

    def test_upload_thumbnail_item_skips_existing_attachment_when_requested(self):
        uploader = load_module("upload_thumbnails")
        calls = {"find": 0, "tokens": 0, "replace": 0}

        def fake_find_record_id(config, *, table_id, key_field, key_value):
            calls["find"] += 1
            return "recSlide"

        def fake_get_attachment_tokens(config, *, table_id, record_id, field_id):
            calls["tokens"] += 1
            return ["file_existing"]

        def fake_replace_attachment(*args, **kwargs):
            calls["replace"] += 1
            raise AssertionError("skip-existing should not replace an existing thumbnail")

        uploader.lark_base.find_record_id = fake_find_record_id
        uploader.lark_base.get_attachment_tokens = fake_get_attachment_tokens
        uploader.lark_base.replace_attachment = fake_replace_attachment
        config = uploader.lark_base.BaseConfig(
            base_token="base",
            decks_table="tblDecks",
            slides_table="tblSlides",
        )
        with tempfile.TemporaryDirectory() as tmp:
            thumbnail = Path(tmp) / "page-01.png"
            thumbnail.write_bytes(b"png")
            item = uploader.ThumbnailItem(
                kind="slide_thumbnail",
                table_attr="slides_table",
                key_field="slide_id",
                key_value="deck_demo:intro",
                field_id="thumbnail",
                local_path=thumbnail,
            )

            result = uploader.upload_thumbnail_item(config, item, skip_existing=True)

        self.assertEqual(calls, {"find": 1, "tokens": 1, "replace": 0})
        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "attachment already exists")
        self.assertEqual(result["record_id"], "recSlide")

    def test_upload_thumbnail_item_directly_uploads_when_skip_existing_finds_no_tokens(self):
        uploader = load_module("upload_thumbnails")
        calls = {"find": 0, "tokens": 0, "upload": 0, "replace": 0}

        def fake_find_record_id(config, *, table_id, key_field, key_value):
            calls["find"] += 1
            return "recSlide"

        def fake_get_attachment_tokens(config, *, table_id, record_id, field_id):
            calls["tokens"] += 1
            return []

        def fake_upload_attachment(config, *, table_id, record_id, field_id, files):
            calls["upload"] += 1
            return {"ok": True, "data": {"file_token": "file_new"}}

        def fake_replace_attachment(*args, **kwargs):
            calls["replace"] += 1
            raise AssertionError("skip-existing with no tokens should upload directly")

        uploader.lark_base.find_record_id = fake_find_record_id
        uploader.lark_base.get_attachment_tokens = fake_get_attachment_tokens
        uploader.lark_base.upload_attachment = fake_upload_attachment
        uploader.lark_base.replace_attachment = fake_replace_attachment
        config = uploader.lark_base.BaseConfig(
            base_token="base",
            decks_table="tblDecks",
            slides_table="tblSlides",
        )
        with tempfile.TemporaryDirectory() as tmp:
            thumbnail = Path(tmp) / "page-01.png"
            thumbnail.write_bytes(b"png")
            item = uploader.ThumbnailItem(
                kind="slide_thumbnail",
                table_attr="slides_table",
                key_field="slide_id",
                key_value="deck_demo:intro",
                field_id="thumbnail",
                local_path=thumbnail,
            )

            result = uploader.upload_thumbnail_item(config, item, skip_existing=True)

        self.assertEqual(calls, {"find": 1, "tokens": 1, "upload": 1, "replace": 0})
        self.assertEqual(result["status"], "uploaded")

    def test_upload_thumbnail_item_records_missing_base_record(self):
        uploader = load_module("upload_thumbnails")
        uploader.lark_base.find_record_id = lambda *args, **kwargs: None
        config = uploader.lark_base.BaseConfig(
            base_token="base",
            decks_table="tblDecks",
            slides_table="tblSlides",
        )
        with tempfile.TemporaryDirectory() as tmp:
            thumbnail = Path(tmp) / "page-01.png"
            thumbnail.write_bytes(b"png")
            item = uploader.ThumbnailItem(
                kind="slide_thumbnail",
                table_attr="slides_table",
                key_field="slide_id",
                key_value="deck_demo:intro",
                field_id="thumbnail",
                local_path=thumbnail,
            )

            result = uploader.upload_thumbnail_item(config, item, skip_existing=False)

        self.assertEqual(result["status"], "skipped")
        self.assertEqual(result["reason"], "record not found")
        self.assertEqual(result["key_value"], "deck_demo:intro")

    def test_prepare_cli_upload_path_stages_files_outside_current_directory(self):
        uploader = load_module("upload_thumbnails")
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "page-01.png"
            source.write_bytes(b"png")
            staging_dir = Path.cwd() / ".deck-library-cache/test-upload-thumbnails"

            upload_path = uploader.prepare_cli_upload_path(source, staging_dir=staging_dir)

        staged = Path.cwd() / upload_path
        self.assertTrue(upload_path.startswith(".deck-library-cache/test-upload-thumbnails/"))
        self.assertTrue(upload_path.endswith("/page-01.png"))
        self.assertTrue(staged.exists())
        self.assertEqual(staged.read_bytes(), b"png")
        staged.unlink()
        staged.parent.rmdir()

    def test_prior_failed_keys_uses_latest_manifest_status_per_item(self):
        uploader = load_module("upload_thumbnails")
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "manifest.jsonl"
            manifest.write_text(
                "\n".join(
                    [
                        json.dumps({"kind": "slide_thumbnail", "key_value": "deck:slide-001", "status": "failed"}),
                        json.dumps({"kind": "slide_thumbnail", "key_value": "deck:slide-001", "status": "uploaded"}),
                        json.dumps({"kind": "slide_thumbnail", "key_value": "deck:slide-002", "status": "failed"}),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            self.assertEqual(uploader.prior_failed_keys(manifest), {("slide_thumbnail", "deck:slide-002")})


if __name__ == "__main__":
    unittest.main()
