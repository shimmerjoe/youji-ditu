import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CITY_DIR = ROOT / "城市"
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

    def test_special_regions_have_their_own_destination_group(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        municipality = index.split("<h3>直辖市</h3>", 1)[1].split("</section>", 1)[0]
        special = index.split("<h3>特别行政区</h3>", 1)[1].split("</section>", 1)[0]
        self.assertIn(">北京</a>", municipality)
        self.assertNotIn(">香港</a>", municipality)
        self.assertNotIn(">澳门</a>", municipality)
        self.assertIn(">香港</a>", special)
        self.assertIn(">澳门</a>", special)

    def test_generated_site_exposes_all_new_destinations(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("222 个城市", index)
        for stem, config in self.cities.items():
            with self.subTest(city=stem):
                output = ROOT / "cities" / f'{config["slug"]}.html'
                self.assertTrue(output.exists())
                self.assertIn(f'cities/{config["slug"]}.html', index)

    def test_new_city_quick_find_exposes_all_four_core_sections(self):
        for config in self.cities.values():
            with self.subTest(city=config["slug"]):
                output = ROOT / "cities" / f'{config["slug"]}.html'
                html = output.read_text(encoding="utf-8")
                self.assertIn('href="#attractions"', html)
                self.assertIn('href="#food"', html)
                self.assertIn('href="#routes"', html)
                self.assertIn('href="#warnings"', html)
                quick_find = html.split('<div class="hero-quickfind">', 1)[1].split('</div></div>', 1)[0]
                self.assertEqual(4, quick_find.count('class="quickfind-card"'))

    def test_new_city_cover_photos_are_local_and_licensed(self):
        cache = json.loads((ROOT / "assets" / "photo-cache.json").read_text(encoding="utf-8"))
        for config in self.cities.values():
            key = f'cityphoto|{config["slug"]}'
            with self.subTest(city=config["slug"]):
                entry = cache[key]
                self.assertEqual("hit", entry["status"])
                self.assertTrue((ROOT / entry["path"]).exists())
                self.assertIn("commons.wikimedia.org", entry["source"])
                self.assertTrue(entry["license"])


if __name__ == "__main__":
    unittest.main()
