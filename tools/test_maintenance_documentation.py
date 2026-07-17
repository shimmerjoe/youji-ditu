import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MaintenanceDocumentationTests(unittest.TestCase):
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
        self.assertIn("git push origin main", readme)


if __name__ == "__main__":
    unittest.main()
