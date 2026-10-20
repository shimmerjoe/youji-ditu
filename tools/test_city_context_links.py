import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QINGDAO_HTML = ROOT / "site" / "cities" / "qingdao.html"
INDEX_HTML = ROOT / "site" / "index.html"


class CityContextLinkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.city_html = QINGDAO_HTML.read_text(encoding="utf-8")
        cls.index_html = INDEX_HTML.read_text(encoding="utf-8")

    def test_city_page_removes_the_full_width_research_panel(self):
        self.assertNotIn("青岛联网核验入口", self.city_html)
        self.assertNotIn('aria-label="联网核验入口"', self.city_html)

    def test_home_page_keeps_the_research_method_panel(self):
        self.assertIn('aria-label="资料更新规则"', self.index_html)

    def test_core_attractions_have_compact_context_actions(self):
        match = re.search(
            r'id="attractions-[^"]*".*?<nav class="poi-actions".*?</nav>',
            self.city_html,
            re.S,
        )
        self.assertIsNotNone(match, "missing contextual links on a core attraction")
        block = match.group(0)
        self.assertIn("查官网", block)
        self.assertIn("地图", block)
        self.assertIn("攻略", block)
        self.assertIn('target="_blank"', block)
        self.assertIn('rel="noopener noreferrer"', block)
        self.assertLessEqual(block.count("<a "), 3)

    def test_city_sources_are_presented_as_a_compact_footer_resource_area(self):
        self.assertIn("实用信息与资料来源", self.city_html)
        self.assertIn("出行前复核", self.city_html)

    def test_destination_navigation_lists_provinces_without_a_nationwide_or_hot_city_strip(self):
        self.assertIn('class="province-nav-list"', self.city_html)
        self.assertGreaterEqual(self.city_html.count('class="destination-nav province-nav'), 20)
        self.assertNotIn("全国目的地", self.city_html)
        self.assertNotIn('class="destination-quick"', self.city_html)
        self.assertNotIn('aria-label="热门目的地"', self.city_html)

    def test_municipalities_are_the_first_group_and_current_province_is_active(self):
        municipality_at = self.city_html.index('data-nav-group="直辖市"')
        anhui_at = self.city_html.index('data-nav-group="安徽"')
        self.assertLess(municipality_at, anhui_at)
        self.assertRegex(
            self.city_html,
            r'class="destination-nav province-nav active" data-nav-group="山东"',
        )
        self.assertIn('data-nav-group="港澳"', self.city_html)
        self.assertRegex(self.city_html, r'<small>\d+ 城</small>')

    def test_province_city_lists_are_progressively_loaded_instead_of_duplicated_per_page(self):
        self.assertIn('data-destination-menu', self.city_html)
        self.assertIn('aria-live="polite"', self.city_html)
        self.assertLessEqual(self.city_html.count('class="destination-city'), 4)
        self.assertIn('href="../destinations.html?province=%E5%B1%B1%E4%B8%9C"', self.city_html)


if __name__ == "__main__":
    unittest.main()
