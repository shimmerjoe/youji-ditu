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


class CityTemplateRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = {path.stem: path.read_text(encoding="utf-8") for path in (ROOT / "content" / "城市").glob("*.md")}
        cls.destinations = (ROOT / "site" / "destinations.html").read_text(encoding="utf-8")

    def test_no_city_claims_social_media_research_that_was_not_done(self):
        offenders = [name for name, text in self.sources.items() if "结合小红书" in text]
        self.assertEqual(offenders, [])

    def test_shared_day_plan_template_is_gone(self):
        template = "半天看城市核心或夜市，1 天打一条经典线，2-3 天再加远郊/周边"
        self.assertEqual([name for name, text in self.sources.items() if template in text], [])

    def test_summaries_keep_numeric_ranges(self):
        import sys
        sys.path.insert(0, str(ROOT / "tools"))
        import build_travel_html as builder
        self.assertEqual("3-5 月、9-11 月", builder.clean_summary("- 3-5 月、9-11 月"))

    def test_theme_filters_still_discriminate(self):
        themes = re.findall(r'data-theme="([^"]*)"', self.destinations)
        family = sum("亲子" in value.split() for value in themes)
        weekend = sum("周末短途" in value.split() for value in themes)
        self.assertGreater(family, 0)
        self.assertLess(family, len(themes) // 3)
        self.assertLess(weekend, len(themes) // 2)


if __name__ == "__main__":
    unittest.main()
