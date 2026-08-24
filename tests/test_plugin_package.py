"""The Codex marketplace package stays installable and mirrors public skills."""

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "flow-alignment"
MARKETPLACE = ROOT / ".agents" / "plugins" / "marketplace.json"
CLAUDE_MARKETPLACE = ROOT / ".claude-plugin" / "marketplace.json"
SYNC_SCRIPT = ROOT / "scripts" / "sync_plugin_skills.py"


class PluginPackage(unittest.TestCase):
    def test_marketplace_points_to_plugin(self):
        payload = json.loads(MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "flow-alignment")
        self.assertEqual(len(payload["plugins"]), 1)
        entry = payload["plugins"][0]
        self.assertEqual(entry["name"], "flow-alignment")
        self.assertEqual(entry["source"], {
            "source": "local",
            "path": "./plugins/flow-alignment",
        })
        self.assertEqual(entry["policy"]["installation"], "AVAILABLE")

    def test_bundled_skills_match_canonical_sources(self):
        result = subprocess.run(
            [sys.executable, str(SYNC_SCRIPT), "--check"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_claude_marketplace_points_to_same_plugin(self):
        payload = json.loads(CLAUDE_MARKETPLACE.read_text(encoding="utf-8"))
        self.assertEqual(payload["name"], "flow-alignment")
        self.assertEqual(len(payload["plugins"]), 1)
        entry = payload["plugins"][0]
        self.assertEqual(entry["name"], "flow-alignment")
        self.assertEqual(entry["source"], "./plugins/flow-alignment")

        manifest = json.loads(
            (PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], entry["name"])
        self.assertEqual(manifest["version"], entry["version"])

    def test_plugin_manifest_bundles_only_public_skills(self):
        bundled = sorted(path.name for path in (PLUGIN / "skills").iterdir() if path.is_dir())
        self.assertEqual(
            bundled,
            ["flow-alignment-prototype", "website-flow-reference"],
        )


if __name__ == "__main__":
    unittest.main()
