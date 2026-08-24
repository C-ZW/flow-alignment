"""Checks that keep the public repository installable and intentionally scoped."""

import json
import re
import unittest
from pathlib import Path

from _support import ROOT


class ReleaseHygiene(unittest.TestCase):
    def test_readme_has_no_repository_url_placeholder(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("<repository" + "-url>", readme)

    def test_readme_installation_uses_the_public_marketplace(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        quick_install = readme.split("## Quick install", 1)[1].split(
            "## Skills", 1
        )[0]
        self.assertIn(
            "claude plugin marketplace add C-ZW/flow-alignment",
            quick_install,
        )
        self.assertIn(
            "codex plugin marketplace add C-ZW/flow-alignment",
            quick_install,
        )
        self.assertIn(
            "codex plugin marketplace upgrade flow-alignment",
            readme,
        )
        self.assertIn("claude plugin marketplace add ./ --scope local", readme)
        self.assertIn("codex plugin marketplace add ./", readme)
        self.assertNotIn("/absolute/path/to/flow-alignment", readme)
        self.assertNotIn("cp -R .claude/skills", readme)
        self.assertNotIn("git pull\ncodex plugin add", readme)

    def test_pages_workflow_deploys_the_standalone_demo(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github/workflows/pages.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("[Live prototype](https://c-zw.github.io/flow-alignment/)", readme)
        self.assertIn("prototypes/behind-your-day-purchase/prototype.html", workflow)
        self.assertIn("actions/upload-pages-artifact@v4", workflow)
        self.assertIn("actions/deploy-pages@v4", workflow)
        self.assertIn("pages: write", workflow)
        self.assertIn("id-token: write", workflow)

    def test_plugin_has_stable_version_and_license(self):
        plugin = ROOT / "plugins" / "flow-alignment"
        manifest = json.loads(
            (plugin / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertRegex(
            manifest["version"],
            r"^\d+\.\d+\.\d+(?:\+codex\.[0-9A-Za-z.-]+)?$",
        )
        self.assertEqual(
            (plugin / "LICENSE").read_text(encoding="utf-8"),
            (ROOT / "LICENSE").read_text(encoding="utf-8"),
        )

    def test_internal_blind_runs_are_not_shipped_as_examples(self):
        found = [
            path.relative_to(ROOT)
            for parent in (ROOT / "references", ROOT / "prototypes")
            if parent.is_dir()
            for path in parent.iterdir()
            if path.is_dir() and re.search(r"(?:^|-)blind(?:-|$)", path.name)
        ]
        self.assertEqual(found, [])

    def test_source_capture_license_boundary_is_documented(self):
        notice = (ROOT / "THIRD_PARTY_NOTICES.md").read_text(encoding="utf-8")
        for reference in sorted((ROOT / "references").glob("*/reference.json")):
            document = json.loads(reference.read_text(encoding="utf-8"))
            if any(item.get("kind") == "screenshot" for item in document.get("evidence", [])):
                expected = f"`references/{reference.parent.name}/screenshots/`"
                self.assertIn(expected, notice)

    def test_ci_covers_supported_python_versions(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )
        for version in ("3.10", "3.11", "3.12", "3.13", "3.14"):
            self.assertIn(f'"{version}"', workflow)
        self.assertIn("python scripts/validate_repository.py", workflow)


if __name__ == "__main__":
    unittest.main()
