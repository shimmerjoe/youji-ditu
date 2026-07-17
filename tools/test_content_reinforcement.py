import re
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


class ContentReinforcementTests(unittest.TestCase):
    def test_every_city_has_one_nonduplicated_local_body_image(self):
        for page in (ROOT / "cities").glob("*.html"):
            with self.subTest(page=page.name):
                html = page.read_text(encoding="utf-8")
                images = re.findall(r'src="\.\./assets/photos/[^\"]+/scenery-[^\"]+"', html)
                self.assertEqual(1, len(images))

    def test_generated_body_gallery_uses_a_mobile_ready_derivative(self):
        for slug in ("jinhua", "chuzhou"):
            with self.subTest(city=slug):
                photos = sorted((ROOT / "assets" / "photos" / slug).glob("scenery-[0-9][0-9].jpg"))
                self.assertEqual(1, len(photos))
                with Image.open(photos[0]) as image:
                    self.assertEqual((960, 540), image.size)

    def test_generated_audit_has_no_reinforcement_backlog(self):
        audit = (ROOT / "内容与图片体检.md").read_text(encoding="utf-8")
        self.assertIn("需要优先补充：0", audit)


if __name__ == "__main__":
    unittest.main()
