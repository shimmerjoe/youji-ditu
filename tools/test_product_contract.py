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

    def test_home_uses_a_curated_city_subset_while_catalog_remains_complete(self):
        catalog = (ROOT / "city-guides.html").read_text(encoding="utf-8")
        self.assertEqual(self.home.count('<article class="city-card '), 24)
        self.assertEqual(catalog.count('<article class="city-card '), 222)
        self.assertIn('data-catalog-scope="curated"', self.home)
        self.assertIn('href="destinations.html"', self.home)
        self.assertLess(len(self.home.encode("utf-8")), 450_000)

    def test_carousel_defers_non_active_images_and_respects_reduced_motion(self):
        slide_images = re.findall(
            r'class="hero-slide[^\"]*"[^>]*>\s*<img\s+([^>]+)>',
            self.home,
            re.S,
        )
        self.assertGreaterEqual(len(slide_images), 2)
        self.assertRegex(slide_images[0], r'(?:^|\s)src="[^"]+"')
        for attrs in slide_images[1:]:
            self.assertNotRegex(attrs, r'(?:^|\s)src="')
            self.assertRegex(attrs, r'(?:^|\s)data-src="[^"]+"')
        self.assertIn('class="hero-pause"', self.home)
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn("function hydrateSlide", script)
        self.assertIn('prefers-reduced-motion: reduce', script)

    def test_search_index_is_loaded_on_demand_instead_of_blocking_every_page(self):
        self.assertRegex(self.home, r'data-search-index="assets/search-index\.js\?v=[0-9a-f]{10}"')
        self.assertNotRegex(self.home, r'<script[^>]+src="assets/search-index\.js')
        source = (ROOT / "frontend" / "src" / "site-search.ts").read_text(encoding="utf-8")
        for marker in ("ensureSearchIndex", 'document.createElement("script")', "搜索索引加载失败"):
            with self.subTest(marker=marker):
                self.assertIn(marker, source)

    def test_city_catalog_exposes_review_status_filter_and_url_state(self):
        catalog = (ROOT / "city-guides.html").read_text(encoding="utf-8")
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        for marker in (
            'id="cityReviewFilter"',
            'data-review="reviewed"',
            'data-review="pending"',
            'data-review-status="pending"',
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, catalog)
        for marker in ("activeReview", 'params.get("review")', "reviewStatus"):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)

    def test_global_scroll_feedback_does_not_run_unthrottled_listeners(self):
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "travel.css").read_text(encoding="utf-8")
        self.assertNotIn('addEventListener("scroll"', script)
        self.assertNotIn("window.scrollY", script)
        self.assertIn("IntersectionObserver", script)
        self.assertIn("animation-timeline: scroll(root block)", css)
        self.assertIn("transform: scaleX(0)", css)

    def test_global_search_is_a_typed_accessible_progressive_enhancement(self):
        home = (ROOT / "index.html").read_text(encoding="utf-8")
        legacy_script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        typed_source = (ROOT / "frontend" / "src" / "site-search.ts").read_text(encoding="utf-8")
        self.assertIn('role="combobox"', home)
        self.assertIn('aria-autocomplete="list"', home)
        self.assertIn('aria-controls="siteSearchResults"', home)
        self.assertIn('role="listbox"', home)
        self.assertIn('id="siteSearchRecent"', home)
        self.assertIn('aria-label="最近搜索与浏览"', home)
        self.assertNotIn("renderSiteSearch", legacy_script)
        self.assertNotIn("innerHTML", typed_source)
        self.assertIn("aria-activedescendant", typed_source)
        for marker in ("tay_search_recent", "normalizeRecentSearches", "normalizeRecentVisits"):
            with self.subTest(marker=marker):
                self.assertIn(marker, typed_source)

    def test_lightbox_has_keyboard_and_focus_lifecycle_without_layout_animation(self):
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        css = (ROOT / "assets" / "travel.css").read_text(encoding="utf-8")
        self.assertNotIn("lb.innerHTML", script)
        self.assertIn('setAttribute("role", "dialog")', script)
        self.assertIn('setAttribute("aria-modal", "true")', script)
        self.assertIn("tabIndex = 0", script)
        self.assertIn("lightbox-active", script)
        self.assertNotIn("transition: width", css)

    def test_skip_link_is_prerendered_for_no_script_navigation(self):
        for relative_path in ("index.html", "cities/qingdao.html", "user.html"):
            page = (ROOT / relative_path).read_text(encoding="utf-8")
            self.assertIn('<a class="skip-link" href="#mainContent">跳到主要内容</a>', page)
            self.assertIn('<main id="mainContent" tabindex="-1">', page)
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertNotIn('skip.textContent = "跳到主要内容"', script)

    def test_city_catalog_uses_unique_indices_and_responsive_disclosure(self):
        catalog = (ROOT / "city-guides.html").read_text(encoding="utf-8")
        indices = [int(value) for value in re.findall(r'data-index="(\d+)"', catalog)]
        self.assertEqual(indices, list(range(222)))
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn('matchMedia("(max-width: 640px)").matches ? 12', script)
        self.assertIn('matchMedia("(max-width: 1100px)").matches ? 24', script)

    def test_city_catalog_does_not_nest_action_buttons_inside_links(self):
        catalog = (ROOT / "city-guides.html").read_text(encoding="utf-8")
        self.assertEqual(catalog.count('<article class="city-card '), 222)
        self.assertEqual(catalog.count('class="city-card-title"'), 222)
        self.assertNotIn('<a class="city-card rich"', catalog)
        self.assertNotIn('<a class="city-card noimg"', catalog)
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn("card.dataset.href", script)

    def test_city_page_does_not_embed_the_full_destination_catalog(self):
        self.assertNotIn('id="cityExplorer"', self.qingdao)
        self.assertNotIn('id="cityExplorerSearch"', self.qingdao)
        self.assertLess(self.qingdao.count('class="city-card'), 24)
        self.assertIn('href="../city-guides.html"', self.qingdao)

    def test_global_destination_menu_is_a_lightweight_province_gateway(self):
        self.assertIn('class="province-nav-list"', self.qingdao)
        self.assertIn('aria-label="按省份选择城市"', self.qingdao)
        self.assertIn('data-nav-group="直辖市"', self.qingdao)
        self.assertIn('data-nav-group="山东"', self.qingdao)
        self.assertNotIn("全国目的地", self.qingdao)
        self.assertNotIn('class="destination-quick"', self.qingdao)
        self.assertLessEqual(self.qingdao.count('class="destination-city'), 4)

    def test_recent_search_history_participates_in_local_backup_and_reset(self):
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn('"tay_search_recent"', script)
        self.assertRegex(script, r'STORAGE_ARRAY_KEYS[^\n]+tay_search_recent')
        self.assertRegex(script, r'ucResetAll[\s\S]+tay_search_recent')

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
        self.assertIn("scroll-snap-type: x mandatory", css)
        self.assertNotRegex(
            css,
            r"@media\s*\(max-width:\s*460px\)[\s\S]*?\.user-tabs\s*\{[^}]*display:\s*grid",
        )

    def test_mobile_navigation_respects_safe_areas_and_touch_targets(self):
        css = (ROOT / "assets" / "travel.css").read_text(encoding="utf-8")
        self.assertIn("env(safe-area-inset-bottom)", css)
        self.assertRegex(css, r"\.mobile-quickbar a\s*\{[^}]*min-height:\s*44px", re.S)
        self.assertIn("touch-action: manipulation", css)

    def test_mobile_hero_uses_a_compact_horizontal_decision_strip(self):
        css = (ROOT / "assets" / "travel.css").read_text(encoding="utf-8")
        self.assertRegex(
            css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.hero-points\s*\{[^}]*overflow-x:\s*auto[^}]*scroll-snap-type:\s*x mandatory",
        )

    def test_user_center_uses_keyboard_operable_aria_tabs(self):
        self.assertIn('role="tablist"', self.user)
        self.assertEqual(self.user.count('role="tab"'), 9)
        self.assertEqual(self.user.count('role="tabpanel"'), 9)
        self.assertIn('aria-selected="true"', self.user)
        self.assertIn('aria-controls="user-panel-profile"', self.user)
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        for marker in ('"ArrowRight"', '"ArrowLeft"', '"Home"', '"End"', "aria-selected"):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)

    def test_trip_workspace_is_available_across_discovery_and_city_pages(self):
        for page in (self.home, self.qingdao):
            for marker in (
                'id="tripDockToggle"',
                'id="tripDockCount"',
                'id="tripDock"',
                'id="tripDockList"',
                'id="tripDockClose"',
            ):
                with self.subTest(marker=marker):
                    self.assertIn(marker, page)
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        for marker in (
            "function renderTripDock",
            'window.addEventListener("tay:storage-change"',
            'event.key === "Escape"',
            "rootHref",
            "tripDockPreviousFocus",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)

    def test_trip_workspace_has_mobile_sheet_and_desktop_rail_layouts(self):
        css = (ROOT / "assets" / "travel.css").read_text(encoding="utf-8")
        self.assertIn(".trip-dock", css)
        self.assertRegex(css, r"\.trip-dock\s*\{[^}]*position:\s*fixed[^}]*right:\s*0", re.S)
        self.assertRegex(
            css,
            r"@media\s*\(max-width:\s*720px\)[\s\S]*?\.trip-dock\s*\{[^}]*left:\s*0[^}]*bottom:\s*0",
        )

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

    def test_public_pages_do_not_render_unverified_remote_images(self):
        pages = [ROOT / "index.html", *sorted((ROOT / "cities").glob("*.html"))]
        remote_images = []
        source_media_images = []
        for page in pages:
            html = page.read_text(encoding="utf-8")
            for match in re.finditer(r'<img\b[^>]*\bsrc="([^"]+)"', html, re.I):
                src = match.group(1)
                if src.startswith(("http://", "https://")):
                    remote_images.append((page.name, src))
                if "assets/photos/_sources/" in src:
                    source_media_images.append((page.name, src))
        self.assertEqual(
            remote_images,
            [],
            "external images must remain source links until republication rights are recorded",
        )
        self.assertEqual(
            source_media_images,
            [],
            "source-page media without explicit rights must not be copied into public pages",
        )

    def test_unreviewed_city_does_not_use_filesystem_mtime_as_travel_fact_date(self):
        beijing = (ROOT / "cities" / "beijing.html").read_text(encoding="utf-8")
        roadtrip_data = (ROOT / "assets" / "roadtrip-data.js").read_text(encoding="utf-8")
        self.assertIn("资料整理日期：未核验", beijing)
        self.assertRegex(roadtrip_data, r'"key":"beijing"[^}]*"updatedAt":"未核验"')

    def test_content_audit_exposes_raw_evidence_and_unreviewed_cities(self):
        audit = (ROOT / "docs" / "reports" / "内容与图片体检.md").read_text(encoding="utf-8")
        self.assertIn("原始字数", audit)
        self.assertIn("核验日期", audit)
        self.assertIn("未核验", audit)
        self.assertIn("封面衍生图不计为独立素材", audit)

    def test_local_storage_has_version_migration_and_cross_tab_contract(self):
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        for marker in (
            "tay_storage_meta",
            "STORAGE_SCHEMA",
            "migrateStorage",
            "tay:storage-change",
            "exportData",
            "importData",
        ):
            with self.subTest(marker=marker):
                self.assertIn(marker, script)

    def test_user_center_exposes_local_data_backup_and_restore(self):
        for control_id in ("dataExport", "dataImport", "dataTransferStatus"):
            with self.subTest(control_id=control_id):
                self.assertIn(f'id="{control_id}"', self.user)
        script = (ROOT / "assets" / "travel.js").read_text(encoding="utf-8")
        self.assertIn("dataExport", script)
        self.assertIn("dataImport", script)
        self.assertIn("importData", script)


if __name__ == "__main__":
    unittest.main()
