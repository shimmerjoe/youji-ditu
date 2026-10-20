import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NodeBuildContractTests(unittest.TestCase):
    def test_package_exposes_one_reproducible_build_entrypoint(self):
        package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package.get("private"), True)
        self.assertIn("vite", package.get("devDependencies", {}))
        self.assertIn("typescript", package.get("devDependencies", {}))
        self.assertIn("build:app", package.get("scripts", {}))
        self.assertIn("build_travel_html.py", package["scripts"]["build"])

    def test_vite_manifest_is_consumed_by_generated_pages(self):
        manifest_path = ROOT / "site" / "assets" / "vite-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        entries = [entry for entry in manifest.values() if entry.get("isEntry")]
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertTrue((ROOT / "site" / "assets" / entry["file"]).is_file())
        qingdao = (ROOT / "site" / "cities" / "qingdao.html").read_text(encoding="utf-8")
        self.assertRegex(
            qingdao,
            rf'<script type="module" src="\.\./assets/{re.escape(entry["file"])}\?v=[a-f0-9]+"></script>',
        )
        for css_file in entry.get("css", []):
            self.assertTrue((ROOT / "site" / "assets" / css_file).is_file())
            self.assertIn(f'../assets/{css_file}?v=', qingdao)

    def test_static_city_content_remains_available_without_the_app_module(self):
        qingdao = (ROOT / "site" / "cities" / "qingdao.html").read_text(encoding="utf-8")
        self.assertIn("山东青岛旅游攻略", qingdao)
        self.assertIn('<article class="content" id="guideContent">', qingdao)
        self.assertIn("<noscript>", qingdao)


if __name__ == "__main__":
    unittest.main()
