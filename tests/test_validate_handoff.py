"""The portable handoff command makes artifact completion mechanically checkable."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import ROOT


SCRIPT = (
    ROOT
    / ".claude"
    / "skills"
    / "flow-alignment-prototype"
    / "scripts"
    / "validate_handoff.py"
)


class ValidateHandoff(unittest.TestCase):
    def test_repository_demo_passes_the_complete_gate(self):
        artifact = ROOT / "prototypes" / "behind-your-day-purchase"
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(artifact), "--require-preview"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("deterministic handoff gates passed", result.stdout)
        self.assertIn("Runtime browser walks remain required", result.stdout)

    def test_missing_walkthrough_blocks_handoff_before_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = Path(directory) / "prototypes" / "incomplete-flow"
            artifact.mkdir(parents=True)
            (artifact / "flow.json").write_text("{}", encoding="utf-8")
            (artifact / "prototype.html").write_text("<html></html>", encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(artifact)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(result.returncode, 1)
        self.assertIn("walkthrough.md", result.stdout)


if __name__ == "__main__":
    unittest.main()
