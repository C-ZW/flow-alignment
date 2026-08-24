"""Runtime audit planning stays generic before a browser is launched."""

import importlib.util
import sys
import unittest

from _support import ROOT


SCRIPT = (
    ROOT
    / ".claude"
    / "skills"
    / "flow-alignment-prototype"
    / "scripts"
    / "audit_runtime.py"
)
SPEC = importlib.util.spec_from_file_location("audit_runtime", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RuntimeAuditPlanning(unittest.TestCase):
    def test_viewport_parser_accepts_named_and_unnamed_sizes(self):
        self.assertEqual(
            MODULE.parse_viewport("phone=390x844"),
            MODULE.Viewport("phone", 390, 844),
        )
        self.assertEqual(
            MODULE.parse_viewport("1440x1000"),
            MODULE.Viewport("1440x1000", 1440, 1000),
        )

    def test_transition_plan_reaches_each_edge_from_entry(self):
        flow = {
            "entry": {"state": "start"},
            "states": [
                {"id": "start", "transitions": ["choice"]},
                {"id": "choice", "transitions": ["yes", "no"]},
                {"id": "yes", "transitions": ["choice"]},
                {"id": "no", "transitions": []},
            ],
        }
        self.assertEqual(
            MODULE.transition_cases(flow),
            [
                ("start", "choice", ["start"]),
                ("choice", "yes", ["start", "choice"]),
                ("choice", "no", ["start", "choice"]),
                ("yes", "choice", ["start", "choice", "yes"]),
            ],
        )


if __name__ == "__main__":
    unittest.main()
