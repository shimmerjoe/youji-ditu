import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BrowserAuditTests(unittest.TestCase):
    def test_audit_waits_for_dom_readiness_instead_of_global_network_idle(self):
        source = (ROOT / "tools" / "browser_audit.py").read_text(encoding="utf-8")
        self.assertIn('wait_until="domcontentloaded"', source)
        self.assertNotIn('wait_until="networkidle"', source)

    def test_hidden_image_placeholders_do_not_count_as_broken_media(self):
        source = (ROOT / "tools" / "browser_audit.py").read_text(encoding="utf-8")
        self.assertIn(".filter((img) => (img.currentSrc || img.src) && img.complete && img.naturalWidth === 0)", source)
        self.assertIn(".filter((img) => (img.currentSrc || img.src) && (!img.hasAttribute('width') || !img.hasAttribute('height')))", source)

    def test_city_images_reserve_intrinsic_layout_space(self):
        source = (ROOT / "tools" / "build_travel_html.py").read_text(encoding="utf-8")
        self.assertIn('width="800" height="480"', source)
        self.assertIn('width="1200" height="675"', source)

    def test_generated_pages_size_every_real_image(self):
        for page_name in ("index.html", "cities/qingdao.html"):
            page = (ROOT / page_name).read_text(encoding="utf-8")
            images = [tag for tag in re.findall(r"<img\b[^>]*>", page) if re.search(r'\bsrc="[^"]+"', tag)]
            with self.subTest(page=page_name):
                self.assertTrue(images)
                for image in images:
                    self.assertRegex(image, r'\bwidth="\d+"')
                    self.assertRegex(image, r'\bheight="\d+"')


if __name__ == "__main__":
    unittest.main()
