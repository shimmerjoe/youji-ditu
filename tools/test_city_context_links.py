import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QINGDAO_HTML = ROOT / "cities" / "qingdao.html"
INDEX_HTML = ROOT / "index.html"


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

    def test_destination_navigation_uses_one_compact_mega_menu(self):
        self.assertEqual(self.city_html.count('class="destination-nav'), 1)
        self.assertIn('class="destination-panel"', self.city_html)
        self.assertIn('class="destination-groups"', self.city_html)
        self.assertIn("全国目的地", self.city_html)
        self.assertRegex(self.city_html, r"<small>\d+ 个城市</small>")

    def test_destination_navigation_still_exposes_provinces_and_current_city(self):
        self.assertIn('<h3>山东</h3>', self.city_html)
        self.assertRegex(
            self.city_html,
            r'class="destination-city active" href="qingdao\.html">青岛</a>',
        )


if __name__ == "__main__":
    unittest.main()
