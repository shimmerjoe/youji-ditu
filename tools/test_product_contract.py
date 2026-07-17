import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ProductContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.user = (ROOT / "user.html").read_text(encoding="utf-8")
        cls.qingdao = (ROOT / "cities" / "qingdao.html").read_text(encoding="utf-8")

    def test_source_files_are_not_excluded_from_version_control(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        ignored_lines = {
            line.strip()
            for line in gitignore.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        for source_path in ("tools/", "城市/", "记录.md"):
            with self.subTest(source_path=source_path):
                self.assertNotIn(source_path, ignored_lines)

    def test_home_has_multidimensional_trip_finder(self):
        for control_id in (
            "travelRegion",
            "travelSeason",
            "travelDays",
            "travelTheme",
            "travelTransport",
        ):
            with self.subTest(control_id=control_id):
                self.assertIn(f'id="{control_id}"', self.home)
        self.assertIn('id="travelFinderReset"', self.home)
        self.assertIn('id="travelFinderSummary"', self.home)

    def test_home_city_catalog_is_progressively_disclosed(self):
        self.assertIn('id="cityLoadMore"', self.home)
        self.assertIn('id="cityExplorerSummary"', self.home)
        self.assertIn("CITY_PAGE_SIZE", (ROOT / "assets" / "travel.js").read_text(encoding="utf-8"))

    def test_trip_finder_state_is_shareable_and_restored_from_the_url(self):
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn("function readFinderState()", script)
        self.assertIn("function writeFinderState()", script)
        self.assertIn('history.replaceState', script)
        for key in ("q", "region", "season", "days", "theme", "transport"):
            with self.subTest(key=key):
                self.assertIn(f'params.get("{key}")', script)

    def test_primary_navigation_exposes_product_areas_on_desktop_and_mobile(self):
        for label in ("首页", "目的地", "主题玩法", "城市攻略", "自驾路书", "实用工具"):
            with self.subTest(label=label):
                self.assertIn(f">{label}</a>", self.home)
        self.assertIn('class="mobile-primary-nav"', self.home)

    def test_mobile_layout_avoids_full_width_sections_plus_side_margins(self):
        css = (ROOT / "assets" / "travel.css").read_text(encoding="utf-8")
        self.assertIn("width: calc(100% - 24px)", css)
        self.assertRegex(css, r"\.user-tab\s*\{[^}]*white-space:\s*nowrap", re.S)

    def test_home_theme_catalog_covers_core_travel_needs(self):
        for theme in ("亲子", "博物馆", "自然风光", "历史文化", "美食", "避暑", "冬季", "周末短途"):
            with self.subTest(theme=theme):
                self.assertIn(theme, self.home)

    def test_user_center_has_recent_history_panel(self):
        self.assertIn('data-tab="history"', self.user)
        self.assertIn('data-panel="history"', self.user)
        self.assertIn('id="historyList"', self.user)
        self.assertIn('id="historyEmpty"', self.user)
        self.assertIn("tay_recent", self.user)

    def test_city_overview_does_not_present_a_single_month_as_the_season(self):
        match = re.search(
            r'<span class="co-k">适宜季节</span><span class="co-v">([^<]+)</span>',
            self.qingdao,
        )
        self.assertIsNotNone(match)
        self.assertNotRegex(match.group(1), r"^\d{1,2}\s*月$")
        self.assertRegex(match.group(1), r"春|夏|秋|冬|全年|月")


if __name__ == "__main__":
    unittest.main()
