import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class RoadtripBuildContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page_path = ROOT / "roadtrip.html"
        cls.page = cls.page_path.read_text(encoding="utf-8") if cls.page_path.exists() else ""
        cls.data_path = ROOT / "assets" / "roadtrip-data.js"
        cls.data_js = cls.data_path.read_text(encoding="utf-8") if cls.data_path.exists() else ""

    def test_roadtrip_page_contains_complete_planner_surface(self):
        required_ids = (
            "roadtripForm",
            "rtOrigin",
            "rtDestination",
            "rtDays",
            "rtTripType",
            "rtRouteStrategy",
            "rtVehicle",
            "rtMap",
            "rtResults",
            "rtSave",
            "rtExport",
            "rtShare",
            "rtPrint",
        )
        for element_id in required_ids:
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.page)

    def test_page_inlines_optional_map_config_before_runtime_assets(self):
        config_marker = "window.TRAVEL_ROADTRIP_CONFIG ="
        scripts = (
            config_marker,
            "assets/roadtrip-data.js",
            "assets/roadtrip-core.js",
            "assets/roadtrip-app.js",
        )
        positions = [self.page.find(script) for script in scripts]
        self.assertTrue(all(position >= 0 for position in positions), positions)
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("assets/roadtrip-config.js", self.page)

    def test_page_is_explicitly_non_transactional(self):
        self.assertIn("不提供站内交易", self.page)
        self.assertNotRegex(self.page, r"立即购买|立即下单|支付|优惠券|广告位")

    def test_city_data_has_planning_fields_for_all_guides(self):
        match = re.search(r"window\.TRAVEL_ROADTRIP_CITIES\s*=\s*(\[.*\]);", self.data_js, re.S)
        self.assertIsNotNone(match, "roadtrip-data.js does not expose city data")
        cities = json.loads(match.group(1))
        self.assertGreaterEqual(len(cities), 200)
        required = {"key", "province", "city", "title", "href", "highlights", "foods", "routes", "ticketEstimate", "sources", "updatedAt"}
        for city in cities:
            self.assertTrue(required.issubset(city), city)

    def test_navigation_and_homepage_link_to_the_planner(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('href="roadtrip.html"', index)
        self.assertIn("生成自驾路书", index)

    def test_page_uses_the_shared_full_width_catalog_masthead(self):
        self.assertIn('class="catalog-masthead reveal"', self.page)
        self.assertIn("Roadbook Studio", self.page)
        self.assertIn("离线可用", self.page)
        self.assertIn("路线与预算", self.page)

    def test_masthead_precedes_the_roadtrip_workbench(self):
        masthead = self.page.find('class="catalog-masthead reveal"')
        workbench = self.page.find('class="rt-workbench"')
        self.assertGreaterEqual(masthead, 0)
        self.assertGreater(workbench, masthead)

    def test_default_runtime_config_is_empty_and_never_requests_a_missing_file(self):
        self.assertRegex(
            self.page,
            r'window\.TRAVEL_ROADTRIP_CONFIG\s*=\s*\{"amapJsKey":"","amapSecurityCode":""\}',
        )
        self.assertNotIn("webServiceKey", self.page)

    def test_generator_accepts_explicit_build_time_browser_map_config(self):
        source = (ROOT / "tools" / "build_travel_html.py").read_text(encoding="utf-8")
        self.assertIn("TRAVEL_AMAP_JS_KEY", source)
        self.assertIn("TRAVEL_AMAP_SECURITY_CODE", source)

    def test_roadbook_uses_the_shared_versioned_storage_adapter(self):
        source = (ROOT / "tools" / "roadtrip-app.js").read_text(encoding="utf-8")
        self.assertIn("window.TAY_STORAGE", source)
        self.assertIn("storage.get('tay_roadtrips'", source)
        self.assertIn("storage.set('tay_roadtrips'", source)
        self.assertIn("renderPlan(last)", source)
        self.assertIn("encodeSharePlan", source)
        self.assertIn("decodeSharePlan", source)
        self.assertIn("location.hash", source)
        self.assertNotRegex(source, r"localStorage\.(?:getItem|setItem)\(['\"]tay_(?:roadtrips|last_roadtrip)")

    def test_roadbook_uses_three_progressive_form_steps(self):
        self.assertIn('class="rt-stepper"', self.page)
        self.assertEqual(self.page.count('class="rt-step"'), 3)
        for number in (1, 2, 3):
            self.assertIn(f'data-rt-step="{number}"', self.page)
            self.assertIn(f'data-rt-step-target="{number}"', self.page)
        source = (ROOT / "tools" / "roadtrip-app.js").read_text(encoding="utf-8")
        self.assertIn("function setRoadtripStep", source)
        self.assertIn("form.classList.add('rt-stepped')", source)

    def test_empty_map_and_result_actions_expand_only_after_a_plan_exists(self):
        self.assertIn('class="rt-map-frame is-idle"', self.page)
        self.assertRegex(self.page, r'class="rt-result-actions"[^>]*hidden')
        source = (ROOT / "tools" / "roadtrip-app.js").read_text(encoding="utf-8")
        self.assertIn("mapFrame.classList.remove('is-idle')", source)
        self.assertIn("resultActions.hidden = false", source)


if __name__ == "__main__":
    unittest.main()
