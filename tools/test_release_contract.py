import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseContractTests(unittest.TestCase):
    def test_pages_workflow_runs_the_locked_full_check_and_deploys_dist(self):
        workflow = ROOT / ".github" / "workflows" / "pages.yml"
        self.assertTrue(workflow.is_file(), "GitHub Pages workflow is missing")
        source = workflow.read_text(encoding="utf-8")
        self.assertIn("npm ci", source)
        self.assertIn("npm run check", source)
        self.assertIn("npm run stage", source)
        self.assertIn("actions/upload-pages-artifact@", source)
        self.assertIn("path: dist", source)
        self.assertIn("actions/deploy-pages@", source)

    def test_stager_uses_an_allowlist_instead_of_copying_the_repository(self):
        source = (ROOT / "tools" / "stage_pages.py").read_text(encoding="utf-8")
        self.assertIn("ROOT_FILES", source)
        self.assertIn("ROOT_DIRECTORIES", source)
        self.assertNotIn("copytree(ROOT,", source)

    def test_package_exposes_a_repeatable_stage_command(self):
        package = (ROOT / "package.json").read_text(encoding="utf-8")
        self.assertIn('"stage": "python -X utf8 tools/stage_pages.py"', package)

    def test_pages_workflow_installs_the_pinned_python_build_dependency(self):
        workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
        requirements = ROOT / "tools" / "requirements-build.txt"
        self.assertTrue(requirements.is_file())
        self.assertIn("Pillow==12.2.0", requirements.read_text(encoding="utf-8"))
        self.assertIn("python -m pip install -r tools/requirements-build.txt", workflow)


if __name__ == "__main__":
    unittest.main()
