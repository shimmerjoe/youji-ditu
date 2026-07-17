import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS_PATH = ROOT / "assets" / "travel.css"
OVERRIDE_MARKER = "/* ===== 2026 实用型重构覆盖层 ===== */"


class DesktopNavigationRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        css = CSS_PATH.read_text(encoding="utf-8")
        cls.override = css.split(OVERRIDE_MARKER, 1)[1]
        cls.desktop_override = cls.override.split("@media (max-width: 920px)", 1)[0]

    def test_wide_screen_shells_use_the_available_width(self):
        expected_selectors = (
            ".header-bar",
            ".top-nav",
            ".hero",
            ".research-panel",
            ".home-section",
            ".city-explorer",
            ".source-media",
            ".city-overview",
            ".tool-bar",
            ".layout",
        )
        for selector in expected_selectors:
            with self.subTest(selector=selector):
                rule = re.search(
                    rf"{re.escape(selector)}[^{{]*\{{[^}}]*max-width:\s*none;",
                    self.desktop_override,
                    re.S,
                )
                self.assertIsNotNone(rule, f"{selector} is still capped on wide screens")

    def test_desktop_province_navigation_does_not_clip_dropdowns(self):
        rules = re.findall(r"\.top-nav\s*\{([^}]*)\}", self.desktop_override, re.S)
        self.assertTrue(rules, "missing desktop .top-nav rule")
        self.assertIn("overflow: visible;", rules[-1])

    def test_province_buttons_hide_all_disclosure_markers(self):
        self.assertRegex(
            self.desktop_override,
            r"\.nav-group summary::after\s*\{\s*display:\s*none;\s*\}",
        )
        self.assertRegex(
            self.desktop_override,
            r"\.nav-group summary::marker\s*\{[^}]*content:\s*\"\";",
        )


class MobileActionRegressionTests(unittest.TestCase):
    def test_mobile_navigation_can_be_closed_with_escape(self):
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn("function closeMobileNav()", script)
        self.assertIn('event.key === "Escape" && header.classList.contains("nav-open")', script)

    def test_back_to_top_is_a_compact_icon_button(self):
        roadtrip = (ROOT / "roadtrip.html").read_text(encoding="utf-8")
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
        city = (ROOT / "cities" / "qingdao.html").read_text(encoding="utf-8")
        self.assertIn('hero-carousel" id="heroCarousel" data-count="1"', city)
        self.assertNotIn('class="hero-arrow', city)
        self.assertNotIn('class="hero-dot', city)


if __name__ == "__main__":
    unittest.main()
