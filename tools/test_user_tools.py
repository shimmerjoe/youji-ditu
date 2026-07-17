import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
USER_HTML = ROOT / "user.html"
TRAVEL_JS = ROOT / "assets" / "travel.js"
SEARCH_INDEX = ROOT / "assets" / "search-index.js"
QINGDAO_HTML = ROOT / "cities" / "qingdao.html"


class UserToolsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.user_html = USER_HTML.read_text(encoding="utf-8")
        cls.travel_js = TRAVEL_JS.read_text(encoding="utf-8")
        cls.search_index = SEARCH_INDEX.read_text(encoding="utf-8")
        cls.qingdao_html = QINGDAO_HTML.read_text(encoding="utf-8")

    def test_user_center_has_a_functional_travel_tools_panel(self):
        self.assertIn('data-tab="tools"', self.user_html)
        self.assertIn('data-panel="tools"', self.user_html)
        for element_id in (
            "travelChecklist",
            "checklistInput",
            "checklistAdd",
            "budgetList",
            "budgetName",
            "budgetAmount",
            "budgetAdd",
            "budgetTotal",
            "travelNotes",
            "toolsExport",
        ):
            with self.subTest(element_id=element_id):
                self.assertIn(f'id="{element_id}"', self.user_html)

    def test_travel_tools_use_local_storage_and_support_markdown_export(self):
        for key in ("tay_checklist", "tay_budget", "tay_notes"):
            with self.subTest(storage_key=key):
                self.assertIn(f'"{key}"', self.travel_js)
        self.assertIn("new Blob", self.travel_js)
        self.assertIn("旅行工作台.md", self.travel_js)

    def test_reset_clears_all_travel_tool_data(self):
        reset_block = re.search(
            r'const reset = document\.getElementById\("ucResetAll"\);.*?location\.reload\(\);',
            self.travel_js,
            re.S,
        )
        self.assertIsNotNone(reset_block)
        for key in ("tay_checklist", "tay_budget", "tay_notes"):
            self.assertIn(key, reset_block.group(0))

    def test_user_center_city_counts_are_generated_from_current_content(self):
        self.assertNotIn("190</strong><span>可逛城市", self.user_html)
        self.assertRegex(self.user_html, r'<strong>222</strong><span>可逛城市</span>')
        self.assertIn("覆盖地区", self.user_html)

    def test_trip_cities_can_be_compared_with_current_city_metadata(self):
        self.assertIn('id="tripCompare"', self.user_html)
        self.assertIn('id="tripCompareTable"', self.user_html)
        self.assertIn('"key": "qingdao"', self.search_index)
        self.assertIn('"season":', self.search_index)
        self.assertIn('getElementById("tripCompare")', self.travel_js)
        self.assertIn('class="trip-compare-table"', self.travel_js)

    def test_city_page_share_uses_native_share_with_clipboard_fallback(self):
        self.assertIn('class="co-share"', self.qingdao_html)
        self.assertIn('aria-label="分享山东青岛旅游攻略"', self.qingdao_html)
        self.assertIn("navigator.share", self.travel_js)
        self.assertIn("navigator.clipboard", self.travel_js)


if __name__ == "__main__":
    unittest.main()
