import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ContentTransparencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = (ROOT / "site" / "city-guides.html").read_text(encoding="utf-8")
        cls.reviewed_city = (ROOT / "site" / "cities" / "qingdao.html").read_text(encoding="utf-8")
        cls.pending_city = (ROOT / "site" / "cities" / "changsha.html").read_text(encoding="utf-8")
        cls.css = (ROOT / "site" / "assets" / "travel.css").read_text(encoding="utf-8")

    def test_city_finder_exposes_review_status_without_claiming_freshness(self):
        self.assertIn("资料状态", self.page)
        self.assertRegex(self.page, r"\d+ 座待复核")
        self.assertIn("出行前复核", self.page)

    def test_city_overview_exposes_explicit_review_date_and_recheck_action(self):
        self.assertIn('class="co-cell co-review reviewed"', self.reviewed_city)
        self.assertIn('<span class="co-v">核验日期 2026-07-15</span>', self.reviewed_city)
        self.assertIn("动态信息出行前复核", self.reviewed_city)

    def test_city_overview_keeps_missing_review_evidence_visible(self):
        self.assertIn('class="co-cell co-review pending"', self.pending_city)
        self.assertIn('<span class="co-v">资料待复核</span>', self.pending_city)
        self.assertIn("动态信息出行前复核", self.pending_city)

    def test_review_status_uses_existing_design_tokens(self):
        defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", self.css))
        used = set(re.findall(r"var\((--[a-z0-9-]+)", self.css))
        self.assertEqual(set(), used - defined, "stylesheet references undefined custom properties")
        self.assertIn(".co-review.pending", self.css)
        self.assertIn(".city-review-status.reviewed", self.css)


if __name__ == "__main__":
    unittest.main()
