import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_BASE = "https://shimmerjoe.github.io/youji-ditu/"


class SeoContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.city = (ROOT / "cities" / "qingdao.html").read_text(encoding="utf-8")
        cls.sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8") if (ROOT / "sitemap.xml").exists() else ""
        cls.robots = (ROOT / "robots.txt").read_text(encoding="utf-8") if (ROOT / "robots.txt").exists() else ""

    def test_pages_expose_absolute_canonical_and_share_metadata(self):
        self.assertIn(f'<link rel="canonical" href="{PUBLIC_BASE}">', self.index)
        self.assertIn(f'<link rel="canonical" href="{PUBLIC_BASE}cities/qingdao.html">', self.city)
        for page in (self.index, self.city):
            self.assertIn('property="og:url"', page)
            self.assertIn('property="og:site_name"', page)
            self.assertIn('name="twitter:card"', page)

    def test_sitemap_and_robots_are_generated_for_the_public_deployment(self):
        self.assertIn("<urlset", self.sitemap)
        self.assertIn(f"<loc>{PUBLIC_BASE}</loc>", self.sitemap)
        self.assertIn(f"<loc>{PUBLIC_BASE}cities/qingdao.html</loc>", self.sitemap)
        self.assertIn("User-agent: *", self.robots)
        self.assertIn(f"Sitemap: {PUBLIC_BASE}sitemap.xml", self.robots)


if __name__ == "__main__":
    unittest.main()
