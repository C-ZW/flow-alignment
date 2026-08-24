"""Product fragments are the only authoring surface for generated prototypes."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import ROOT, template_spec


SCRIPT = (
    ROOT
    / ".claude"
    / "skills"
    / "flow-alignment-prototype"
    / "scripts"
    / "build_prototype.py"
)


class BuildPrototype(unittest.TestCase):
    def run_script(self, artifact: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(artifact), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_builder_owns_generic_markup_and_preserves_product_fragments(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "prototypes" / "built-flow"
            initialized = self.run_script(artifact, "--init")
            self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
            self.assertIn("authoring fragments only", initialized.stdout)
            self.assertIn("author flow.json and walkthrough.md", initialized.stdout)
            (artifact / "flow.json").write_text(
                json.dumps(template_spec(), indent=2) + "\n",
                encoding="utf-8",
            )
            shell = artifact / "authoring" / "product-shell.html"
            shell.write_text(
                shell.read_text(encoding="utf-8").replace(
                    "[PRODUCT LOGO]", "Example product", 1
                ),
                encoding="utf-8",
            )

            built = self.run_script(artifact)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            output = artifact / "prototype.html"
            self.assertIn("Example product", output.read_text(encoding="utf-8"))
            self.assertEqual(self.run_script(artifact, "--check").returncode, 0)

            output.write_text(
                output.read_text(encoding="utf-8").replace(
                    "font-size: 13px", "font-size: 12px", 1
                ),
                encoding="utf-8",
            )
            self.assertEqual(self.run_script(artifact, "--check").returncode, 1)
            self.assertEqual(self.run_script(artifact).returncode, 0)
            self.assertNotIn("font-size: 12px", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
