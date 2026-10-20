import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageStat
from tools import build_travel_html as builder


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "assets" / "photo-cache.json"
EDITORIAL_PATH = ROOT / "assets" / "photo-editorial-decisions.json"
CITY_SLUGS = ("jinhua", "wanning", "sanya", "chuzhou", "nanchang")
APPROVED_CREDIT_SLUGS = (
    "beijing",
    "tianjin",
    "lhasa",
    "dunhuang",
    "kunming",
    "nanning",
    "lijiang",
    "yanan",
    "xiamen",
    "beihai",
    "changsha",
    "urumqi",
    "lanzhou",
    "haikou",
)
REJECTED_CREDIT_SLUGS = ("benxi", "city-cd061af662")
PLACEHOLDER_LICENSES = {"", "unknown", "wikipedia", "wikimedia commons"}


class PriorityCityImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))

    @staticmethod
    def rejected_xiamen_fixture():
        decision = json.loads(EDITORIAL_PATH.read_text(encoding="utf-8"))["decisions"]["xiamen"]
        return {
            "status": "hit",
            "path": "assets/photos/xiamen/editorially-rejected-fixture.jpg",
            "source": decision["source"],
            "license": "CC BY-SA 3.0",
            "artist": "Editorial fixture",
            "query": "fixture",
        }

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

    def test_published_city_photo_cache_uses_reproducible_cover_derivatives(self):
        primary_hits = {
            key: entry for key, entry in self.cache.items()
            if key.startswith("cityphoto|") and key.count("|") == 1 and entry.get("status") == "hit"
        }
        self.assertGreaterEqual(len(primary_hits), 200)
        for key, entry in primary_hits.items():
            slug = key.split("|", 1)[1]
            expected = f"assets/images/{slug}.jpg"
            with self.subTest(city=slug):
                self.assertEqual(expected, entry["path"])
                self.assertTrue((ROOT / expected).exists())

    def test_image_cleanup_preserves_cache_backed_cover_and_removes_stale_output(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir)
            images = output / "assets" / "images"
            images.mkdir(parents=True)
            kept = images / "kept.jpg"
            stale = images / "stale.jpg"
            kept.write_bytes(b"licensed-cover")
            stale.write_bytes(b"obsolete-output")
            cache = {
                "cityphoto|kept": {
                    "status": "hit",
                    "path": "assets/images/kept.jpg",
                    "source": "https://commons.wikimedia.org/wiki/File:Kept.jpg",
                    "license": "CC0 1.0",
                    "artist": "",
                }
            }

            with (
                patch.object(builder, "OUT", output),
                patch.object(builder, "IMAGES", images),
                patch.object(builder, "PHOTO_CACHE", cache),
                patch.object(builder, "PHOTO_CACHE_LOADED", True),
            ):
                builder.prepare_image_output()

            self.assertEqual(b"licensed-cover", kept.read_bytes())
            self.assertFalse(stale.exists())

    def test_jinhua_and_chuzhou_have_three_local_gallery_sources(self):
        for slug in ("jinhua", "chuzhou"):
            with self.subTest(city=slug):
                photo_dir = ROOT / "assets" / "photos" / slug
                photos = [ROOT / self.cache[f"cityphoto|{slug}"]["path"]] + [
                    path for path in photo_dir.iterdir()
                    if path.name.startswith("scenery-")
                    and path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
                ]
                self.assertGreaterEqual(len(photos), 3)
                self.assertTrue(all(path.exists() for path in photos))
                self.assertTrue(any(path.name.startswith("scenery-") for path in photos))

    def test_published_city_photos_have_republication_metadata(self):
        for key, entry in self.cache.items():
            if not key.startswith("cityphoto|") or entry.get("status") != "hit":
                continue
            with self.subTest(cache_key=key):
                license_name = str(entry.get("license", "")).strip()
                artist = str(entry.get("artist", "")).strip()
                source = str(entry.get("source", "")).strip()
                self.assertNotIn(license_name.lower(), PLACEHOLDER_LICENSES)
                self.assertIn("commons.wikimedia.org/wiki/File:", source)
                if " BY" in f" {license_name.upper()}" or "ATTRIBUTION" in license_name.upper():
                    self.assertTrue(artist, "attribution licenses require a named creator")

    def test_rejected_city_photos_are_not_published_as_hits(self):
        rejected = {
            "cityphoto|benxi",
            "cityphoto|city-cd061af662",
            "cityphoto|city-e3ec02a30b",
        }
        for key in rejected:
            with self.subTest(cache_key=key):
                self.assertEqual("rejected", self.cache[key]["status"])
                self.assertTrue(self.cache[key].get("rejection_reason"))

    def test_editorial_rejections_are_explained_and_source_scoped(self):
        payload = json.loads(EDITORIAL_PATH.read_text(encoding="utf-8"))
        self.assertEqual(1, payload["schemaVersion"])
        decisions = payload["decisions"]
        self.assertIn("beihai", decisions)
        self.assertIn("yanan", decisions)
        self.assertIn("xiamen", decisions)
        for slug, decision in decisions.items():
            with self.subTest(city=slug):
                entry = self.cache[f"cityphoto|{slug}"]
                self.assertEqual("rejected", decision["status"])
                self.assertIn("commons.wikimedia.org/wiki/File:", decision["source"])
                self.assertTrue(decision["reason"].strip())
                self.assertRegex(decision["reviewedAt"], r"^\d{4}-\d{2}-\d{2}$")
                for previous in decision.get("previousRejections", []):
                    self.assertIn("commons.wikimedia.org/wiki/File:", previous["source"])
                    self.assertTrue(previous["reason"].strip())
                    self.assertRegex(previous["reviewedAt"], r"^\d{4}-\d{2}-\d{2}$")
                if entry.get("source") == decision["source"]:
                    self.assertFalse(builder.photo_is_publishable(entry, slug))
                else:
                    self.assertTrue(
                        builder.photo_is_publishable(entry, slug),
                        "a replacement source must pass the rights gate and reopen review",
                    )

    def test_replacing_a_rejected_source_reopens_editorial_review(self):
        old_entry = self.rejected_xiamen_fixture()
        self.assertFalse(builder.photo_is_publishable(old_entry, "xiamen"))
        replacement = {
            **old_entry,
            "source": "https://commons.wikimedia.org/wiki/File:Replacement_Xiamen.jpg",
        }
        self.assertTrue(builder.photo_is_publishable(replacement, "xiamen"))

    def test_failed_refresh_preserves_rejected_source_evidence(self):
        old_entry = self.rejected_xiamen_fixture()
        result = builder.photo_cache_entry_after_miss("xiamen", old_entry, "new query")
        self.assertEqual(old_entry, result)

    def test_editorially_rejected_photos_render_as_text_cards(self):
        decisions = json.loads(EDITORIAL_PATH.read_text(encoding="utf-8"))["decisions"]
        catalog = (ROOT / "city-guides.html").read_text(encoding="utf-8")
        no_image_keys = set(
            re.findall(r'<article class="city-card noimg"[^>]+data-key="([^"]+)"', catalog)
        )
        active_rejections = {
            slug
            for slug, decision in decisions.items()
            if self.cache[f"cityphoto|{slug}"].get("source") == decision["source"]
        }
        replacements = set(decisions) - active_rejections
        for slug in active_rejections:
            with self.subTest(city=slug):
                self.assertIn(slug, no_image_keys)
        for slug in replacements:
            with self.subTest(replacement=slug):
                self.assertNotIn(slug, no_image_keys)

    def test_editorial_rejections_are_visible_in_the_content_audit(self):
        decisions = json.loads(EDITORIAL_PATH.read_text(encoding="utf-8"))["decisions"]
        audit = (ROOT / "docs" / "reports" / "内容与图片体检.md").read_text(encoding="utf-8")
        self.assertIn("图片内容审核拒绝清单", audit)
        for slug, decision in decisions.items():
            if self.cache[f"cityphoto|{slug}"].get("source") != decision["source"]:
                continue
            with self.subTest(city=slug):
                self.assertIn(decision["reason"], audit)

    def test_approved_city_cover_credits_expose_creator_license_and_source(self):
        pages = {page.key: page for page in builder.PAGES}
        for slug in APPROVED_CREDIT_SLUGS:
            with self.subTest(city=slug):
                page = pages[slug]
                entry = self.cache[f"cityphoto|{slug}"]
                credit = builder.city_cover_credit_html(page)
                self.assertIn('class="hero-photo-credit"', credit)
                self.assertIn(entry["artist"], credit)
                self.assertIn(entry["license"], credit)
                self.assertIn(f'href="{entry["source"]}"', credit)
                self.assertIn('target="_blank"', credit)
                self.assertIn('rel="noopener noreferrer"', credit)
                self.assertIn("新窗口", credit)

    def test_approved_city_pages_render_specific_cover_credits(self):
        for slug in APPROVED_CREDIT_SLUGS:
            with self.subTest(city=slug):
                entry = self.cache[f"cityphoto|{slug}"]
                output = (ROOT / "cities" / f"{slug}.html").read_text(encoding="utf-8")
                self.assertIn('class="hero-photo-credit"', output)
                self.assertIn(entry["artist"], output)
                self.assertIn(entry["license"], output)
                self.assertIn(entry["source"], output)

    def test_rejected_city_cover_credits_stay_hidden(self):
        pages = {page.key: page for page in builder.PAGES}
        for slug in REJECTED_CREDIT_SLUGS:
            with self.subTest(city=slug):
                page = pages[slug]
                entry = self.cache[f"cityphoto|{slug}"]
                self.assertFalse(builder.photo_is_publishable(entry, slug))
                self.assertEqual("", builder.city_cover_credit_html(page))
                output = (ROOT / "cities" / f"{slug}.html").read_text(encoding="utf-8")
                self.assertNotIn('class="hero-photo-credit"', output)


if __name__ == "__main__":
    unittest.main()
