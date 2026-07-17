import json
import unittest
from pathlib import Path

from PIL import Image, ImageStat


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "assets" / "photo-cache.json"
CITY_SLUGS = ("jinhua", "wanning", "sanya", "chuzhou", "nanchang")


class PriorityCityImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    def test_priority_city_covers_are_real_local_photos(self):
        for slug in CITY_SLUGS:
            with self.subTest(city=slug):
                cover = ROOT / "assets" / "images" / f"{slug}.jpg"
                self.assertTrue(cover.exists())
                with Image.open(cover) as image:
                    self.assertGreaterEqual(image.width, 1200)
                    self.assertGreaterEqual(image.height, 675)
                    variation = sum(ImageStat.Stat(image.convert("RGB")).stddev)
                    self.assertGreater(variation, 20, "cover must not be a solid placeholder")

    def test_priority_city_photos_have_distinct_traceable_licenses(self):
        sources = set()
        for slug in CITY_SLUGS:
            with self.subTest(city=slug):
                entry = self.cache[f"cityphoto|{slug}"]
                self.assertEqual("hit", entry["status"])
                self.assertIn("commons.wikimedia.org/wiki/File:", entry["source"])
                self.assertNotIn("CADAL", entry["source"])
                self.assertTrue(entry["license"])
                self.assertTrue(entry.get("title"))
                self.assertTrue((ROOT / entry["path"]).exists())
                sources.add(entry["source"])
        self.assertEqual(len(CITY_SLUGS), len(sources))

    def test_jinhua_and_chuzhou_have_three_local_gallery_sources(self):
        for slug in ("jinhua", "chuzhou"):
            with self.subTest(city=slug):
                photo_dir = ROOT / "assets" / "photos" / slug
                photos = [
                    path for path in photo_dir.iterdir()
                    if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                ]
                self.assertGreaterEqual(len(photos), 3)
                self.assertTrue(any(path.name.startswith("scenery-") for path in photos))


if __name__ == "__main__":
    unittest.main()
