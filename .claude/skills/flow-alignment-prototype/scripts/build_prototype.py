#!/usr/bin/env python3
"""Build prototype.html from isolated product-owned authoring fragments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from sync_prototype_wrapper import (
    PRODUCT_CSS_MARKER,
    SHELL_END,
    SHELL_START,
    STATE_END,
    STATE_START,
    TEMPLATE,
    assemble,
    product_css,
    slice_between,
)


AUTHORING_FILES = {
    "shell": "product-shell.html",
    "states": "state-views.html",
    "css": "product.css",
}


def authoring_paths(artifact_dir: Path) -> dict[str, Path]:
    authoring = artifact_dir / "authoring"
    return {name: authoring / filename for name, filename in AUTHORING_FILES.items()}


def write_fragments(artifact_dir: Path, source: str, *, overwrite: bool) -> None:
    paths = authoring_paths(artifact_dir)
    paths["shell"].parent.mkdir(parents=True, exist_ok=True)
    fragments = {
        "shell": slice_between(source, SHELL_START, SHELL_END).rstrip() + "\n",
        "states": slice_between(source, STATE_START, STATE_END).rstrip() + "\n",
        "css": product_css(source).strip() + "\n",
    }
    for name, path in paths.items():
        if path.exists() and not overwrite:
            raise FileExistsError(f"Refusing to overwrite existing authoring fragment: {path}")
        path.write_text(fragments[name], encoding="utf-8")
        print(f"Wrote {path}")


def expected_prototype(artifact_dir: Path) -> str:
    paths = authoring_paths(artifact_dir)
    flow_path = artifact_dir / "flow.json"
    flow_text = flow_path.read_text(encoding="utf-8")
    json.loads(flow_text)
    template = TEMPLATE.read_text(encoding="utf-8")
    return assemble(
        template,
        paths["shell"].read_text(encoding="utf-8"),
        flow_text,
        paths["states"].read_text(encoding="utf-8"),
        paths["css"].read_text(encoding="utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a prototype from product-owned fragments and canonical generic markup."
    )
    parser.add_argument("artifact_dir", type=Path, help="prototypes/<flow-name> directory")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--init",
        action="store_true",
        help="seed authoring fragments only; flow.json and walkthrough.md remain agent-authored",
    )
    mode.add_argument(
        "--extract",
        action="store_true",
        help="migrate an existing prototype into authoring fragments",
    )
    mode.add_argument("--check", action="store_true", help="verify output matches fragments")
    args = parser.parse_args()

    artifact_dir = args.artifact_dir.resolve()
    output = artifact_dir / "prototype.html"
    try:
        if args.init:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            write_fragments(
                artifact_dir,
                TEMPLATE.read_text(encoding="utf-8"),
                overwrite=False,
            )
            print("Initialized authoring fragments only.")
            print("Next: author flow.json and walkthrough.md, then run this command without --init.")
            return 0
        if args.extract:
            write_fragments(
                artifact_dir,
                output.read_text(encoding="utf-8"),
                overwrite=False,
            )
            return 0

        expected = expected_prototype(artifact_dir)
        if args.check:
            if not output.is_file() or output.read_text(encoding="utf-8") != expected:
                print(f"ERROR: {output} does not match its authoring fragments.")
                return 1
            print(f"OK: {output} matches its authoring fragments.")
            return 0
        output.write_text(expected, encoding="utf-8")
        print(f"Built {output}")
        return 0
    except (OSError, UnicodeError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: Cannot build prototype: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
