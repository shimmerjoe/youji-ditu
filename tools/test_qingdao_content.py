import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "城市" / "山东_青岛.md"


class QingdaoContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markdown = SOURCE.read_text(encoding="utf-8")

    def test_beer_museum_uses_the_current_official_schedule_and_ticket_rule(self):
        self.assertIn("1月1日至4月30日：08:30-17:30", self.markdown)
        self.assertIn("7月1日至8月31日：07:30-19:30", self.markdown)
        self.assertIn("微信公众号实名预约购票", self.markdown)
        self.assertNotIn("多为免费预约", self.markdown)

    def test_city_museum_is_not_confused_with_the_beer_museum(self):
        self.assertIn("青岛市博物馆", self.markdown)
        self.assertIn("免费开放、免预约入馆", self.markdown)
        self.assertIn("每周一闭馆（法定节假日除外）", self.markdown)

    def test_dynamic_information_has_a_review_date_and_official_sources(self):
        self.assertIn("动态信息核验日期：2026-07-15", self.markdown)
        self.assertIn("https://www.qdlaoshan.cn/", self.markdown)
        self.assertIn("https://www.qingdaomuseum.cn/visit", self.markdown)
        self.assertIn("articleTitleCus/1790371205849559041", self.markdown)


if __name__ == "__main__":
    unittest.main()
