"""Shared helpers for the validator test suite."""

from __future__ import annotations

import copy
import importlib.util
import json
import re
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
TEMPLATE = SKILLS / "flow-alignment-prototype" / "assets" / "prototype-template.html"


def load_module(relative_path: str) -> ModuleType:
    """Import a validator script that lives outside a Python package."""
    path = SKILLS / relative_path
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


flow_spec = load_module("flow-alignment-prototype/scripts/validate_flow_spec.py")
adaptation = load_module("flow-alignment-prototype/scripts/validate_adaptation.py")
review_apply = load_module("flow-alignment-prototype/scripts/apply_review_session.py")
reference = load_module("website-flow-reference/scripts/validate_reference.py")


def template_html() -> str:
    return TEMPLATE.read_text(encoding="utf-8")


def template_spec() -> dict:
    """The specification embedded in the shipped template."""
    embedded = re.search(
        r'<script id="flow-spec" type="application/json">(.*?)</script>',
        template_html(),
        re.DOTALL,
    )
    return json.loads(embedded.group(1))


def valid_spec() -> dict:
    return copy.deepcopy(template_spec())


def errors(issues) -> list[str]:
    return [issue.message for issue in issues if issue.level == "ERROR"]


def warnings(issues) -> list[str]:
    return [issue.message for issue in issues if issue.level == "WARNING"]


def check_spec(spec: dict) -> list[str]:
    """Error messages produced by validating a specification alone."""
    return errors(flow_spec.validate_spec(spec)[0])


def check_html(html: str, spec: dict | None = None) -> tuple[list[str], list[str]]:
    """Error and warning messages produced by validating a prototype document."""
    spec = spec if spec is not None else template_spec()
    spec_issues, models = flow_spec.validate_spec(spec)
    assert not errors(spec_issues), f"fixture specification is invalid: {errors(spec_issues)}"
    issues = flow_spec.validate_html(spec, models, html)
    return errors(issues), warnings(issues)


def mentions(messages: list[str], *fragments: str) -> bool:
    """True when one message contains every fragment."""
    return any(all(fragment in message for fragment in fragments) for message in messages)
