#!/usr/bin/env python3
"""Run the portable, deterministic handoff gates for one flow artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
REFERENCE_SKILL = SKILL_DIR.parent / "website-flow-reference"


def non_empty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


def run(command: list[str], *, cwd: Path) -> bool:
    print("+", " ".join(command))
    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode == 0


def repository_root(artifact_dir: Path) -> Path:
    if artifact_dir.parent.name == "prototypes":
        return artifact_dir.parent.parent
    for parent in (artifact_dir, *artifact_dir.parents):
        if (parent / "PROJECT_GOALS.md").is_file():
            return parent
    return Path.cwd().resolve()


def reference_from_adaptation(adaptation_path: Path, root: Path) -> Path:
    document = json.loads(adaptation_path.read_text(encoding="utf-8"))
    raw_path = document.get("reference", {}).get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("adaptation.reference.path must be a non-empty string")
    return (root / raw_path).resolve()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate one flow artifact and its website handoff, when present."
    )
    parser.add_argument("artifact_dir", type=Path, help="prototypes/<flow-name> directory")
    parser.add_argument(
        "--reference",
        type=Path,
        help="reference.json; otherwise derived from adaptation.json when present",
    )
    parser.add_argument(
        "--require-preview",
        action="store_true",
        help="require screenshots/readme-preview.png for a documented demo",
    )
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="also run the optional Playwright browser audit",
    )
    args = parser.parse_args()

    artifact_dir = args.artifact_dir.resolve()
    root = repository_root(artifact_dir)
    flow_path = artifact_dir / "flow.json"
    prototype_path = artifact_dir / "prototype.html"
    walkthrough_path = artifact_dir / "walkthrough.md"
    adaptation_path = artifact_dir / "adaptation.json"
    authoring_dir = artifact_dir / "authoring"

    errors: list[str] = []
    for path in (flow_path, prototype_path, walkthrough_path):
        if not non_empty(path):
            errors.append(f"Required handoff file is missing or empty: {path}")
    for name in ("product-shell.html", "state-views.html", "product.css"):
        path = authoring_dir / name
        if not non_empty(path):
            errors.append(f"Required authoring fragment is missing or empty: {path}")
    if args.require_preview:
        preview = artifact_dir / "screenshots" / "readme-preview.png"
        if not non_empty(preview):
            errors.append(f"Required demo preview is missing or empty: {preview}")
        elif not preview.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append(f"Demo preview is not a PNG file: {preview}")

    reference_path = args.reference.resolve() if args.reference else None
    if reference_path is not None and not non_empty(adaptation_path):
        errors.append("A website-derived handoff requires a non-empty adaptation.json.")
    if reference_path is None and non_empty(adaptation_path):
        try:
            reference_path = reference_from_adaptation(adaptation_path, root)
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            errors.append(f"Cannot resolve the reference from adaptation.json: {exc}")
    if reference_path is not None and not non_empty(reference_path):
        errors.append(f"Reference file is missing or empty: {reference_path}")

    if errors:
        for message in errors:
            print(f"ERROR: {message}")
        return 1

    commands = [
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "build_prototype.py"),
            str(artifact_dir),
            "--check",
        ],
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "sync_prototype_wrapper.py"),
            str(prototype_path),
            "--check",
        ],
        [
            sys.executable,
            str(SKILL_DIR / "scripts" / "validate_flow_spec.py"),
            str(flow_path),
            str(prototype_path),
        ],
    ]
    if reference_path is not None:
        commands.extend(
            [
                [
                    sys.executable,
                    str(REFERENCE_SKILL / "scripts" / "validate_reference.py"),
                    str(reference_path),
                ],
                [
                    sys.executable,
                    str(SKILL_DIR / "scripts" / "validate_adaptation.py"),
                    str(adaptation_path),
                    str(reference_path),
                    str(flow_path),
                ],
            ]
        )
    if args.runtime:
        commands.append(
            [
                sys.executable,
                str(SKILL_DIR / "scripts" / "audit_runtime.py"),
                str(artifact_dir),
            ]
        )

    passed = all(run(command, cwd=root) for command in commands)
    if not passed:
        return 1
    print("OK: deterministic handoff gates passed.")
    if args.runtime:
        print("OK: mechanical runtime browser audit passed.")
    else:
        print(
            "Runtime browser walks remain required before reporting completion; "
            "rerun with --runtime when Playwright is available."
        )
    print(
        "Human review remains required for product meaning, omitted journeys, "
        "and visual-reference judgement."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
