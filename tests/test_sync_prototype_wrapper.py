"""The portable wrapper synchronizer preserves authored regions and rejects drift."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from _support import ROOT, TEMPLATE


SCRIPT = (
    ROOT
    / ".claude"
    / "skills"
    / "flow-alignment-prototype"
    / "scripts"
    / "sync_prototype_wrapper.py"
)


class PrototypeWrapperSync(unittest.TestCase):
    def run_script(self, path: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(path), *arguments],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

    def test_check_rejects_generic_drift_and_sync_restores_it(self):
        canonical = TEMPLATE.read_text(encoding="utf-8")
        drifted = canonical.replace("font-size: 13px", "font-size: 12px", 1)
        self.assertNotEqual(drifted, canonical)

        with tempfile.TemporaryDirectory() as directory:
            prototype = Path(directory) / "prototype.html"
            prototype.write_text(drifted, encoding="utf-8")

            check = self.run_script(prototype, "--check")
            self.assertEqual(check.returncode, 1, check.stdout + check.stderr)

            sync = self.run_script(prototype)
            self.assertEqual(sync.returncode, 0, sync.stdout + sync.stderr)
            self.assertEqual(prototype.read_text(encoding="utf-8"), canonical)

            final_check = self.run_script(prototype, "--check")
            self.assertEqual(final_check.returncode, 0, final_check.stdout + final_check.stderr)

    def test_changed_shell_outer_element_names_the_required_marker(self):
        changed = TEMPLATE.read_text(encoding="utf-8").replace(
            '<div class="app-shell" id="app-shell">',
            '<div class="app-shell product-app" id="app-shell">',
            1,
        )
        with tempfile.TemporaryDirectory() as directory:
            prototype = Path(directory) / "prototype.html"
            prototype.write_text(changed, encoding="utf-8")
            result = self.run_script(prototype, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertIn("required exact marker is missing", result.stdout)
        self.assertIn('<div class="app-shell" id="app-shell">', result.stdout)


if __name__ == "__main__":
    unittest.main()
