import re
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class ContentReinforcementTests(unittest.TestCase):
    def test_city_pages_do_not_repeat_the_cover_as_a_body_gallery(self):
        # The full-bleed hero already shows the licensed cover; a cropped copy of
        # the same photo further down the page is not an independent asset.
        for page in (ROOT / "site" / "cities").glob("*.html"):
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                images = re.findall(r'src="\.\./assets/photos/[^\"]+/scenery-[^\"]+"', html)
                self.assertEqual(0, len(images))

    def test_generated_body_gallery_uses_a_mobile_ready_derivative(self):
        for slug in ("jinhua", "chuzhou"):
            with self.subTest(city=slug):
                photos = sorted((ROOT / "site" / "assets" / "photos" / slug).glob("scenery-[0-9][0-9].jpg"))
                self.assertEqual(1, len(photos))
                with Image.open(photos[0]) as image:
                    self.assertEqual((960, 540), image.size)

    def test_short_guides_are_not_padded_with_a_generic_appendix(self):
        for page in (ROOT / "site" / "cities").glob("*.html"):
            with self.subTest(page=page.name):
                self.assertNotIn("行程执行补强", page.read_text(encoding="utf-8"))

    def test_generated_audit_does_not_hide_reinforcement_backlog(self):
        audit = (ROOT / "docs" / "reports" / "内容与图片体检.md").read_text(encoding="utf-8")
        self.assertRegex(audit, r"需要优先补充：\d+")
        self.assertIn("原始字数", audit)
        self.assertIn("封面衍生图不计为独立素材", audit)


if __name__ == "__main__":
    unittest.main()
