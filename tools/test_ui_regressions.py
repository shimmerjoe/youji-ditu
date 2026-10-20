import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
CSS_PATH = SITE / "assets" / "travel.css"


class NavigationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.css = CSS_PATH.read_text(encoding="utf-8")
        cls.qingdao = (SITE / "cities" / "qingdao.html").read_text(encoding="utf-8")

    def test_content_blocks_share_one_centered_container_except_full_bleed_heroes(self):
        rule = re.search(r"main > :not\(\.city-hero\):not\(\.section-tabs\)[^{]*\{([^}]*)\}", self.css)
        self.assertIsNotNone(rule, "missing shared container rule")
        self.assertIn("margin-inline: auto", rule.group(1))

    def test_province_menu_is_a_toggled_panel_instead_of_permanent_rows(self):
        self.assertRegex(self.css, r"\.top-nav\s*\{\s*display:\s*none;")
        self.assertRegex(self.css, r"\.site-header\.nav-open \.top-nav\s*\{\s*display:\s*block;")
        self.assertIn('id="navToggle"', self.qingdao)
        self.assertIn('aria-controls="topNav"', self.qingdao)

    def test_province_buttons_hide_all_disclosure_markers(self):
        self.assertRegex(self.css, r"\.destination-nav > summary::-webkit-details-marker\s*\{\s*display:\s*none;")
        self.assertRegex(self.css, r"\.destination-nav > summary::marker\s*\{[^}]*content:\s*\"\";")

    def test_open_province_expands_inline_so_city_lists_are_never_clipped(self):
        self.assertRegex(self.css, r"\.destination-nav\[open\]\s*\{\s*grid-column:\s*1 / -1;")


class MobileActionRegressionTests(unittest.TestCase):
    def test_mobile_navigation_can_be_closed_with_escape(self):
        script = (SITE / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn("function closeMobileNav()", script)
        self.assertIn('event.key === "Escape" && header.classList.contains("nav-open")', script)

    def test_back_to_top_is_a_compact_icon_button(self):
        roadtrip = (SITE / "roadtrip.html").read_text(encoding="utf-8")
        css = CSS_PATH.read_text(encoding="utf-8")
        self.assertIn('aria-label="返回顶部"', roadtrip)
        self.assertRegex(roadtrip, r'<button class="to-top"[^>]*>↑</button>')
        self.assertNotIn('>返回顶部</button>', roadtrip)
        rules = re.findall(r"\.to-top\s*\{([^}]*)\}", css, re.S)
        self.assertTrue(rules)
        combined = "\n".join(rules)
        self.assertRegex(combined, r"width:\s*46px;")
        self.assertRegex(combined, r"border-radius:\s*50%;")


class CityMediaRegressionTests(unittest.TestCase):
    def test_single_image_city_hero_has_no_inert_carousel_controls(self):
        city = (SITE / "cities" / "qingdao.html").read_text(encoding="utf-8")
        self.assertIn('hero-carousel" id="heroCarousel" data-count="1"', city)
        self.assertNotIn('class="hero-arrow', city)
        self.assertNotIn('class="hero-dot', city)

    def test_city_without_licensed_cover_uses_a_typographic_hero(self):
        city = (SITE / "cities" / "city-c815eff127.html").read_text(encoding="utf-8")
        self.assertIn('class="city-hero no-photo"', city)
        self.assertNotIn('id="heroCarousel"', city)


class GuideComponentTests(unittest.TestCase):
    """The Markdown outline is rendered as task-shaped components, not nested bullets."""

    @classmethod
    def setUpClass(cls):
        cls.beijing = (SITE / "cities" / "beijing.html").read_text(encoding="utf-8")

    def test_sections_use_dedicated_components(self):
        for marker in (
            'class="fact-grid"',
            'class="scenario-grid"',
            'class="month-grid" data-month-grid',
            'class="card-grid"',
            'class="route-list"',
            'class="tip-list"',
            'class="area-grid"',
            'class="row-list"',
            'class="check-list" data-checklist="beijing"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, self.beijing)
        self.assertNotIn('class="md-list', self.beijing)
        self.assertNotIn('class="item-label"', self.beijing)

    def test_long_cards_disclose_details_progressively_without_script(self):
        self.assertIn('<details class="card-more">', self.beijing)
        self.assertIn("展开其余", self.beijing)

    def test_food_cards_lead_with_the_dish_name(self):
        self.assertRegex(self.beijing, r'<p class="card-kicker">特色菜</p><h3 class="card-title">北京烤鸭</h3>')

    def test_section_tabs_and_side_toc_share_the_same_anchors(self):
        tabs = self.beijing.split('<nav class="section-tabs"', 1)[1].split("</nav>", 1)[0]
        for anchor in ("#overview", "#months", "#attractions", "#food", "#routes", "#checklist"):
            with self.subTest(anchor=anchor):
                self.assertIn(f'href="{anchor}"', tabs)
                self.assertIn(f'id="{anchor[1:]}"', self.beijing)


if __name__ == "__main__":
    unittest.main()
