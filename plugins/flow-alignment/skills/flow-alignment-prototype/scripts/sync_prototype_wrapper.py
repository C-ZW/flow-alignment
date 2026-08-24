#!/usr/bin/env python3
"""Restore generic prototype regions while preserving authored product regions."""

from __future__ import annotations

import argparse
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_DIR / "assets" / "prototype-template.html"
PRODUCT_CSS_MARKER = "/* ---- Product-specific additions go below this line. ---- */"
SHELL_START = '<div class="app-shell" id="app-shell">'
SHELL_END = '\n<div id="interaction-mask"'
SPEC_START = '<script id="flow-spec" type="application/json">'
STATE_START = '<div id="state-views" hidden>'
STATE_END = '<!-- ========================================================================\n     ENGINE'


def marker_index(document: str, marker: str, *, start: int = 0) -> int:
    index = document.find(marker, start)
    if index < 0:
        raise ValueError(f"required exact marker is missing: {marker!r}")
    return index


def slice_between(document: str, start: str, end: str, *, include_end: bool = False) -> str:
    left = marker_index(document, start)
    right = marker_index(document, end, start=left)
    if include_end:
        right += len(end)
    return document[left:right]


def product_css(document: str) -> str:
    left = marker_index(document, PRODUCT_CSS_MARKER) + len(PRODUCT_CSS_MARKER)
    right = marker_index(document, "</style>", start=left)
    return document[left:right]


def replace_between(document: str, start: str, end: str, replacement: str) -> str:
    left = marker_index(document, start)
    right = marker_index(document, end, start=left)
    return document[:left] + replacement + document[right:]


def rebuild(template: str, artifact: str) -> str:
    shell = slice_between(artifact, SHELL_START, SHELL_END)
    spec = slice_between(artifact, SPEC_START, "</script>", include_end=True)
    states = slice_between(artifact, STATE_START, STATE_END)
    css = product_css(artifact)

    rebuilt = replace_between(template, SHELL_START, SHELL_END, shell)
    rebuilt = replace_between(rebuilt, SPEC_START, "</script>", spec[:-len("</script>")])
    css_start = marker_index(rebuilt, PRODUCT_CSS_MARKER) + len(PRODUCT_CSS_MARKER)
    css_end = marker_index(rebuilt, "</style>", start=css_start)
    rebuilt = rebuilt[:css_start] + css + rebuilt[css_end:]
    return replace_between(rebuilt, STATE_START, STATE_END, states)


def assemble(template: str, shell: str, flow_json: str, states: str, css: str) -> str:
    """Build a prototype from only the four authored regions."""
    rebuilt = replace_between(template, SHELL_START, SHELL_END, shell.rstrip())
    spec = f'{SPEC_START}\n{flow_json.strip()}\n'
    rebuilt = replace_between(rebuilt, SPEC_START, "</script>", spec)
    css_start = marker_index(rebuilt, PRODUCT_CSS_MARKER) + len(PRODUCT_CSS_MARKER)
    css_end = marker_index(rebuilt, "</style>", start=css_start)
    rebuilt = rebuilt[:css_start] + css.rstrip() + "\n" + rebuilt[css_end:]
    return replace_between(rebuilt, STATE_START, STATE_END, states.rstrip() + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync generic prototype markup while preserving authored regions."
    )
    parser.add_argument("prototype", type=Path, help="prototype.html to normalize or check")
    parser.add_argument("--check", action="store_true", help="report drift without writing")
    args = parser.parse_args()

    try:
        template = TEMPLATE.read_text(encoding="utf-8")
        current = args.prototype.read_text(encoding="utf-8")
        expected = rebuild(template, current)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: Cannot synchronize prototype wrapper: {exc}")
        return 1

    if current == expected:
        print(f"OK: {args.prototype} matches the canonical prototype wrapper.")
        return 0
    if args.check:
        print(f"ERROR: {args.prototype} has generic wrapper drift.")
        return 1

    args.prototype.write_text(expected, encoding="utf-8")
    print(f"Synced {args.prototype}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
