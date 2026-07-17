import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PwaCacheTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sw = (ROOT / "sw.js").read_text(encoding="utf-8")
        cls.home = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_cache_name_tracks_the_current_build(self):
        self.assertRegex(self.sw, r"const CACHE='tay-[0-9a-f]{10}'")

    def test_navigation_is_network_first_so_rebuilds_are_visible(self):
        self.assertIn("e.request.mode==='navigate'", self.sw)
        self.assertIn("fetch(e.request)", self.sw)
        self.assertNotIn("return hit||net", self.sw)

    def test_scripts_and_styles_are_network_first_to_avoid_stale_interactions(self):
        self.assertIn("e.request.destination==='script'||e.request.destination==='style'", self.sw)
        self.assertIn("catch(_){return await c.match(e.request)||Response.error();}", self.sw)

    def test_app_shell_assets_have_a_build_version_for_existing_service_workers(self):
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
            "./assets/search-index.js",
            "./assets/icon-192.png",
        ):
            with self.subTest(resource=resource):
                self.assertIn(resource, self.sw)

    def test_install_does_not_download_large_destination_catalogs(self):
        for resource in (
            "./destinations.html",
            "./themes.html",
            "./city-guides.html",
            "./roadtrip.html",
            "./tools.html",
            "./user.html",
        ):
            with self.subTest(resource=resource):
                self.assertNotIn(resource, self.sw)


if __name__ == "__main__":
    unittest.main()
