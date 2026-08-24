import unittest

from tools.import_commons_city_photo import (
    commons_file_title,
    entry_from_commons_payload,
)


class CommonsCityPhotoImportTests(unittest.TestCase):
    def test_extracts_encoded_commons_file_title(self):
        url = "https://commons.wikimedia.org/wiki/File%3AForbidden_City_Panorama_1.jpg"
        self.assertEqual("File:Forbidden_City_Panorama_1.jpg", commons_file_title(url))

    def test_rejects_non_commons_sources(self):
        with self.assertRaises(ValueError):
            commons_file_title("https://example.com/wiki/File:photo.jpg")

    def test_builds_traceable_entry_from_api_payload(self):
        payload = {
            "query": {
                "pages": {
                    "1": {
                        "title": "File:Example.jpg",
                        "imageinfo": [{
                            "mime": "image/jpeg",
                            "thumburl": "https://upload.wikimedia.org/example.jpg",
                            "thumbwidth": 1600,
                            "thumbheight": 900,
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Example.jpg",
                            "extmetadata": {
                                "LicenseShortName": {"value": "CC BY-SA 4.0"},
                                "Artist": {"value": "<b>Example Artist</b>"},
                            },
                        }],
                    }
                }
            }
        }
        entry, image_url, width, height = entry_from_commons_payload(payload, "beijing")
        self.assertEqual("https://upload.wikimedia.org/example.jpg", image_url)
        self.assertEqual((1600, 900), (width, height))
        self.assertEqual("CC BY-SA 4.0", entry["license"])
        self.assertEqual("Example Artist", entry["artist"])
        self.assertEqual("assets/photos/beijing/cityphoto-src.jpg", entry["path"])

    def test_rejects_vertical_or_unlicensed_payloads(self):
        payload = {
            "query": {
                "pages": {
                    "1": {
                        "title": "File:Bad.jpg",
                        "imageinfo": [{
                            "mime": "image/jpeg",
                            "thumburl": "https://upload.wikimedia.org/bad.jpg",
                            "thumbwidth": 800,
                            "thumbheight": 1200,
                            "descriptionurl": "https://commons.wikimedia.org/wiki/File:Bad.jpg",
                            "extmetadata": {
                                "LicenseShortName": {"value": "Unknown"},
                                "Artist": {"value": ""},
                            },
                        }],
                    }
                }
            }
        }
        with self.assertRaises(ValueError):
            entry_from_commons_payload(payload, "beijing")


if __name__ == "__main__":
    unittest.main()
