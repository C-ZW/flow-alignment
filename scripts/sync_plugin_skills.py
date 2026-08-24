#!/usr/bin/env python3
"""Keep the distributable Codex plugin aligned with the canonical skills."""

from __future__ import annotations

import argparse
import filecmp
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = ROOT / ".claude" / "skills"
PLUGIN_ROOT = ROOT / "plugins" / "flow-alignment" / "skills"
SKILL_NAMES = ("flow-alignment-prototype", "website-flow-reference")
IGNORED_NAMES = {"__pycache__", ".DS_Store"}


def included_files(root: Path) -> dict[Path, Path]:
    return {
        path.relative_to(root): path
        for path in root.rglob("*")
        if path.is_file()
        and not any(part in IGNORED_NAMES for part in path.relative_to(root).parts)
        and path.suffix not in {".pyc", ".pyo"}
    }


def differences(source: Path, target: Path) -> list[str]:
    source_files = included_files(source)
    target_files = included_files(target) if target.exists() else {}
    findings = []
    for relative_path in sorted(source_files.keys() | target_files.keys()):
        source_path = source_files.get(relative_path)
        target_path = target_files.get(relative_path)
        if source_path is None:
            findings.append(f"extra in plugin: {relative_path}")
        elif target_path is None:
            findings.append(f"missing from plugin: {relative_path}")
        elif not filecmp.cmp(source_path, target_path, shallow=False):
            findings.append(f"content differs: {relative_path}")
    return findings


def sync_skill(source: Path, target: Path) -> None:
    if target.exists():
        shutil.rmtree(target)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns("__pycache__", ".DS_Store", "*.pyc", "*.pyo"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync or verify the skills bundled in the Flow Alignment Codex plugin."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report drift without changing files.",
    )
    args = parser.parse_args()

    all_findings: list[str] = []
    for name in SKILL_NAMES:
        source = SOURCE_ROOT / name
        target = PLUGIN_ROOT / name
        if not source.is_dir():
            all_findings.append(f"canonical skill is missing: {source}")
            continue
        if args.check:
            all_findings.extend(f"{name}: {item}" for item in differences(source, target))
        else:
            sync_skill(source, target)
            print(f"Synced {name}")

    if all_findings:
        print("Plugin skill bundle is out of sync:")
        for finding in all_findings:
            print(f"- {finding}")
        return 1
    if args.check:
        print("Plugin skill bundle matches the canonical skills.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
