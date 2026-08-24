#!/usr/bin/env python3
"""Validate the distributable skills and every checked-in example artifact."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE_VALIDATOR = (
    ROOT
    / ".claude/skills/website-flow-reference/scripts/validate_reference.py"
)
HANDOFF_VALIDATOR = (
    ROOT
    / ".claude/skills/flow-alignment-prototype/scripts/validate_handoff.py"
)


def run(*args: str | Path) -> None:
    command = [str(arg) for arg in args]
    print("+", " ".join(command), flush=True)
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    subprocess.run(command, cwd=ROOT, env=environment, check=True)


def main() -> int:
    run(sys.executable, "scripts/sync_plugin_skills.py", "--check")
    run(sys.executable, "scripts/sync_prototype_template.py", "--check")

    references = sorted((ROOT / "references").glob("*/reference.json"))
    prototypes = sorted((ROOT / "prototypes").glob("*/flow.json"))
    if not references or not prototypes:
        raise SystemExit("Expected at least one checked-in reference and prototype.")

    for reference in references:
        run(sys.executable, REFERENCE_VALIDATOR, reference)

    for flow in prototypes:
        prototype_dir = flow.parent
        run(sys.executable, HANDOFF_VALIDATOR, prototype_dir)

    run(sys.executable, "-m", "unittest", "discover", "-s", "tests")
    print(
        f"Validated {len(references)} reference(s) and "
        f"{len(prototypes)} prototype(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
