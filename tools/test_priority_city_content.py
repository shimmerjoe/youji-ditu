import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CITY_DIR = ROOT / "城市"


class PriorityCityContentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sanya = (CITY_DIR / "海南_三亚.md").read_text(encoding="utf-8")
        cls.wanning = (CITY_DIR / "海南_万宁.md").read_text(encoding="utf-8")
        cls.nanchang = (CITY_DIR / "江西_南昌.md").read_text(encoding="utf-8")
        cls.jinhua = (CITY_DIR / "浙江_金华.md").read_text(encoding="utf-8")
        cls.chuzhou = (CITY_DIR / "安徽_滁州.md").read_text(encoding="utf-8")

    def test_priority_guides_replace_generic_attraction_copy(self):
        generic = "核心景观、城市地标、历史文化或自然风光"
        for name, text in {
            "sanya": self.sanya,
            "wanning": self.wanning,
            "nanchang": self.nanchang,
        }.items():
            with self.subTest(city=name):
                self.assertNotIn(generic, text)
                self.assertIn("动态信息核验日期：2026-07-15", text)

    def test_sanya_has_current_free_entry_and_crowd_check_guidance(self):
        self.assertIn("天涯海角自 2023 年 6 月 1 日起免门票开放", self.sanya)
        self.assertIn("三亚放心游", self.sanya)
        self.assertIn("景区客流可视化", self.sanya)
        self.assertIn("english.sanya.gov.cn/syen/news/202605", self.sanya)
        self.assertIn("ty.sanya.gov.cn/tyqsite/jrty/202602", self.sanya)

    def test_wanning_uses_the_current_four_area_route_structure(self):
        self.assertIn("日月湾、兴隆旅游区、石梅湾、神州半岛四大片区", self.wanning)
        self.assertIn("不要在同一天反复横跨海岸线", self.wanning)
        self.assertIn("news.hainan.net/zixun/2026/07/13/4805767.shtml", self.wanning)
        self.assertIn("mee.gov.cn/home/ztbd/2021/mlhwyxalzjhd", self.wanning)

    def test_nanchang_distinguishes_open_areas_and_current_excursion_bus(self):
        self.assertIn("90% 区域向全民免费开放", self.nanchang)
        self.assertIn("主楼等收费项目不能据此视为全部免费", self.nanchang)
        self.assertIn("百丈山", self.nanchang)
        self.assertIn("龙源峡 + 云居山", self.nanchang)
        self.assertIn("50 元/人（往返）", self.nanchang)
        self.assertIn("gzw.nc.gov.cn/ncsgzw/gzdt/202606/580bbac4", self.nanchang)

    def test_jinhua_separates_the_city_and_county_level_routes(self):
        self.assertNotIn("核心景观、城市地标、历史文化或自然风光", self.jinhua)
        self.assertIn("动态信息核验日期：2026-07-15", self.jinhua)
        self.assertIn("婺城城区、金华山、东阳横店、兰溪诸葛村是四条不同方向", self.jinhua)
        self.assertIn("不要把横店影视城和双龙风景旅游区硬塞进同一天", self.jinhua)
        self.assertIn("shuanglongdong.com", self.jinhua)
        self.assertIn("hengdianworld.com", self.jinhua)

    def test_chuzhou_separates_langya_mountain_and_fengyang(self):
        self.assertNotIn("核心景观、城市地标、历史文化或自然风光", self.chuzhou)
        self.assertIn("动态信息核验日期：2026-07-15", self.chuzhou)
        self.assertIn("琅琊山与凤阳不是同一片区", self.chuzhou)
        self.assertIn("明中都皇故城国家考古遗址公园", self.chuzhou)
        self.assertIn("中国滁州政府门户网站", self.chuzhou)


if __name__ == "__main__":
    unittest.main()
