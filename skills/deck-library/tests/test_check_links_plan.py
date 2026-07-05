import importlib.util
import json
import subprocess
import sys
import urllib.error
import urllib.request
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


class CheckLinksPlanTests(unittest.TestCase):
    def test_classify_link_health_maps_missing_success_and_failure(self):
        check_links = load_module("check_links")

        self.assertEqual(check_links.classify_link_health(""), ("failed", "无线上链接"))
        self.assertEqual(check_links.classify_link_health("https://example.com", status_code=200), ("ok", "可访问"))
        self.assertEqual(
            check_links.classify_link_health("https://example.com", status_code=302),
            ("failed", "链接跳转未验证"),
        )
        self.assertEqual(
            check_links.classify_link_health("https://example.com", status_code=404),
            ("failed", "链接失效或无权限"),
        )
        self.assertEqual(
            check_links.classify_link_health("https://example.com", error="timeout"),
            ("failed", "链接检查失败: timeout"),
        )

    def test_build_update_fields_sets_human_machine_and_access_status(self):
        check_links = load_module("check_links")

        fields = check_links.build_update_fields("https://example.com", status_code=204, checked_at="2026-07-05 12:00:00")
        failed_fields = check_links.build_update_fields("https://example.com", status_code=404, checked_at="2026-07-05 12:00:00")
        missing_fields = check_links.build_update_fields("", checked_at="2026-07-05 12:00:00")

        self.assertEqual(fields["link_health"], "ok")
        self.assertEqual(fields["链接状态"], "可访问")
        self.assertEqual(fields["last_checked_at"], "2026-07-05 12:00:00")
        self.assertEqual(fields["access_status"], "ready")
        self.assertEqual(failed_fields["access_status"], "broken")
        self.assertEqual(missing_fields["access_status"], "draft")

    def test_url_safety_rejects_non_public_targets(self):
        check_links = load_module("check_links")

        self.assertIsNone(check_links.url_safety_error("https://bytedance.larkoffice.com/path"))
        self.assertIn("untrusted", check_links.url_safety_error("https://example.com/path"))
        self.assertIn("scheme", check_links.url_safety_error("file:///etc/passwd"))
        self.assertIn("private", check_links.url_safety_error("http://127.0.0.1:8000"))
        self.assertIn("private", check_links.url_safety_error("http://localhost:8000"))

    def test_redirect_handler_does_not_follow_unchecked_redirects(self):
        check_links = load_module("check_links")
        handler = check_links.NoRedirectHandler()
        request = urllib.request.Request("https://example.com")

        with self.assertRaises(urllib.error.HTTPError) as ctx:
            handler.http_error_302(request, None, 302, "Found", {})

        self.assertEqual(ctx.exception.code, 302)

    def test_extract_rows_preserves_record_ids_for_safe_updates(self):
        check_links = load_module("check_links")
        result = {
            "data": {
                "record_id_list": ["rec1"],
                "fields": ["deck_id", "online_url"],
                "data": [["deck_1", "https://example.com"]],
            }
        }

        self.assertEqual(
            check_links.extract_rows(result),
            [{"_record_id": "rec1", "deck_id": "deck_1", "online_url": "https://example.com"}],
        )

    def test_check_links_dry_run_prints_plan_without_configuration(self):
        completed = subprocess.run(
            [
                sys.executable,
                str(ASSETS / "check_links.py"),
                "--dry-run",
                "--limit",
                "5",
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["operation"], "check_links")
        self.assertEqual(payload["limit"], 5)


if __name__ == "__main__":
    unittest.main()
