import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PerformanceBudgetTests(unittest.TestCase):
    def test_homepage_keeps_the_curated_discovery_budget(self):
        home_path = ROOT / "index.html"
        home = home_path.read_text(encoding="utf-8")
        self.assertLessEqual(home_path.stat().st_size, 320_000)
        self.assertEqual(home.count('<article class="city-card '), 24)
        slide_images = re.findall(r'class="hero-slide[^\"]*"[^>]*>\s*<img\s+([^>]+)>', home, re.S)
        self.assertGreater(len(slide_images), 1)
        self.assertEqual(sum(bool(re.search(r'(?:^|\s)src="', attrs)) for attrs in slide_images), 1)

    def test_shared_runtime_assets_stay_within_reviewed_budgets(self):
        budgets = {
            "travel.css": 120_000,
            "travel.js": 90_000,
            "travel-app.js": 10_000,
            "travel-app.css": 5_000,
        }
        for name, budget in budgets.items():
            with self.subTest(asset=name):
                size = (ROOT / "assets" / name).stat().st_size
                self.assertLessEqual(size, budget, f"{name} is {size} bytes; budget is {budget}")

    def test_large_feature_data_is_not_loaded_by_unrelated_pages(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        qingdao = (ROOT / "cities" / "qingdao.html").read_text(encoding="utf-8")
        roadtrip = (ROOT / "roadtrip.html").read_text(encoding="utf-8")
        for page in (home, qingdao):
            self.assertNotIn("roadtrip-data.js", page)
        self.assertIn("roadtrip-data.js", roadtrip)


if __name__ == "__main__":
    unittest.main()
