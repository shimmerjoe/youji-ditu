import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MaintenanceDocumentationTests(unittest.TestCase):
    def test_generated_documents_and_windows_scripts_stay_out_of_root(self):
        self.assertFalse(list(ROOT.glob("*.bat")))
        for name in ("内容与图片体检.md", "资料来源与更新规则.md", "便携运行说明.md", "移动端与APK说明.md", "聊天记录整理.md"):
            with self.subTest(name=name):
                self.assertFalse((ROOT / name).exists())
        self.assertTrue((ROOT / "docs/reports/内容与图片体检.md").is_file())
        self.assertTrue((ROOT / "docs/guides/资料来源与更新规则.md").is_file())
        for script in (ROOT / "scripts/windows").glob("*.bat"):
            with self.subTest(script=script.name):
                self.assertIn('%~dp0..\\..', script.read_text(encoding="utf-8"))

    def test_iteration_log_records_priority_backlog_and_evidence(self):
        log = ROOT / "docs" / "iteration-log.md"
        self.assertTrue(log.exists(), "iteration log must be retained with the generated site")
        content = log.read_text(encoding="utf-8")
        for heading in ("## 待办清单", "## 第 9 轮", "问题", "验证结果", "遗留风险"):
            with self.subTest(heading=heading):
                self.assertIn(heading, content)

    def test_readme_requires_github_pages_sync_after_each_maintenance_release(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://shimmerjoe.github.io/youji-ditu/", readme)
        self.assertIn("GitHub Pages", readme)
        self.assertIn("公开地址", readme)
        self.assertIn("选择性", readme)
        self.assertNotIn("git add -A", readme)
        self.assertIn("明确授权", readme)
        self.assertIn("不上传服务器", readme)
        self.assertIn("私人知识库", readme)

    def test_readme_documents_the_reviewed_photo_workflow(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("assets\\photo-editorial-decisions.json", readme)
        self.assertIn("tools\\import_commons_city_photo.py", readme)
        self.assertIn("TRAVEL_FETCH_CITY_KEYS", readme)
        self.assertIn("授权合规", readme)
        self.assertIn("内容适配", readme)


if __name__ == "__main__":
    unittest.main()
