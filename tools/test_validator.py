import unittest
from pathlib import Path

from validate_travel_site import LinkParser, split_local_link


class ValidatorParserTests(unittest.TestCase):
    def test_parser_tracks_duplicate_ids_and_images_without_alt_text(self):
        parser = LinkParser()
        parser.feed(
            '<main id="content"><section id="content"></section>'
            '<img src="photo.jpg"><img src="decorative.jpg" alt=""></main>'
        )
        self.assertEqual(["content"], parser.duplicate_ids)
        self.assertEqual(["photo.jpg"], parser.images_missing_alt)

    def test_local_links_ignore_cache_query_strings_when_resolving_files(self):
        self.assertEqual(("assets/travel.js", "guide"), split_local_link("assets/travel.js?v=abc123#guide"))

    def test_generated_pages_do_not_include_trailing_whitespace(self):
        root = Path(__file__).resolve().parents[1]
        for page in (root / "index.html", root / "cities" / "qingdao.html"):
            with self.subTest(page=page.name):
                self.assertTrue(all(line == line.rstrip() for line in page.read_text(encoding="utf-8").splitlines()))


if __name__ == "__main__":
    unittest.main()
