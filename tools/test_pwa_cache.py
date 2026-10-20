import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PwaCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sw = (ROOT / "site" / "sw.js").read_text(encoding="utf-8")
        cls.home = (ROOT / "site" / "index.html").read_text(encoding="utf-8")

    def test_cache_name_tracks_the_current_build(self):
        self.assertRegex(self.sw, r"const CACHE='tay-[0-9a-f]{10}'")

    def test_navigation_is_network_first_so_rebuilds_are_visible(self):
        self.assertIn("e.request.mode==='navigate'", self.sw)
        self.assertIn("fetch(e.request)", self.sw)
        self.assertNotIn("return hit||net", self.sw)

    def test_navigation_has_a_readable_offline_fallback(self):
        self.assertIn("return await c.match(e.request)||offlineResponse()", self.sw)
        self.assertNotIn("c.match(OFFLINE_FALLBACK)", self.sw)
        self.assertIn("离线", self.sw)
        self.assertIn("status:503", self.sw)

    def test_scripts_and_styles_are_network_first_to_avoid_stale_interactions(self):
        self.assertIn("e.request.destination==='script'||e.request.destination==='style'", self.sw)
        self.assertIn("catch(_){return await c.match(e.request)||Response.error();}", self.sw)

    def test_runtime_assets_have_a_build_version_for_existing_service_workers(self):
        for asset in ("travel.css", "search-index.js", "travel.js"):
            with self.subTest(asset=asset):
                self.assertRegex(self.home, rf'assets/{re.escape(asset)}\?v=[0-9a-f]{{10}}')

    def test_activation_removes_previous_build_caches(self):
        self.assertIn("caches.keys()", self.sw)
        self.assertIn("caches.delete", self.sw)

    def test_install_precaches_the_offline_app_shell(self):
        self.assertIn("const APP_SHELL=", self.sw)
        self.assertIn("c.addAll(APP_SHELL)", self.sw)
        for resource in (
            "./index.html",
            "./assets/travel.css",
            "./assets/travel.js",
            "./assets/icon-192.png",
        ):
            with self.subTest(resource=resource):
                self.assertIn(resource, self.sw)

    def test_large_search_index_is_cached_only_after_the_user_searches(self):
        self.assertNotIn("./assets/search-index.js?v=", self.sw)

    def test_install_does_not_download_large_destination_catalogs(self):
        for resource in (
            "./destinations.html",
            "./themes.html",
            "./city-guides.html",
            "./tools.html",
            "./user.html",
        ):
            with self.subTest(resource=resource):
                self.assertNotIn(resource, self.sw)

    def test_on_trip_tools_work_offline_without_a_prior_visit(self):
        # 行程计划和自驾路书是旅途中（常常没信号）才打开的页面，必须随安装预缓存。
        for resource in ("./plan.html", "./roadtrip.html", "./assets/roadtrip-app.js", "./assets/travel-chunk-"):
            with self.subTest(resource=resource):
                self.assertIn(resource, self.sw)


if __name__ == "__main__":
    unittest.main()
