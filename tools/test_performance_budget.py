import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PerformanceBudgetTests(unittest.TestCase):
    def test_homepage_keeps_the_curated_discovery_budget(self):
        home_path = ROOT / "site" / "index.html"
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
            # 入口只含搜索、省份导航和两个按需加载钩子；行程计划代码在分块里。
            "travel-app.js": 12_000,
            "travel-app.css": 5_000,
        }
        for name, budget in budgets.items():
            with self.subTest(asset=name):
                size = (ROOT / "site" / "assets" / name).stat().st_size
                self.assertLessEqual(size, budget, f"{name} is {size} bytes; budget is {budget}")

    def test_trip_planner_code_is_lazy_loaded_instead_of_shipped_to_every_page(self):
        entry = (ROOT / "site" / "assets" / "travel-app.js").read_text(encoding="utf-8")
        self.assertNotIn("生成分享链接", entry)
        self.assertNotIn("放进哪份行程", entry)
        chunks = sorted((ROOT / "site" / "assets").glob("travel-chunk-*.js"))
        self.assertTrue(chunks, "planner chunks were not emitted")
        combined = "".join(chunk.read_text(encoding="utf-8") for chunk in chunks)
        self.assertIn("生成分享链接", combined)
        self.assertIn("放进哪份行程", combined)
        for chunk in chunks:
            with self.subTest(chunk=chunk.name):
                self.assertLessEqual(chunk.stat().st_size, 40_000)

    def test_large_feature_data_is_not_loaded_by_unrelated_pages(self):
        home = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        qingdao = (ROOT / "site" / "cities" / "qingdao.html").read_text(encoding="utf-8")
        roadtrip = (ROOT / "site" / "roadtrip.html").read_text(encoding="utf-8")
        for page in (home, qingdao):
            self.assertNotIn("roadtrip-data.js", page)
        self.assertIn("roadtrip-data.js", roadtrip)


if __name__ == "__main__":
    unittest.main()
