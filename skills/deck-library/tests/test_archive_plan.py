import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
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


class ArchivePlanTests(unittest.TestCase):
    def test_archive_plan_sets_searchable_default_status_fields(self):
        archive = load_module("archive")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "deck.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "deck": {"title": "Demo Deck"},
                        "slides": [
                            {"key": "intro", "layout": "raw", "data": {"title": "Intro", "html": "<div></div>"}}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            plan = archive.build_archive_plan(output, "deck_demo")

        self.assertEqual(plan["deck_record"]["status"], "archived")
        self.assertEqual(plan["deck_record"]["validation_status"], "unknown")
        self.assertEqual(plan["deck_record"]["access_status"], "draft")
        self.assertEqual(plan["deck_record"]["link_health"], "unknown")
        self.assertEqual(plan["deck_record"]["quality_tier"], "draft")
        self.assertEqual(plan["deck_record"]["reuse_scope"], "页面拆用")
        self.assertEqual(plan["deck_record"]["title"], "Demo Deck")
        self.assertEqual(plan["deck_record"]["中文名称"], "Demo Deck")
        self.assertIn("完整 H5 deck", plan["deck_record"]["中文描述"])
        self.assertIn("汇报材料", plan["deck_record"]["适用场景"])
        self.assertIn("下钻到 Materials", plan["deck_record"]["推荐用法"])
        self.assertEqual(plan["slide_records"][0]["status"], "active")
        self.assertEqual(plan["slide_records"][0]["content_summary"], "Intro")

    def test_archive_plan_uses_existing_page_snapshots_as_thumbnails(self):
        archive = load_module("archive")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            pages = output / "pages"
            pages.mkdir()
            (pages / "page-01.jpg").write_bytes(b"fake-jpg")
            (output / "deck.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "deck": {"title": "Demo Deck"},
                        "slides": [
                            {"key": "intro", "layout": "raw", "data": {"title": "Intro", "html": "<div></div>"}}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            plan = archive.build_archive_plan(output, "deck_demo")

        self.assertEqual(plan["deck_record"]["cover_thumbnail"], str(pages / "page-01.jpg"))
        self.assertEqual(plan["slide_records"][0]["thumbnail"], str(pages / "page-01.jpg"))

    def test_archive_plan_can_limit_slides_for_smoke_tests(self):
        archive = load_module("archive")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            (output / "deck.json").write_text(
                json.dumps(
                    {
                        "version": "1.0",
                        "deck": {"title": "Demo Deck"},
                        "slides": [
                            {"key": "intro", "layout": "raw", "data": {"title": "Intro", "html": "<div></div>"}},
                            {"key": "body", "layout": "raw", "data": {"title": "Body", "html": "<div></div>"}},
                            {"key": "end", "layout": "raw", "data": {"title": "End", "html": "<div></div>"}},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            plan = archive.build_archive_plan(output, "deck_demo", limit_slides=2)

        self.assertEqual(plan["deck_record"]["slide_count"], 2)
        self.assertEqual([record["material_code"] for record in plan["slide_records"]], ["M001", "M002"])
        self.assertEqual(plan["planned_writes"]["feishu_base_slides"], 2)

    def test_archive_plan_marks_deck_artifacts_as_attachment_sources(self):
        archive = load_module("archive")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo" / "output"
            output.mkdir(parents=True)
            (output / "deck.json").write_text(
                json.dumps({"slides": [{"key": "intro", "layout": "raw"}]}),
                encoding="utf-8",
            )
            (output / "index.html").write_text("<html></html>", encoding="utf-8")

            plan = archive.build_archive_plan(output, "deck_demo")

        self.assertEqual(plan["deck_record"]["deck_json"], str(output / "deck.json"))
        self.assertEqual(plan["deck_record"]["inline_html"], str(output / "index.html"))
        self.assertEqual(plan["deck_record"]["source_run_path"], str(output))
        self.assertEqual(plan["artifact_files"]["deck_json"], str(output / "deck.json"))
        self.assertEqual(plan["artifact_files"]["inline_html"], str(output / "index.html"))
        self.assertIsNone(plan["artifact_files"]["assets_zip"])

    def test_prepare_artifacts_zips_assets_directory_for_upload(self):
        archive = load_module("archive")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "demo" / "output"
            assets = output / "assets"
            pages = output / "pages"
            assets.mkdir(parents=True)
            pages.mkdir()
            (assets / "image.txt").write_text("asset", encoding="utf-8")
            (pages / "page-01.jpg").write_bytes(b"page")
            artifact_files = {
                "deck_json": str(output / "deck.json"),
                "inline_html": str(output / "index.html"),
                "assets_zip": str(output / "assets.zip"),
            }

            prepared = archive.prepare_artifacts_for_upload(output, artifact_files)

            self.assertEqual(prepared["assets_zip"], str(output / "assets.zip"))
            self.assertTrue((output / "assets.zip").exists())
            with zipfile.ZipFile(output / "assets.zip") as archive_zip:
                self.assertEqual(archive_zip.namelist(), ["assets/image.txt", "pages/page-01.jpg"])

    def test_base_write_records_exclude_attachment_fields(self):
        archive = load_module("archive")

        deck_record = archive.record_without_attachment_fields({"deck_id": "deck_1", "cover_thumbnail": "/tmp/page.jpg"})
        slide_record = archive.record_without_attachment_fields({"slide_id": "slide_1", "thumbnail": "/tmp/page.jpg"})

        self.assertEqual(deck_record, {"deck_id": "deck_1"})
        self.assertEqual(slide_record, {"slide_id": "slide_1"})

    def test_base_write_records_exclude_all_reusable_attachment_fields(self):
        archive = load_module("archive")

        record = archive.record_without_attachment_fields(
            {
                "deck_id": "deck_1",
                "deck_json": "/tmp/deck.json",
                "inline_html": "/tmp/index.html",
                "assets_zip": "/tmp/assets.zip",
                "cover_thumbnail": "/tmp/page.jpg",
                "thumbnail": "/tmp/page.jpg",
            }
        )

        self.assertEqual(record, {"deck_id": "deck_1"})

    def test_slide_records_use_cloud_artifact_reference_not_local_path(self):
        archive = load_module("archive")
        deck = {"slides": [{"key": "intro", "layout": "raw"}]}

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["source_artifact_ref"], "base://deck/deck_demo")
        self.assertNotIn("source_deck_json", records[0])

    def test_slide_records_create_material_fields_for_search_and_compose(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "intro",
                    "layout": "raw",
                    "screen_label": "01",
                    "data": {
                        "title": "客户反馈背景",
                        "html": "<section><h1>客户反馈背景</h1><p>围绕 VOC 数据介绍现状。</p></section>",
                    },
                    "custom_css": ".title{color:#fff}",
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["material_id"], "deck_demo:M001")
        self.assertEqual(records[0]["material_code"], "M001")
        self.assertIn("客户反馈背景", records[0]["page_description"])
        self.assertIn("VOC 数据介绍现状", records[0]["page_description"])
        self.assertEqual(json.loads(records[0]["slide_payload_json"])["key"], "intro")

    def test_slide_records_create_chinese_user_facing_fields(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "feedback-action-flow",
                    "layout": "raw",
                    "data": {
                        "title": "客户反馈行动闭环",
                        "html": "<section><p>从 VOC 收集到行动跟进。</p></section>",
                    },
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["素材名称"], "客户反馈行动闭环")
        self.assertIn("客户反馈行动闭环", records[0]["素材描述"])
        self.assertIn("VOC 收集到行动跟进", records[0]["素材描述"])
        self.assertIn("汇报材料", records[0]["适用场景"])
        self.assertIn("复用", records[0]["页面价值"])
        self.assertEqual(records[0]["视觉类型"], "raw")
        self.assertIn("feedback action flow", records[0]["关键词"])

    def test_image_only_slide_gets_searchable_page_description(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "vipshop-pilot-cover",
                    "layout": "replica",
                    "screen_label": "01",
                    "data": {"page_image": "pages/page-01.jpg", "alt": "vipshop_c_feedback source slide 01", "source_page": 1},
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertIn("vipshop pilot cover", records[0]["page_description"])
        self.assertIn("source slide 01", records[0]["page_description"])
        self.assertIn("page 1", records[0]["page_description"])

    def test_slide_records_mark_full_bleed_image_pages_as_replica_screenshot(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "page-08-demo",
                    "layout": "raw",
                    "data": {
                        "title": "模型到应用",
                        "html": '<section class="material-replica"><img class="material-image" src="pages/page-08.png" alt="模型到应用"></section>',
                    },
                    "custom_css": ".material-image{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}",
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["material_type"], "replica_screenshot")
        self.assertEqual(records[0]["quality_tier"], "draft")
        self.assertIn("截图", records[0]["fidelity_notes"])
        self.assertIn("native H5", records[0]["fidelity_notes"])
        self.assertEqual(records[0]["has_motion"], False)
        self.assertEqual(records[0]["motion_tier"], "none")
        self.assertIn("默认不加动效", records[0]["motion_notes"])

    def test_slide_records_mark_normal_raw_html_pages_as_native_h5(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "native-summary",
                    "layout": "raw",
                    "data": {
                        "title": "客户反馈总结",
                        "html": "<section><h1>客户反馈总结</h1><p>保留真实文本和布局。</p></section>",
                    },
                    "custom_css": "h1{font-size:48px}",
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["material_type"], "native_h5")
        self.assertEqual(records[0]["quality_tier"], "delivery")
        self.assertIn("真实 HTML/CSS", records[0]["fidelity_notes"])
        self.assertEqual(records[0]["has_motion"], False)
        self.assertEqual(records[0]["motion_tier"], "none")
        self.assertIn("当前无 bespoke motion", records[0]["motion_notes"])

    def test_slide_records_mark_animated_native_h5_motion_metadata(self):
        archive = load_module("archive")
        deck = {
            "slides": [
                {
                    "key": "native-motion",
                    "layout": "raw",
                    "data": {
                        "title": "动效素材",
                        "html": '<section><h1 class="reveal">动效素材</h1></section>',
                    },
                    "custom_css": (
                        '@media (prefers-reduced-motion: no-preference){'
                        '.slide-frame.is-current .slide[data-slide-key="native-motion"] .reveal{'
                        'animation:native-motion-rise .6s both;'
                        '}'
                        '}'
                        '@keyframes native-motion-rise{from{opacity:0}to{opacity:1}}'
                    ),
                }
            ]
        }

        records = archive.slide_records("deck_demo", deck, Path("/tmp/demo/output"))

        self.assertEqual(records[0]["material_type"], "native_h5")
        self.assertEqual(records[0]["quality_tier"], "delivery")
        self.assertEqual(records[0]["has_motion"], True)
        self.assertEqual(records[0]["motion_tier"], "subtle")
        self.assertIn("CSS-only 动效", records[0]["motion_notes"])

    def test_upload_deck_artifacts_uploads_cloud_reusable_files(self):
        archive = load_module("archive")
        calls = []

        def fake_replace(config, *, table_id, record_id, field_id, files):
            calls.append((table_id, record_id, field_id, files))
            return {"ok": True, "field_id": field_id}

        archive.lark_base.replace_attachment = fake_replace
        config = archive.lark_base.BaseConfig(
            base_token="base",
            decks_table="tblDecks",
            slides_table="tblSlides",
        )

        result = archive.upload_deck_artifacts(
            config,
            deck_result={"record_id": "recDeck"},
            artifact_files={
                "deck_json": str(Path.cwd() / "runs/demo/output/deck.json"),
                "inline_html": str(Path.cwd() / "runs/demo/output/index.html"),
                "assets_zip": None,
            },
        )

        self.assertEqual(result["deck_json"]["uploaded"], True)
        self.assertEqual(result["inline_html"]["uploaded"], True)
        self.assertEqual([call[2] for call in calls], ["deck_json", "inline_html"])
        self.assertEqual(calls[0][3], ["runs/demo/output/deck.json"])

    def test_attachment_upload_path_is_relative_to_current_directory(self):
        archive = load_module("archive")
        path = Path.cwd() / "runs" / "demo" / "output" / "pages" / "page-01.jpg"

        self.assertEqual(
            archive.attachment_upload_path(str(path)),
            "runs/demo/output/pages/page-01.jpg",
        )


if __name__ == "__main__":
    unittest.main()
