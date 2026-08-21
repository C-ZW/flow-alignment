#!/usr/bin/env python3
"""Validate a flow-validation prototype against its JSON source of truth.

flow.json declares every flow, state, and allowed transition. prototype.html is a
view layer: it embeds the same specification and renders one declarative
<template data-flow data-state> per state. This script checks that the two agree,
that the declared graph is actually navigable, and that observer-only controls
never leak into the participant-facing product viewport.

Usage:
    validate_flow_spec.py <flow.json> [prototype.html]

Exit codes: 0 = valid (warnings allowed), 1 = errors found, 2 = bad invocation.
"""

from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

SPEC_VERSION = 2
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

REQUIRED_ELEMENT_IDS = (
    "observer-hud",
    "flow-selector",
    "flow-title",
    "flow-hypothesis",
    "flow-success",
    "flow-task",
    "state-stepper",
    "state-instruction",
    "hud-details",
    "details-toggle",
    "reset-flow",
    "error-toggle",
    "present-toggle",
    "hypothesis-block",
    "success-block",
    "product-viewport",
    "state-views",
    "flow-spec",
)

# Vocabulary that belongs to the observer HUD and must never appear in a product
# state view. Kept deliberately narrow so real product copy does not trip it, and
# extended per language: an artifact written for Chinese-speaking participants
# leaks the same way an English one does. Add your own product's terms here when
# a team uses different wording for the test apparatus.
OBSERVER_ONLY_PHRASES = (
    # English
    "reset flow",
    "restart flow",
    "restart test",
    "restart validation",
    "restart the flow",
    "simulate error",
    "error simulation",
    "hypothesis",
    "observer guide",
    "observer hud",
    "participant task",
    "validation flow",
    "test plan",
    "telemetry",
    "event log",
    "facilitator",
    # Chinese (traditional and simplified)
    "重置流程",
    "重新開始流程",
    "重新开始流程",
    "重啟流程",
    "重启流程",
    "重新測試",
    "重新测试",
    "模擬錯誤",
    "模拟错误",
    "錯誤模擬",
    "错误模拟",
    "驗證假說",
    "验证假说",
    "驗證假設",
    "验证假设",
    "驗證流程",
    "验证流程",
    "觀察者指引",
    "观察者指引",
    "測試任務",
    "测试任务",
    "測試計畫",
    "测试计划",
    "測試腳本",
    "测试脚本",
    "遙測",
    "遥测",
)

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

ALLOWED_EXTERNAL_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")

