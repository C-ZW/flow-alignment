#!/usr/bin/env python3
"""Rebuild artifact wrappers from the canonical template without touching product regions."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / ".claude/skills/flow-alignment-prototype/assets/prototype-template.html"
PRODUCT_CSS_MARKER = "/* ---- Product-specific additions go below this line. ---- */"
SHELL_START = '<div class="app-shell" id="app-shell">'
SHELL_END = '\n<div id="interaction-mask"'
SPEC_START = '<script id="flow-spec" type="application/json">'
STATE_START = '<div id="state-views" hidden>'
STATE_END = '<!-- ========================================================================\n     ENGINE'


def slice_between(document: str, start: str, end: str, *, include_end: bool = False) -> str:
    left = document.index(start)
    right = document.index(end, left)
    if include_end:
        right += len(end)
    return document[left:right]


def product_css(document: str) -> str:
    left = document.index(PRODUCT_CSS_MARKER) + len(PRODUCT_CSS_MARKER)
    right = document.index("</style>", left)
    return document[left:right]


def replace_between(document: str, start: str, end: str, replacement: str) -> str:
    left = document.index(start)
    right = document.index(end, left)
    return document[:left] + replacement + document[right:]


def rebuild(template: str, artifact: str) -> str:
    shell = slice_between(artifact, SHELL_START, SHELL_END)
    spec = slice_between(artifact, SPEC_START, "</script>", include_end=True)
    states = slice_between(artifact, STATE_START, STATE_END)
    css = product_css(artifact)

    rebuilt = replace_between(template, SHELL_START, SHELL_END, shell)
    rebuilt = replace_between(rebuilt, SPEC_START, "</script>", spec[:-len("</script>")])
    css_start = rebuilt.index(PRODUCT_CSS_MARKER) + len(PRODUCT_CSS_MARKER)
    css_end = rebuilt.index("</style>", css_start)
    rebuilt = rebuilt[:css_start] + css + rebuilt[css_end:]
    rebuilt = replace_between(rebuilt, STATE_START, STATE_END, states)
    return rebuilt


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync generic prototype markup while preserving the four authored regions."
    )
    parser.add_argument("paths", nargs="*", type=Path, help="prototype.html files; defaults to all")
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    paths = args.paths or sorted((ROOT / "prototypes").glob("*/prototype.html"))
    template = TEMPLATE.read_text(encoding="utf-8")
    drifted: list[Path] = []
    for raw_path in paths:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        current = path.read_text(encoding="utf-8")
        expected = rebuild(template, current)
        if current == expected:
            continue
        drifted.append(path)
        if not args.check:
            path.write_text(expected, encoding="utf-8")
            print(f"Synced {path.relative_to(ROOT)}")

    if args.check and drifted:
        print("Prototype wrappers are out of sync:")
        for path in drifted:
            print(f"- {path.relative_to(ROOT)}")
        return 1
    if args.check:
        print("All prototype wrappers match the canonical template.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
