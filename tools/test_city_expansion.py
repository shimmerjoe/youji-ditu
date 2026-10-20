import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CITY_DIR = ROOT / "content" / "城市"
META_PATH = ROOT / "tools" / "city-page-meta.json"


class CityExpansionTests(unittest.TestCase):
    cities = {
        "香港_香港": {
            "slug": "hong-kong",
            "sources": ["discoverhongkong.com", "hko.gov.hk"],
        },
        "澳门_澳门": {
            "slug": "macao",
            "sources": ["macaotourism.gov.mo", "wh.mo"],
        },
        "吉林_吉林市": {
            "slug": "jilin-city",
            "sources": ["jlcity.gov.cn", "jl.gov.cn"],
        },
        "辽宁_盘锦": {
            "slug": "panjin",
            "sources": ["panjin.gov.cn"],
        },
    }

    def test_four_new_city_guides_have_consistent_travel_sections(self):
        required = [
            "## 先看结论",
            "## 适合季节与天数",
            "## 核心景点",
            "## 行程路线",
            "## 交通细节",
            "## 预算参考",
            "## 避坑提醒",
            "## 来源参考",
        ]
        for stem in self.cities:
            with self.subTest(city=stem):
                text = (CITY_DIR / f"{stem}.md").read_text(encoding="utf-8")
                for heading in required:
                    self.assertIn(heading, text)
                self.assertIn("动态信息核验日期：2026-07-15", text)

    def test_new_city_guides_use_official_sources(self):
        for stem, config in self.cities.items():
            with self.subTest(city=stem):
                text = (CITY_DIR / f"{stem}.md").read_text(encoding="utf-8")
                for domain in config["sources"]:
                    self.assertIn(domain, text)

    def test_new_cities_have_stable_public_slugs(self):
        meta = json.loads(META_PATH.read_text(encoding="utf-8"))
        for stem, config in self.cities.items():
            with self.subTest(city=stem):
                self.assertEqual(config["slug"], meta[stem]["slug"])

    def test_hong_kong_and_macao_are_top_level_regions(self):
        generator = (ROOT / "tools" / "build_travel_html.py").read_text(encoding="utf-8")
        self.assertIn('SPECIAL_REGIONS = {"香港", "澳门"}', generator)
        self.assertIn("TOP_LEVEL_REGIONS = DIRECT_MUNICIPALITIES | SPECIAL_REGIONS", generator)

    def test_special_regions_have_a_dedicated_discovery_route(self):
        index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        destinations = (ROOT / "site" / "destinations.html").read_text(encoding="utf-8")
        self.assertIn("destinations.html?region=%E6%B8%AF%E6%BE%B3", index)
        self.assertIn('data-province="香港"', destinations)
        self.assertIn('data-province="澳门"', destinations)
        self.assertIn('data-province="直辖市"', destinations)
        self.assertIn('href="cities/beijing.html"', destinations)

    def test_generated_site_exposes_all_new_destinations(self):
        index = (ROOT / "site" / "index.html").read_text(encoding="utf-8")
        catalog = (ROOT / "site" / "city-guides.html").read_text(encoding="utf-8")
        self.assertIn('<div><dt>城市攻略</dt><dd>222</dd></div>', index)
        self.assertIn('data-nav-group="直辖市"', index)
        for stem, config in self.cities.items():
            with self.subTest(city=stem):
                output = ROOT / "site" / "cities" / f'{config["slug"]}.html'
                self.assertTrue(output.exists())
                self.assertIn(f'cities/{config["slug"]}.html', catalog)

    def test_new_city_quick_find_exposes_all_four_core_sections(self):
        for config in self.cities.values():
            with self.subTest(city=config["slug"]):
                output = ROOT / "site" / "cities" / f'{config["slug"]}.html'
                html = output.read_text(encoding="utf-8")
                self.assertIn('href="#attractions"', html)
                self.assertIn('href="#food"', html)
                self.assertIn('href="#routes"', html)
                self.assertIn('href="#warnings"', html)
                tabs = html.split('<nav class="section-tabs"', 1)[1].split('</nav>', 1)[0]
                for anchor in ("#attractions", "#food", "#routes", "#warnings"):
                    self.assertIn(f'href="{anchor}"', tabs)

    def test_new_city_cover_photos_are_local_and_licensed(self):
        cache = json.loads((ROOT / "site" / "assets" / "photo-cache.json").read_text(encoding="utf-8"))
        for config in self.cities.values():
            key = f'cityphoto|{config["slug"]}'
            with self.subTest(city=config["slug"]):
                entry = cache[key]
                self.assertEqual("hit", entry["status"])
                self.assertTrue((ROOT / "site" / entry["path"]).exists())
                self.assertIn("commons.wikimedia.org", entry["source"])
                self.assertTrue(entry["license"])


if __name__ == "__main__":
    unittest.main()