BLOCKING_DIALOGS = re.compile(r"\b(?:alert|confirm|prompt)\s*\(")
NETWORK_CALLS = re.compile(r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(")


class Issue:
    """A validation finding. Only errors fail the run."""

    def __init__(self, level: str, message: str) -> None:
        self.level = level
        self.message = message

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Issue({self.level!r}, {self.message!r})"


def error(message: str) -> Issue:
    return Issue("ERROR", message)


def warning(message: str) -> Issue:
    return Issue("WARNING", message)


def is_kebab(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


# --------------------------------------------------------------------------- #
# flow.json
# --------------------------------------------------------------------------- #


def read_spec(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read flow specification: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("flow.json must be a JSON object.")
    return data


def validate_flow(flow: object, index: int) -> tuple[list[Issue], dict]:
    """Validate one flow. Returns issues and a lookup model of its states."""
    label = f"flows[{index}]"
    if not isinstance(flow, dict):
        return [error(f"{label} must be an object.")], {}

    issues: list[Issue] = []
    flow_id = flow.get("id")
    if not is_kebab(flow_id):
        issues.append(error(f"{label}.id must be a kebab-case string."))
        flow_id = flow_id if isinstance(flow_id, str) else label
    label = f"flow '{flow_id}'"

    for field in ("title", "task"):
        if not is_text(flow.get(field)):
            issues.append(error(f"{label} is missing {field}."))
    # Research fields are optional: a flow being confirmed with a client has a
    # scenario to walk, not a hypothesis to falsify.
    for field in ("hypothesis", "successSignal"):
        if field in flow and not is_text(flow.get(field)):
            issues.append(error(f"{label} has an empty {field}; omit it or fill it in."))

    error_simulation = flow.get("errorSimulation")
    if error_simulation is not None:
        if not isinstance(error_simulation, dict) or not isinstance(error_simulation.get("supported"), bool):
            issues.append(error(f"{label}.errorSimulation needs a boolean 'supported'."))
        elif error_simulation["supported"] and not is_text(error_simulation.get("label")):
            issues.append(error(f"{label} enables error simulation but has no label."))

    states = flow.get("states")
    if not isinstance(states, list) or len(states) < 2:
        issues.append(error(f"{label} needs at least two states."))
        return issues, {"id": flow_id, "states": {}, "transitions": {}, "navigation": {}}

    transitions: dict[str, list[str]] = {}
    navigation: dict[str, dict] = {}
    terminal: set[str] = set()
    steps: dict[str, int] = {}
    for state in states:
        if not isinstance(state, dict):
            issues.append(error(f"{label} has a state that is not an object."))
            continue
        state_id = state.get("id")
        if not is_kebab(state_id):
            issues.append(error(f"{label} has a state without a kebab-case id."))
            continue
        if state_id in transitions:
            issues.append(error(f"{label} has a duplicate state id: {state_id}."))
            continue
        for field in ("title", "instruction"):
            if not is_text(state.get(field)):
                issues.append(error(f"{label} state '{state_id}' is missing {field}."))
        step = state.get("step")
        if not isinstance(step, int) or isinstance(step, bool) or step < 1:
            issues.append(error(f"{label} state '{state_id}' needs a positive integer step."))
        else:
            steps[state_id] = step
        targets = state.get("transitions")
        if not isinstance(targets, list) or not all(isinstance(target, str) for target in targets):
            issues.append(error(f"{label} state '{state_id}' needs a transitions array of state ids."))
            targets = []
        if len(set(targets)) != len(targets):
            issues.append(error(f"{label} state '{state_id}' lists a duplicate transition."))
        transitions[state_id] = list(dict.fromkeys(targets))
        if state.get("terminal") is True:
            terminal.add(state_id)

        scope = state.get("scope")
        if scope is not None and scope not in ("viewport", "shell"):
            issues.append(error(f"{label} state '{state_id}' has scope '{scope}'; use viewport or shell."))
        nav_targets = state.get("navTargets")
        if nav_targets is not None:
            if not isinstance(nav_targets, dict) or not nav_targets:
                issues.append(error(f"{label} state '{state_id}' navTargets must be a non-empty object."))
                nav_targets = {}
            else:
                for key, destination in nav_targets.items():
                    if not isinstance(key, str) or not key.strip():
                        issues.append(error(f"{label} state '{state_id}' has a navTargets key that is not a name."))
                    elif destination not in targets:
                        issues.append(error(
                            f"{label} state '{state_id}' routes nav '{key}' to '{destination}', which is not a "
                            "declared transition from that state."
                        ))
            if scope != "shell":
                issues.append(error(
                    f"{label} state '{state_id}' declares navTargets but not scope 'shell'; the navigation it "
                    "points at would stay dimmed and unusable."
                ))
        elif scope == "shell":
            issues.append(warning(
                f"{label} state '{state_id}' opens the whole shell but offers no navTargets."
            ))
        navigation[state_id] = dict(nav_targets) if isinstance(nav_targets, dict) else {}

    state_ids = set(transitions)
    for source, targets in transitions.items():
        for target in targets:
            if target not in state_ids:
                issues.append(error(f"{label} state '{source}' transitions to unknown state '{target}'."))

    initial = flow.get("initialState")
    if initial not in state_ids:
        issues.append(error(f"{label}.initialState must reference a declared state."))
    else:
        reachable: set[str] = set()
        pending = [initial]
        while pending:
            current = pending.pop()
            if current in reachable:
                continue
            reachable.add(current)
            pending.extend(t for t in transitions.get(current, []) if t in state_ids)
        for orphan in sorted(state_ids - reachable):
            issues.append(error(f"{label} state '{orphan}' is unreachable from initialState."))
        if not terminal:
            issues.append(error(f"{label} needs at least one state marked terminal."))
        elif not terminal & reachable:
            issues.append(error(f"{label} has no terminal state reachable from initialState."))
        if steps.get(initial, 1) != 1:
            issues.append(warning(f"{label}.initialState is not step 1."))

    model = {
        "id": flow_id,
        "states": state_ids,
        "transitions": transitions,
        "navigation": navigation,
        "errorSimulation": error_simulation if isinstance(error_simulation, dict) else {"supported": False},
    }
    return issues, model


def validate_spec(spec: dict) -> tuple[list[Issue], list[dict]]:
    issues: list[Issue] = []
    if spec.get("version") != SPEC_VERSION:
        if spec.get("version") == 1:
            issues.append(error(
                "flow.json uses the retired version 1 shape. Version 2 wraps every flow in a top-level "
                "'flows' array."
            ))
        else:
            issues.append(error(f"flow.json version must equal {SPEC_VERSION}."))

    flows = spec.get("flows")
    if not isinstance(flows, list) or not flows:
        issues.append(error("flow.json needs a non-empty 'flows' array."))
        return issues, []
    if len(flows) > 3:
        issues.append(warning(
            f"{len(flows)} flows in one artifact. One artifact should test one focused hypothesis by default."
        ))

    models: list[dict] = []
    for index, flow in enumerate(flows):
        flow_issues, model = validate_flow(flow, index)
        issues.extend(flow_issues)
        models.append(model)

    seen: set[str] = set()
    for model in models:
        flow_id = model.get("id")
        if isinstance(flow_id, str):
            if flow_id in seen:
                issues.append(error(f"Duplicate flow id: {flow_id}."))
            seen.add(flow_id)
    return issues, models


# --------------------------------------------------------------------------- #
# prototype.html
# --------------------------------------------------------------------------- #


class TemplateRecord:
    def __init__(self, flow_id: str | None, state_id: str | None, variant: str | None) -> None:
        self.flow_id = flow_id
        self.state_id = state_id
        self.variant = variant
        self.gotos: list[tuple[str, str]] = []  # (tag, target)
        self.jumps: list[str] = []
        self.navs: list[str] = []
        self.inline_handlers: list[str] = []
        self.text_parts: list[str] = []

    @property
    def key(self) -> str:
        variant = f"/{self.variant}" if self.variant else ""
        return f"{self.flow_id}/{self.state_id}{variant}"

    def searchable_text(self) -> str:
        return " ".join(self.text_parts).lower()


class PrototypeParser(HTMLParser):
    """Collects the structural facts the validator needs from prototype.html."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        self.element_ids: set[str] = set()
        self.templates: list[TemplateRecord] = []
        self.template_stack: list[TemplateRecord] = []
        self.scripts: dict[str, list[str]] = {}
        self.current_script: str | None = None
        self.viewport_children: list[str] = []
        self.viewport_text: list[str] = []
        self.shell_gotos: list[str] = []
        self.templates_in_shell: list[str] = []
        self.templates_outside_container: list[str] = []
        self.external_refs: list[str] = []
        self.hud_gotos: list[str] = []
        self.shell_navs: list[str] = []
        self.misplaced_navs: list[tuple[str, str]] = []

    # -- helpers ---------------------------------------------------------- #

    def _in_context(self, predicate) -> bool:
        return any(predicate(tag, attrs) for tag, attrs in self.stack)

    def _in_shell(self) -> bool:
        return self._in_context(lambda tag, attrs: "product-context" in (attrs.get("class") or "").split())

    def _in_viewport(self) -> bool:
        return self._in_context(lambda tag, attrs: attrs.get("id") == "product-viewport")

    def _in_hud(self) -> bool:
        return self._in_context(lambda tag, attrs: attrs.get("id") == "observer-hud")

    # -- parser hooks ----------------------------------------------------- #

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: (value or "") for key, value in attrs}

        if attr_map.get("id"):
            self.element_ids.add(attr_map["id"])

        if self._in_viewport():
            self.viewport_children.append(tag)

        for key in ("src", "href"):
            value = attr_map.get(key, "")
            if value.startswith(("http://", "https://")) and not any(host in value for host in ALLOWED_EXTERNAL_HOSTS):
                self.external_refs.append(value)

        nav = attr_map.get("data-nav")
        if nav is not None:
            if self.template_stack:
                self.template_stack[-1].navs.append(nav)
            elif self._in_hud():
                self.misplaced_navs.append((nav, "the observer HUD"))
            elif self._in_shell():
                self.shell_navs.append(nav)
            else:
                self.misplaced_navs.append((nav, "outside the product shell"))

        jump = attr_map.get("data-jump")
        if jump and self.template_stack:
            self.template_stack[-1].jumps.append(jump)

        goto = attr_map.get("data-goto")
        if goto:
            if self.template_stack:
                self.template_stack[-1].gotos.append((tag, goto))
            elif self._in_shell():
                self.shell_gotos.append(goto)
            elif self._in_hud():
                self.hud_gotos.append(goto)

        if self.template_stack:
            record = self.template_stack[-1]
            for key, value in attr_map.items():
                if key.startswith("on"):
                    record.inline_handlers.append(f"{tag}[{key}]")
                if key in ("title", "aria-label", "placeholder", "value", "alt"):
                    record.text_parts.append(value)

        if tag == "template":
            record = TemplateRecord(
                attr_map.get("data-flow"),
                attr_map.get("data-state"),
                attr_map.get("data-variant") or None,
            )
            if self._in_shell():
                self.templates_in_shell.append(record.key)
            if not self._in_context(lambda t, a: a.get("id") == "state-views"):
                self.templates_outside_container.append(record.key)
            self.templates.append(record)
            self.template_stack.append(record)

        if tag == "script":
            self.current_script = attr_map.get("id", "__inline__")
            self.scripts.setdefault(self.current_script, [])

        if tag not in VOID_ELEMENTS:
            self.stack.append((tag, attr_map))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.current_script = None
        if tag == "template" and self.template_stack:
            self.template_stack.pop()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if self.current_script is not None:
            self.scripts[self.current_script].append(data)
            return
        if self.template_stack:
            self.template_stack[-1].text_parts.append(data)
        elif self._in_viewport() and data.strip():
            self.viewport_text.append(data.strip())


def validate_html(spec: dict, models: list[dict], html: str) -> list[Issue]:
    issues: list[Issue] = []
    parser = PrototypeParser()
    parser.feed(html)
    parser.close()

    # 1. The embedded specification must match flow.json exactly.
    embedded_raw = "".join(parser.scripts.get("flow-spec", []))
    if not embedded_raw.strip():
        issues.append(error('prototype.html must embed <script id="flow-spec" type="application/json">.'))
    else:
        try:
            embedded = json.loads(embedded_raw)
        except json.JSONDecodeError as exc:
            issues.append(error(f"Embedded #flow-spec is not valid JSON: {exc}."))
        else:
            if embedded != spec:
                issues.append(error("Embedded #flow-spec differs from flow.json."))

    # 2. The generic engine contract.
    for element_id in REQUIRED_ELEMENT_IDS:
        if element_id not in parser.element_ids:
            issues.append(error(f"prototype.html is missing the required element #{element_id}."))

    # 3. The product viewport is rendered at runtime and must be empty in source.
    if parser.viewport_children or parser.viewport_text:
        issues.append(error(
            "#product-viewport must be empty in source; state views belong in <template data-state> elements."
        ))

    # 4. Templates map one-to-one onto declared states.
    declared_flows = {model["id"]: model for model in models if isinstance(model.get("id"), str)}
    seen_keys: set[str] = set()
    for record in parser.templates:
        if record.flow_id is None and record.state_id is None:
            continue  # a non-state template is allowed for reusable markup
        if record.flow_id not in declared_flows:
            issues.append(error(f"Template '{record.key}' references undeclared flow '{record.flow_id}'."))
            continue
        model = declared_flows[record.flow_id]
        if record.state_id not in model["states"]:
            issues.append(error(f"Template '{record.key}' references undeclared state '{record.state_id}'."))
            continue
        if record.variant not in (None, "error"):
            issues.append(error(f"Template '{record.key}' has an unsupported data-variant."))
            continue
        if record.variant == "error" and not model["errorSimulation"].get("supported"):
            issues.append(error(
                f"Template '{record.key}' declares an error variant but flow '{record.flow_id}' "
                "does not enable error simulation."
            ))
        if record.key in seen_keys:
            issues.append(error(f"Duplicate template for '{record.key}'."))
        seen_keys.add(record.key)

        # 5. Every action must be an allowed transition out of this state.
        allowed = set(model["transitions"].get(record.state_id, []))
        for tag, target in record.gotos:
            if target not in allowed:
                issues.append(error(
                    f"Template '{record.key}' has data-goto=\"{target}\", which is not a declared "
                    f"transition from '{record.state_id}'."
                ))
            if tag != "button":
                issues.append(error(f"Template '{record.key}' puts data-goto on <{tag}>; use a <button>."))

        # 6. Observer vocabulary must never reach a participant-facing view.
        text = record.searchable_text()
        for phrase in OBSERVER_ONLY_PHRASES:
            if phrase in text:
                issues.append(error(
                    f"Template '{record.key}' contains observer-only copy: '{phrase}'. "
                    "Observer guidance belongs in the HUD."
                ))
        for key in record.navs:
            issues.append(error(
                f"Template '{record.key}' has data-nav=\"{key}\". Product navigation belongs to the shell, "
                "not to a page view."
            ))
        for target in record.jumps:
            issues.append(error(
                f"Template '{record.key}' has data-jump=\"{target}\". Jumping between states is an "
                "observer control and belongs in the HUD stepper, not in a product view."
            ))
        for handler in record.inline_handlers:
            issues.append(error(
                f"Template '{record.key}' uses an inline handler {handler}; declare actions with data-goto."
            ))

    # 7. Every declared state needs a view, and every declared transition an affordance.
    templates_by_state: dict[tuple[str, str], list[TemplateRecord]] = {}
    for record in parser.templates:
        if record.flow_id in declared_flows and record.state_id in declared_flows[record.flow_id]["states"]:
            templates_by_state.setdefault((record.flow_id, record.state_id), []).append(record)

    for model in models:
        flow_id = model.get("id")
        if not isinstance(flow_id, str):
            continue
        for state_id in sorted(model["states"]):
            records = templates_by_state.get((flow_id, state_id), [])
            if not any(record.variant is None for record in records):
                issues.append(error(f"No base <template data-flow=\"{flow_id}\" data-state=\"{state_id}\"> found."))
                continue
            reachable_targets = {target for record in records for _, target in record.gotos}
            reachable_targets |= set(model["navigation"].get(state_id, {}).values())
            base_targets = {target for record in records if record.variant is None for _, target in record.gotos}
            base_targets |= set(model["navigation"].get(state_id, {}).values())
            for target in model["transitions"].get(state_id, []):
                if target not in reachable_targets:
                    issues.append(error(
                        f"Flow '{flow_id}' declares {state_id} -> {target}, but nothing offers that action. "
                        "Add a button with data-goto, route a nav key to it, or remove the transition."
                    ))
                elif target not in base_targets:
                    issues.append(warning(
                        f"Flow '{flow_id}' reaches {state_id} -> {target} only while error simulation is on."
                    ))
        if model["errorSimulation"].get("supported"):
            has_error_view = any(
                record.variant == "error" and record.flow_id == flow_id for record in parser.templates
            )
            if not has_error_view:
                issues.append(error(
                    f"Flow '{flow_id}' enables error simulation but declares no data-variant=\"error\" template."
                ))

    # 7b. Navigation keys must exist exactly once, in the shell, and be routed.
    for key, where in parser.misplaced_navs:
        issues.append(error(f"data-nav=\"{key}\" sits in {where}; product navigation belongs to the shell."))
    for key in sorted({key for key in parser.shell_navs if parser.shell_navs.count(key) > 1}):
        issues.append(error(f"Duplicate data-nav=\"{key}\" in the shell; navigation keys must be unique."))
    available = set(parser.shell_navs)
    for model in models:
        flow_id = model.get("id")
        if not isinstance(flow_id, str):
            continue
        for state_id, nav_targets in model["navigation"].items():
            for key in nav_targets:
                if key not in available:
                    issues.append(error(
                        f"Flow '{flow_id}' state '{state_id}' routes nav '{key}', but no shell element "
                        f"declares data-nav=\"{key}\"."
                    ))

    # 8. The surrounding product shell stays static; the HUD stays out of the product.
    for goto in parser.shell_gotos:
        issues.append(error(f"The dimmed product shell contains an interactive data-goto=\"{goto}\"."))
    for key in parser.templates_in_shell:
        issues.append(error(f"State view '{key}' is nested inside the non-interactive product shell."))
    for goto in parser.hud_gotos:
        issues.append(error(f"The observer HUD contains a product action data-goto=\"{goto}\"."))
    for key in parser.templates_outside_container:
        if key != "None/None":
            issues.append(error(f"State view '{key}' must live inside the #state-views container."))

    # 9. Local-file, no-backend guarantees.
    for reference in sorted(set(parser.external_refs)):
        issues.append(warning(f"External resource may not load from a local file: {reference}"))
    script_text = "\n".join("".join(chunks) for name, chunks in parser.scripts.items() if name != "flow-spec")
    if BLOCKING_DIALOGS.search(html):
        issues.append(error("Do not use alert(), confirm(), or prompt() as a product experience."))
    if NETWORK_CALLS.search(script_text):
        issues.append(error("The prototype must run offline; remove network calls."))

    # 10. Sketchbook visual language (advisory).
    if "Patrick Hand" not in html:
        issues.append(warning("The Patrick Hand sketchbook typeface is not referenced."))
    if "radial-gradient" not in html:
        issues.append(warning("The dotted graph-paper background is missing."))
    if "255px 15px 225px 15px" not in html:
        issues.append(warning("The hand-drawn wobbly border radius is missing."))
    return issues


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #


def run(spec_path: Path, html_path: Path | None) -> tuple[int, list[Issue]]:
    try:
        spec = read_spec(spec_path)
    except ValueError as exc:
        return 1, [error(str(exc))]

    issues, models = validate_spec(spec)
    if html_path is not None:
        try:
            html = html_path.read_text(encoding="utf-8")
        except OSError as exc:
            issues.append(error(f"Cannot read prototype HTML: {exc}"))
        else:
            issues.extend(validate_html(spec, models, html))

    failed = any(issue.level == "ERROR" for issue in issues)
    return (1 if failed else 0), issues


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("Usage: validate_flow_spec.py <flow.json> [prototype.html]", file=sys.stderr)
        return 2
    spec_path = Path(argv[1])
    html_path = Path(argv[2]) if len(argv) == 3 else None
    status, issues = run(spec_path, html_path)
    for issue in issues:
        print(f"{issue.level}: {issue.message}")
    if status == 0:
        target = f"{spec_path} and {html_path}" if html_path else str(spec_path)
        print(f"OK: {target} passed flow validation.")
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
