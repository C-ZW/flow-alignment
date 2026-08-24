#!/usr/bin/env python3
"""Validate a flow-alignment prototype against its JSON source of truth.

flow.json declares where the journey starts and on whose authority, which screens
the meeting is actually about, what is still undecided, every allowed transition,
and what each outcome changed. prototype.html is a view layer: it embeds the same
specification and renders one declarative <template data-flow data-state> per
state.

This script checks that the two agree, that the declared graph is navigable from
the declared entry point, and that rail-only controls never leak into the product
viewport. It cannot check whether the declared entry point is the real one or
whether a branch is missing — those are human judgements. What it can do is
refuse to let them go unstated.

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
from urllib.parse import urlsplit

SPEC_VERSION = 1
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")

# The five things a room disagrees about. Every flow must take a position on each
# one; "open" is a position, silence is not.
REVIEW_ASPECTS = ("entry-point", "navigation", "branches", "failure-recovery", "ending-state")
REVIEW_STATUSES = ("open", "assumed", "confirmed", "not-applicable")
UNSETTLED = ("open", "assumed")
ENTRY_BASES = ("observed", "provided", "assumed")

REQUIRED_ELEMENT_IDS = (
    "observer-hud",
    "flow-selector",
    "flow-title",
    "flow-task",
    "entry-block",
    "entry-basis",
    "entry-why",
    "entry-preconditions",
    "state-stepper",
    "route-details",
    "state-instruction",
    "reset-flow",
    "product-viewport",
    "interaction-mask",
    "spotlight-ring",
    "state-views",
    "flow-spec",
)

# Runtime hooks are addressed by id, so every hook must have exactly one
# element. Keeping the expected tag names here also catches a duplicate-free
# replacement that makes a hook invisible to the browser API or changes its
# semantics (for example, a <div> in place of the JSON <script>).
REQUIRED_ELEMENT_TAGS = {
    "observer-hud": "aside",
    "flow-selector": "select",
    "flow-title": "span",
    "flow-task": "p",
    "entry-block": "div",
    "entry-basis": "span",
    "entry-why": "p",
    "entry-preconditions": "ul",
    "state-stepper": "nav",
    "route-details": "details",
    "state-instruction": "p",
    "reset-flow": "button",
    "product-viewport": "main",
    "interaction-mask": "div",
    "spotlight-ring": "span",
    "state-views": "div",
    "flow-spec": "script",
}

# Vocabulary that belongs to the observer rail and must never appear in a product
# state view. Kept deliberately narrow so real product copy does not trip it, and
# extended per language: an artifact written for Chinese-speaking participants
# leaks the same way an English one does. Add your own product's terms here when
# a team uses different wording for the apparatus.
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
    # Traditional and simplified Chinese rail terms are encoded so the
    # OSS source remains English-only without dropping localized leak detection.
    "\u91cd\u7f6e\u6d41\u7a0b",
    "\u91cd\u65b0\u958b\u59cb\u6d41\u7a0b",
    "\u91cd\u65b0\u5f00\u59cb\u6d41\u7a0b",
    "\u91cd\u555f\u6d41\u7a0b",
    "\u91cd\u542f\u6d41\u7a0b",
    "\u91cd\u65b0\u6e2c\u8a66",
    "\u91cd\u65b0\u6d4b\u8bd5",
    "\u6a21\u64ec\u932f\u8aa4",
    "\u6a21\u62df\u9519\u8bef",
    "\u932f\u8aa4\u6a21\u64ec",
    "\u9519\u8bef\u6a21\u62df",
    "\u9a57\u8b49\u5047\u8aaa",
    "\u9a8c\u8bc1\u5047\u8bf4",
    "\u9a57\u8b49\u5047\u8a2d",
    "\u9a8c\u8bc1\u5047\u8bbe",
    "\u9a57\u8b49\u6d41\u7a0b",
    "\u9a8c\u8bc1\u6d41\u7a0b",
    "\u89c0\u5bdf\u8005\u6307\u5f15",
    "\u89c2\u5bdf\u8005\u6307\u5f15",
    "\u6e2c\u8a66\u4efb\u52d9",
    "\u6d4b\u8bd5\u4efb\u52a1",
    "\u6e2c\u8a66\u8a08\u756b",
    "\u6d4b\u8bd5\u8ba1\u5212",
    "\u6e2c\u8a66\u8173\u672c",
    "\u6d4b\u8bd5\u811a\u672c",
    "\u9059\u6e2c",
    "\u9065\u6d4b",
)

VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

ALLOWED_EXTERNAL_HOSTS = ("fonts.googleapis.com", "fonts.gstatic.com")
CSP_PRECEDENCE_TAGS = {"base", "link", "script", "style"}

# The prototype is deliberately a self-contained file.  Inline engine and
# product CSS are part of the template, while Google Fonts is the only remote
# exception.  Keep this policy in the validator as well as the template so a
# hand-edited artifact cannot silently remove the browser's network boundary.
REQUIRED_CSP_DIRECTIVES = {
    "default-src": ("'none'",),
    "base-uri": ("'none'",),
    "form-action": ("'none'",),
    "script-src": ("'unsafe-inline'",),
    "script-src-attr": ("'none'",),
    "style-src": ("'unsafe-inline'", "https://fonts.googleapis.com"),
    "font-src": ("https://fonts.gstatic.com",),
    "img-src": ("'self'", "data:"),
    "media-src": ("'self'", "data:"),
    "connect-src": ("'none'",),
    "object-src": ("'none'",),
    "frame-src": ("'none'",),
    "child-src": ("'none'",),
    "worker-src": ("'none'",),
    "manifest-src": ("'none'",),
}

BLOCKING_DIALOGS = re.compile(r"\b(?:alert|confirm|prompt)\s*\(")
# Keep the offline check deliberately conservative.  In addition to the
# browser networking APIs, reject the common analytics entry points that can
# silently send data from a file:// prototype.
NETWORK_CALLS = re.compile(
    r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\(|"
    r"\b(?:navigator\s*\.\s*)?sendBeacon\s*\(|"
    r"(?:\b(?:window\s*\.\s*)?analytics|\b(?:window\s*\.\s*)?(?:gtag|ga)|"
    r"\b(?:window\s*\.\s*)?(?:dataLayer|mixpanel|amplitude|posthog))"
    r"(?:\s*\.\s*[A-Za-z_$][\w$]*)?\s*\(",
    re.IGNORECASE,
)
COMPUTED_NETWORK_CALLS = re.compile(
    r"\b(?:window|globalThis|self)\s*\[\s*['\"]"
    r"(?:fetch|xmlhttprequest|websocket|eventsource|sendbeacon)"
    r"['\"]\s*\]\s*\(",
    re.IGNORECASE,
)
REMOTE_LITERAL = re.compile(r"(?:https?:)?//[^\s\"'()<>]+", re.IGNORECASE)
CSS_REMOTE_REFERENCE = re.compile(
    r"(?:url\s*\(\s*|@import\s+)(?:[\"']\s*)?((?:https?:)?//[^\s\"')]+)",
    re.IGNORECASE,
)
REMOTE_SCRIPT_ASSIGNMENT = re.compile(
    r"(?:new\s+Image\s*\(\s*\)|[A-Za-z_$][\w$]*)\s*\.\s*src\s*=\s*"
    r"[\"'](?:https?:)?//",
    re.IGNORECASE,
)
REMOTE_DOM_PROPERTY_ASSIGNMENT = re.compile(
    r"(?:\.\s*(?:src|href|poster|data)|\[\s*['\"](?:src|href|poster|data)['\"]\s*\])"
    r"\s*=\s*[\"']((?:https?:)?//[^\s\"'(),<>]+)",
    re.IGNORECASE,
)
REMOTE_DOM_ATTRIBUTE_ASSIGNMENT = re.compile(
    r"\.\s*setAttribute(?:NS)?\s*\(\s*(?:[^,()]+,\s*)?"
    r"['\"](?:src|srcset|href|xlink:href|poster|data)['\"]\s*,\s*"
    r"['\"]((?:https?:)?//[^\s\"'(),<>]+)",
    re.IGNORECASE,
)
DESIGN_MARKER = "/* ---- Product-specific additions go below this line. ---- */"
CSS_RULE = re.compile(r"([^{}]+)\{([^{}]*)\}")


def parse_csp_policy(policy: str) -> dict[str, tuple[str, ...]] | None:
    """Parse one CSP policy into directives, rejecting malformed duplicates."""
    directives: dict[str, tuple[str, ...]] = {}
    for raw_directive in policy.split(";"):
        tokens = raw_directive.strip().split()
        if not tokens:
            continue
        name = tokens[0].lower()
        if not re.fullmatch(r"[a-z][a-z0-9-]*", name) or name in directives:
            return None
        directives[name] = tuple(tokens[1:])
    return directives


def is_disallowed_external_url(value: object) -> bool:
    """Return whether *value* is a remote URL outside the font allow-list.

    URL strings must be checked by their parsed hostname.  A substring check
    would incorrectly allow e.g. ``https://attacker.test/fonts.googleapis.com``
    and protocol-relative URLs would bypass the old ``http``/``https`` prefix
    check entirely.
    """
    if not isinstance(value, str):
        return False
    candidate = value.strip()
    if not candidate:
        return False
    try:
        parsed = urlsplit(candidate)
        remote = bool(parsed.scheme in {"http", "https"} or candidate.startswith("//"))
        if not remote:
            return False
        hostname = parsed.hostname
    except ValueError:
        # A malformed remote URL is still an external reference and should not
        # be silently treated as a local path.
        return True
    return hostname not in ALLOWED_EXTERNAL_HOSTS


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


def is_text_list(value: object) -> bool:
    return isinstance(value, list) and all(is_text(item) for item in value)


def reachable_from(start: str, transitions: dict[str, list[str]], blocked: set[str] = frozenset()) -> set[str]:
    """States reachable by walking declared transitions, optionally cutting some."""
    seen: set[str] = set()
    pending = [start]
    while pending:
        current = pending.pop()
        if current in seen or current in blocked:
            continue
        seen.add(current)
        pending.extend(transitions.get(current, []))
    return seen


def can_reach_any(starts: set[str], transitions: dict[str, list[str]]) -> set[str]:
    """States that can reach one of *starts* by following declared transitions."""
    reverse: dict[str, set[str]] = {state_id: set() for state_id in transitions}
    for source, targets in transitions.items():
        for target in targets:
            if target in reverse:
                reverse[target].add(source)

    seen: set[str] = set()
    pending = [state_id for state_id in starts if state_id in reverse]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(reverse[current] - seen)
    return seen


# --------------------------------------------------------------------------- #
# flow.json
# --------------------------------------------------------------------------- #


def read_spec(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Cannot read flow specification: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("flow.json must be a JSON object.")
    return data


def validate_states(flow: dict, label: str) -> tuple[list[Issue], dict]:
    """Structural checks over the states array. Returns issues and a graph model."""
    issues: list[Issue] = []
    states = flow.get("states")
    if not isinstance(states, list) or len(states) < 2:
        issues.append(error(f"{label} needs at least two states."))
        return issues, {}

    transitions: dict[str, list[str]] = {}
    navigation: dict[str, dict] = {}
    steps: dict[str, int] = {}
    outcomes: dict[str, dict] = {}
    spotlights: dict[str, list[str]] = {}
    terminal: set[str] = set()

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

        spotlight = state.get("spotlight")
        spotlight_list = state.get("spotlights")
        if spotlight is not None and spotlight_list is not None:
            issues.append(error(
                f"{label} state '{state_id}' must use spotlight or spotlights, not both."
            ))
            spotlight_keys: list[str] = []
        elif spotlight_list is not None:
            if (not isinstance(spotlight_list, list) or not 2 <= len(spotlight_list) <= 3
                    or not all(is_kebab(key) for key in spotlight_list)):
                issues.append(error(
                    f"{label} state '{state_id}' spotlights must contain two or three kebab-case region keys."
                ))
                spotlight_keys = []
            elif len(set(spotlight_list)) != len(spotlight_list):
                issues.append(error(
                    f"{label} state '{state_id}' spotlights must not repeat a region key."
                ))
                spotlight_keys = []
            else:
                spotlight_keys = spotlight_list
        elif spotlight is None:
            issues.append(warning(
                f"{label} state '{state_id}' has no spotlight; its mask falls back to the whole viewport. "
                "Name the smallest coherent action, decision, or result region."
            ))
            spotlight_keys = []
        elif not is_kebab(spotlight):
            issues.append(error(
                f"{label} state '{state_id}' spotlight must be a kebab-case region key."
            ))
            spotlight_keys = []
        else:
            spotlight_keys = [spotlight]
        spotlights[state_id] = spotlight_keys

        scope = state.get("scope")
        if scope is not None and scope not in ("viewport", "shell"):
            issues.append(error(f"{label} state '{state_id}' has scope '{scope}'; use viewport or shell."))
        nav_targets = state.get("navTargets")
        if nav_targets is not None:
            if not isinstance(nav_targets, dict) or not nav_targets:
                issues.append(error(f"{label} state '{state_id}' navTargets must be a non-empty object."))
                nav_targets = {}
            else:
                safe_nav_targets: dict[str, str] = {}
                if scope == "shell" and len(nav_targets) > 1:
                    issues.append(error(
                        f"{label} state '{state_id}' has {len(nav_targets)} routed navigation controls. "
                        "A shell step may focus at most one routed navigation control; split the route or "
                        "declare a single navTarget."
                    ))
                for key, destination in nav_targets.items():
                    if not isinstance(key, str) or not key.strip():
                        issues.append(error(f"{label} state '{state_id}' has a navTargets key that is not a name."))
                    elif not isinstance(destination, str):
                        issues.append(error(
                            f"{label} state '{state_id}' routes nav '{key}' to a destination that is not a "
                            "state id."
                        ))
                    elif destination not in targets:
                        issues.append(error(
                            f"{label} state '{state_id}' routes nav '{key}' to '{destination}', which is not a "
                            "declared transition from that state."
                        ))
                    else:
                        safe_nav_targets[key] = destination
                nav_targets = safe_nav_targets
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

        # An outcome records what the action changed. It belongs to the screen that
        # ends the journey, and nowhere else.
        outcome = state.get("outcome")
        if outcome is not None and state_id not in terminal:
            issues.append(error(
                f"{label} state '{state_id}' declares an outcome but is not terminal. An outcome is the "
                "postcondition of a finished journey."
            ))
        elif state_id in terminal:
            issues.extend(validate_outcome(outcome, label, state_id, transitions[state_id]))
            if isinstance(outcome, dict):
                outcomes[state_id] = outcome

    state_ids = set(transitions)
    for source, targets in transitions.items():
        for target in targets:
            if target not in state_ids:
                issues.append(error(f"{label} state '{source}' transitions to unknown state '{target}'."))

    model = {
        "states": state_ids,
        "transitions": transitions,
        "navigation": navigation,
        "steps": steps,
        "terminal": terminal,
        "outcomes": outcomes,
        "spotlights": spotlights,
    }
    return issues, model


def validate_outcome(outcome: object, label: str, state_id: str, targets: list[str]) -> list[Issue]:
    """A terminal state must say what happened, what changed, and what comes next."""
    if not isinstance(outcome, dict):
        return [error(
            f"{label} terminal state '{state_id}' has no outcome. Declare what happened, what it changed, "
            "and the continuation that shows it."
        )]

    issues: list[Issue] = []
    if not is_text(outcome.get("happened")):
        issues.append(error(f"{label} outcome for '{state_id}' is missing 'happened'."))
    changed = outcome.get("changed")
    if not is_text_list(changed) or not changed:
        issues.append(error(
            f"{label} outcome for '{state_id}' needs a non-empty 'changed' list. If nothing changed, say so "
            "in words — a branch that changes nothing is itself worth confirming."
        ))
    if "continuation" not in outcome:
        issues.append(error(
            f"{label} outcome for '{state_id}' must declare a continuation, or null when the journey really "
            "stops here."
        ))
    else:
        continuation = outcome["continuation"]
        if continuation is None:
            if targets:
                issues.append(error(
                    f"{label} outcome for '{state_id}' declares no continuation but the state still "
                    "transitions somewhere; terminal outcomes with continuation null must have no "
                    "transitions."
                ))
        elif not isinstance(continuation, str):
            issues.append(error(f"{label} outcome for '{state_id}' has a continuation that is not a state id."))
        else:
            matching = targets.count(continuation)
            if matching == 0:
                issues.append(error(
                    f"{label} outcome for '{state_id}' continues to '{continuation}', which is not a declared "
                    "transition from that state."
                ))
            if matching != 1 or len(targets) != 1:
                issues.append(error(
                    f"{label} outcome for '{state_id}' must declare exactly one transition matching "
                    f"continuation '{continuation}'."
                ))
    return issues


def validate_entry(flow: dict, label: str, model: dict) -> tuple[list[Issue], dict]:
    """Where the journey starts, and on whose authority."""
    issues: list[Issue] = []
    entry = flow.get("entry")
    if not isinstance(entry, dict):
        issues.append(error(
            f"{label} needs an 'entry' object declaring the state the journey starts from, why, on what basis, "
            "and which preconditions it skips."
        ))
        return issues, {}

    state_id = entry.get("state")
    if not isinstance(state_id, str) or state_id not in model["states"]:
        issues.append(error(f"{label}.entry.state must reference a declared state."))
        state_id = None
    else:
        if model["steps"].get(state_id, 1) != 1:
            issues.append(error(
                f"{label}.entry.state '{state_id}' is not step 1. The journey has to start at the beginning."
            ))
        if state_id in model["terminal"]:
            issues.append(error(f"{label}.entry.state '{state_id}' is also terminal."))

    basis = entry.get("basis")
    if basis not in ENTRY_BASES:
        issues.append(error(f"{label}.entry.basis must be one of: {', '.join(ENTRY_BASES)}."))
    elif basis == "observed" and not (is_text_list(entry.get("evidence")) and entry.get("evidence")):
        issues.append(error(
            f"{label}.entry claims the starting point was observed but cites no evidence. Cite the evidence "
            "ids, or set basis to 'assumed'."
        ))
    if not is_text(entry.get("why")):
        issues.append(error(
            f"{label}.entry.why must say why a real user is standing here when the journey starts."
        ))

    preconditions = entry.get("preconditions")
    if not is_text_list(preconditions):
        issues.append(error(
            f"{label}.entry.preconditions must be an array listing what this journey assumes has already "
            "happened. Use [] to state plainly that there is nothing."
        ))
    elif not preconditions:
        issues.append(warning(
            f"{label}.entry declares no preconditions. Is the walker really starting cold — not signed in, "
            "with no existing data?"
        ))
    return issues, {"state": state_id, "basis": basis}


def validate_focus(flow: dict, label: str, model: dict, entry_state: str | None) -> tuple[list[Issue], list[str]]:
    """Which screens this meeting is actually about."""
    issues: list[Issue] = []
    focus = flow.get("focus")
    if not isinstance(focus, list) or not focus:
        issues.append(error(
            f"{label} needs a non-empty 'focus' array naming the screens this walkthrough exists to settle."
        ))
        return issues, []
    if not all(isinstance(state_id, str) for state_id in focus):
        issues.append(error(f"{label}.focus must contain only state id strings."))

    string_focus = [state_id for state_id in focus if isinstance(state_id, str)]
    if len(set(string_focus)) != len(string_focus):
        issues.append(error(f"{label}.focus lists the same state twice."))

    resolved: list[str] = []
    for state_id in dict.fromkeys(string_focus):
        if state_id not in model["states"]:
            issues.append(error(f"{label}.focus names undeclared state '{state_id}'."))
            continue
        if state_id == entry_state:
            issues.append(error(
                f"{label}.focus names '{state_id}', which is also the entry point. Opening on the screen under "
                "discussion is the thing this field exists to prevent."
            ))
            continue
        resolved.append(state_id)

    if entry_state:
        walkable = reachable_from(entry_state, model["transitions"])
        for state_id in resolved:
            if state_id not in walkable:
                issues.append(error(
                    f"{label}.focus names '{state_id}', which cannot be reached from the entry point by "
                    "walking declared transitions."
                ))
    return issues, resolved


def validate_review(flow: dict, label: str, model: dict, entry_basis: str | None) -> list[Issue]:
    """The review ledger: a stated position on each of the five things rooms disagree about."""
    issues: list[Issue] = []
    review = flow.get("review")
    if not isinstance(review, list) or not review:
        issues.append(error(
            f"{label} needs a 'review' array taking a position on each of: {', '.join(REVIEW_ASPECTS)}. "
            "An unanswered question is why this artifact exists; leaving it unwritten is not."
        ))
        return issues

    by_aspect: dict[str, dict] = {}
    for index, item in enumerate(review):
        if not isinstance(item, dict):
            issues.append(error(f"{label}.review[{index}] must be an object."))
            continue
        aspect = item.get("aspect")
        if aspect not in REVIEW_ASPECTS:
            issues.append(error(
                f"{label}.review[{index}] has aspect '{aspect}'; use one of: {', '.join(REVIEW_ASPECTS)}."
            ))
            continue
        if aspect in by_aspect:
            issues.append(error(f"{label}.review declares '{aspect}' twice."))
            continue
        by_aspect[aspect] = item

        point = f"{label}.review['{aspect}']"
        status = item.get("status")
        if not isinstance(status, str) or status not in REVIEW_STATUSES:
            issues.append(error(f"{point}.status must be one of: {', '.join(REVIEW_STATUSES)}."))
        if not is_text(item.get("proposal")):
            issues.append(error(f"{point}.proposal must state what this artifact currently proposes."))
        if isinstance(status, str) and status in UNSETTLED and not is_text(item.get("question")):
            issues.append(error(
                f"{point} is {status} but asks nothing. Write the question to put to the room."
            ))

        states = item.get("states")
        if not isinstance(states, list):
            issues.append(error(f"{point}.states must be an array of state ids."))
        elif not all(isinstance(one, str) for one in states):
            issues.append(error(f"{point}.states must contain only state id strings."))
        else:
            for one in states:
                if one not in model["states"]:
                    issues.append(error(f"{point}.states names undeclared state '{one}'."))
            if not states and status != "not-applicable":
                issues.append(error(
                    f"{point} names no states, so the facilitator cannot raise it beside a specific screen. "
                    "Attach it to the screens it is about."
                ))
        if "alternatives" in item and not is_text_list(item["alternatives"]):
            issues.append(error(f"{point}.alternatives must be an array of non-empty strings."))
        if "basis" in item and not is_text(item["basis"]):
            issues.append(error(f"{point}.basis is empty; omit it or fill it in."))

    for aspect in REVIEW_ASPECTS:
        if aspect not in by_aspect:
            issues.append(error(
                f"{label}.review says nothing about '{aspect}'. Silence reads as agreement; say 'open', "
                "'assumed', 'confirmed', or 'not-applicable'."
            ))

    # A ledger that contradicts the rest of the specification is decoration.
    entry_point = by_aspect.get("entry-point", {})
    if entry_basis == "assumed" and entry_point.get("status") == "confirmed":
        issues.append(error(
            f"{label}.review['entry-point'] is confirmed while entry.basis is 'assumed'. One of the two is wrong."
        ))
    statuses = [item.get("status") for item in by_aspect.values()]
    if len(by_aspect) == len(REVIEW_ASPECTS) and all(status == "confirmed" for status in statuses):
        issues.append(warning(
            f"{label} declares every review point confirmed. If nothing is open, what is the walkthrough for?"
        ))
    return issues


def validate_graph(label: str, model: dict, entry_state: str | None) -> list[Issue]:
    """Reachability, branch semantics, and postconditions that survive the journey."""
    issues: list[Issue] = []
    if entry_state is None:
        return issues

    transitions = model["transitions"]
    steps = model["steps"]
    terminal = model["terminal"]
    outcomes = model["outcomes"]

    reachable = reachable_from(entry_state, transitions)
    for orphan in sorted(model["states"] - reachable):
        issues.append(error(f"{label} state '{orphan}' is unreachable from the entry point."))
    if not terminal:
        issues.append(error(f"{label} needs at least one state marked terminal."))
    elif not terminal & reachable:
        issues.append(error(f"{label} has no terminal state reachable from the entry point."))

    # A reachable terminal is not enough: a second branch can still fall into a
    # closed loop while another branch ends successfully. Every reachable state
    # must be able to reach a structurally valid terminal outcome. Continuation
    # screens are accepted as postcondition endpoints because they deliberately
    # come after the terminal action and do not need to lead to another outcome.
    valid_terminal_outcomes: set[str] = set()
    outcome_continuations: set[str] = set()
    for state_id in terminal & reachable:
        outcome = outcomes.get(state_id)
        targets = transitions.get(state_id, [])
        continuation = outcome.get("continuation") if isinstance(outcome, dict) else None
        outcome_is_valid = (
            isinstance(outcome, dict)
            and is_text(outcome.get("happened"))
            and is_text_list(outcome.get("changed"))
            and bool(outcome.get("changed"))
            and "continuation" in outcome
            and (
                (continuation is None and not targets)
                or (
                    isinstance(continuation, str)
                    and continuation in model["states"]
                    and targets.count(continuation) == 1
                    and len(targets) == 1
                )
            )
        )
        if outcome_is_valid:
            valid_terminal_outcomes.add(state_id)
            if isinstance(continuation, str):
                outcome_continuations.add(continuation)

    ending_states = valid_terminal_outcomes | outcome_continuations
    if terminal & reachable:
        can_reach_ending = can_reach_any(ending_states, transitions)
        for state_id in sorted(reachable - can_reach_ending):
            issues.append(error(
                f"{label} state '{state_id}' is reachable from the entry point but cannot reach a valid "
                "terminal outcome; this branch is a closed loop or has no ending."
            ))

    # Steps that share a number are drawn as alternatives. They have to be
    # alternatives: if you can walk from one to the other without going back, the
    # rail is telling the room something the graph contradicts.
    forward = {
        source: [target for target in targets
                 if target in steps and source in steps and steps[target] >= steps[source]]
        for source, targets in transitions.items()
    }
    by_step: dict[int, list[str]] = {}
    for state_id, step in steps.items():
        by_step.setdefault(step, []).append(state_id)
    for step, siblings in sorted(by_step.items()):
        if len(siblings) < 2:
            continue
        for source in sorted(siblings):
            downstream = reachable_from(source, forward) - {source}
            for other in sorted(set(siblings) & downstream):
                issues.append(error(
                    f"{label} draws '{source}' and '{other}' as alternatives at step {step}, but '{other}' "
                    f"follows '{source}'. Consecutive screens need consecutive step numbers."
                ))

    # The converse is a judgement call, so it warns: a real fork whose targets sit
    # at different steps is drawn as a straight line, which reads as one path.
    for source, targets in forward.items():
        onward = [target for target in targets if target != source and steps.get(target, 0) > steps.get(source, 0)]
        if len(onward) > 1 and len({steps[target] for target in onward}) > 1:
            issues.append(warning(
                f"{label} state '{source}' forks to {', '.join(sorted(onward))}, which sit at different steps, "
                "so the rail draws them as consecutive screens rather than alternatives."
            ))

    # An outcome the walker cannot see is not an outcome. Returning to a screen
    # already passed on the way here shows the world before the action.
    continuations: dict[str, str] = {}
    for state_id in sorted(terminal & reachable):
        outcome = outcomes.get(state_id)
        if not isinstance(outcome, dict):
            continue
        continuation = outcome.get("continuation")
        if not isinstance(continuation, str) or continuation not in model["states"]:
            continue
        if continuation in continuations:
            issues.append(error(
                f"{label} sends both '{continuations[continuation]}' and '{state_id}' on to '{continuation}'. "
                "One screen cannot show two different outcomes."
            ))
        else:
            continuations[continuation] = state_id
        already_seen = reachable_from(entry_state, transitions, blocked={state_id})
        if continuation in already_seen:
            issues.append(error(
                f"{label} outcome '{state_id}' continues to '{continuation}', a screen the walker already "
                "passed through. It still shows the world before the action, so the outcome is undone in "
                "front of the room. Declare a continuation that shows what changed."
            ))

    # A state nobody can leave is either the end of the journey, the postcondition
    # of one, or an accident.
    for state_id in sorted(model["states"]):
        if transitions.get(state_id):
            continue
        if state_id in terminal or state_id in continuations:
            continue
        issues.append(error(
            f"{label} state '{state_id}' is a dead end: it has no transitions and is neither terminal nor the "
            "continuation of an outcome."
        ))

    return issues


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

    state_issues, model = validate_states(flow, label)
    issues.extend(state_issues)
    if not model:
        return issues, {"id": flow_id, "states": set(), "transitions": {}, "navigation": {},
                        "review": []}

    entry_issues, entry = validate_entry(flow, label, model)
    issues.extend(entry_issues)
    focus_issues, focus = validate_focus(flow, label, model, entry.get("state"))
    issues.extend(focus_issues)
    issues.extend(validate_review(flow, label, model, entry.get("basis")))
    issues.extend(validate_graph(label, model, entry.get("state")))

    model.update({
        "id": flow_id,
        "entry": entry,
        "focus": focus,
        "review": flow.get("review") if isinstance(flow.get("review"), list) else [],
        "responsiveAlternatives": flow.get("responsiveAlternatives"),
    })
    return issues, model


def validate_spec(spec: object) -> tuple[list[Issue], list[dict]]:
    issues: list[Issue] = []
    if not isinstance(spec, dict):
        return [error("flow.json must be a JSON object.")], []
    try:
        serialized = json.dumps(spec, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        issues.append(error(f"flow.json contains values that are not JSON-compatible: {exc}."))
        serialized = ""
    if "</script" in serialized.lower():
        issues.append(error(
            "flow.json contains '</script', which would break or inject markup when embedded in prototype.html. "
            "Rewrite that copy without a literal script-closing sequence."
        ))
    if type(spec.get("version")) is not int or spec.get("version") != SPEC_VERSION:
        issues.append(error(f"flow.json version must equal {SPEC_VERSION}."))

    flows = spec.get("flows")
    if not isinstance(flows, list) or not flows:
        issues.append(error("flow.json needs a non-empty 'flows' array."))
        return issues, []
    if len(flows) > 3:
        issues.append(error(
            f"{len(flows)} flows in one artifact. One artifact may carry at most three related journeys."
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

    # A design alternative that changes the screens is a second flow, not a note.
    # When a review point claims one, the flow it names has to be in this artifact.
    for model in models:
        flow_id = model.get("id")
        for item in model.get("review", []):
            if not isinstance(item, dict) or "alternativeFlows" not in item:
                continue
            named = item["alternativeFlows"]
            if not isinstance(named, list) or not named or not all(isinstance(one, str) for one in named):
                issues.append(error(f"flow '{flow_id}' review['{item.get('aspect')}'].alternativeFlows must be "
                                    "a non-empty array of flow ids."))
                continue
            for other in named:
                if other == flow_id:
                    issues.append(error(
                        f"flow '{flow_id}' review['{item.get('aspect')}'] names itself as the alternative."
                    ))
                elif other not in seen:
                    issues.append(error(
                        f"flow '{flow_id}' review['{item.get('aspect')}'] names alternative flow '{other}', "
                        "which this artifact does not build. A design alternative the room cannot walk is "
                        "not an alternative yet."
                    ))

    # A breakpoint that changes the action graph is a second complete flow. A
    # viewport-only note would otherwise hide a real navigation step.
    for model in models:
        flow_id = model.get("id")
        alternatives = model.get("responsiveAlternatives")
        if alternatives is None:
            continue
        if not isinstance(alternatives, list) or not alternatives:
            issues.append(error(
                f"flow '{flow_id}'.responsiveAlternatives must be a non-empty array."
            ))
            continue
        used_viewports: set[str] = set()
        for index, item in enumerate(alternatives):
            point = f"flow '{flow_id}'.responsiveAlternatives[{index}]"
            if not isinstance(item, dict):
                issues.append(error(f"{point} must be an object."))
                continue
            other = item.get("flowId")
            viewport = item.get("viewport")
            if not isinstance(other, str):
                issues.append(error(f"{point}.flowId must be a flow id string."))
            elif other == flow_id:
                issues.append(error(f"{point}.flowId may not name its own flow."))
            elif other not in seen:
                issues.append(error(f"{point}.flowId '{other}' is not built in this artifact."))
            if viewport not in ("narrow", "wide"):
                issues.append(error(f"{point}.viewport must be narrow or wide."))
            elif viewport in used_viewports:
                issues.append(error(
                    f"flow '{flow_id}' declares more than one responsive alternative for viewport '{viewport}'."
                ))
            else:
                used_viewports.add(viewport)
            if not is_text(item.get("reason")):
                issues.append(error(f"{point}.reason must say why the action graph changes."))
    return issues, models


# --------------------------------------------------------------------------- #
# prototype.html
# --------------------------------------------------------------------------- #


class TemplateRecord:
    def __init__(self, flow_id: str | None, state_id: str | None) -> None:
        self.flow_id = flow_id
        self.state_id = state_id
        self.gotos: list[tuple[str, str]] = []  # (tag, target)
        self.goto_spotlights: list[tuple[str, set[str]]] = []
        self.spotlights: list[str] = []
        self.jumps: list[str] = []
        self.navs: list[str] = []
        self.inline_handlers: list[str] = []
        self.text_parts: list[str] = []

    @property
    def key(self) -> str:
        return f"{self.flow_id}/{self.state_id}"

    def searchable_text(self) -> str:
        return " ".join(self.text_parts).lower()


class PrototypeParser(HTMLParser):
    """Collects the structural facts the validator needs from prototype.html."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, dict]] = []
        self.element_ids: set[str] = set()
        self.element_id_tags: dict[str, list[str]] = {}
        self.templates: list[TemplateRecord] = []
        self.template_stack: list[TemplateRecord] = []
        self.scripts: dict[str, list[str]] = {}
        self.current_script: str | None = None
        self.viewport_children: list[str] = []
        self.viewport_text: list[str] = []
        self.orphan_body_text: list[str] = []
        self.shell_gotos: list[str] = []
        self.templates_in_shell: list[str] = []
        self.templates_outside_container: list[str] = []
        self.external_refs: list[str] = []
        self.csp_policies: list[str] = []
        self.csp_effective_positions: list[bool] = []
        self.fetchable_content_seen = False
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

        if tag == "meta" and attr_map.get("http-equiv", "").lower() == "content-security-policy":
            self.csp_policies.append(attr_map.get("content", ""))
            self.csp_effective_positions.append(
                self._in_context(lambda open_tag, _: open_tag == "head")
                and not self.fetchable_content_seen
            )

        if tag in CSP_PRECEDENCE_TAGS or (
            tag == "meta" and attr_map.get("http-equiv", "").lower() == "refresh"
        ):
            self.fetchable_content_seen = True

        if attr_map.get("id"):
            element_id = attr_map["id"]
            self.element_ids.add(element_id)
            self.element_id_tags.setdefault(element_id, []).append(tag)

        if self._in_viewport():
            self.viewport_children.append(tag)

        for key, value in attr_map.items():
            if key not in ("src", "href", "action", "formaction", "poster", "data") and not key.endswith(":href"):
                continue
            if is_disallowed_external_url(value):
                self.external_refs.append(value)
        for key in ("srcset", "srcdoc", "style"):
            value = attr_map.get(key, "")
            for match in REMOTE_LITERAL.findall(value):
                if is_disallowed_external_url(match):
                    self.external_refs.append(match)

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
                record = self.template_stack[-1]
                record.gotos.append((tag, goto))
                regions = {
                    attrs.get("data-spotlight")
                    for _, attrs in self.stack
                    if attrs.get("data-spotlight")
                }
                if attr_map.get("data-spotlight"):
                    regions.add(attr_map["data-spotlight"])
                record.goto_spotlights.append((goto, regions))
            elif self._in_shell():
                self.shell_gotos.append(goto)
            elif self._in_hud():
                self.hud_gotos.append(goto)

        if self.template_stack:
            record = self.template_stack[-1]
            if attr_map.get("data-spotlight"):
                record.spotlights.append(attr_map["data-spotlight"])
            for key, value in attr_map.items():
                if key.startswith("on"):
                    record.inline_handlers.append(f"{tag}[{key}]")
                if key in ("title", "aria-label", "placeholder", "value", "alt"):
                    record.text_parts.append(value)

        if tag == "template":
            record = TemplateRecord(
                attr_map.get("data-flow"),
                attr_map.get("data-state"),
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
        elif data.strip() and self.stack and self.stack[-1][0] == "body":
            self.orphan_body_text.append(data.strip())


def validate_html(spec: dict, models: list[dict], html: str) -> list[Issue]:
    issues: list[Issue] = []
    parser = PrototypeParser()
    parser.feed(html)
    parser.close()

    # A static scan is useful for authoring feedback, but it cannot prevent a
    # browser from receiving a URL assembled at runtime.  Require the same
    # restrictive policy in every artifact so file:// prototypes retain their
    # inline engine while the browser blocks network exfiltration and remote
    # product assets as a second line of defense.
    if len(parser.csp_policies) != 1:
        issues.append(error(
            "prototype.html must include exactly one Content-Security-Policy meta tag."
        ))
    else:
        if parser.csp_effective_positions != [True]:
            issues.append(error(
                "The Content-Security-Policy meta tag must be inside <head> and precede every "
                "base, link, style, script, or refresh directive so the browser enforces it before "
                "anything can load or execute."
            ))
        policy = parse_csp_policy(parser.csp_policies[0])
        if policy is None:
            issues.append(error("The Content-Security-Policy meta tag is malformed or repeats a directive."))
        else:
            expected_names = set(REQUIRED_CSP_DIRECTIVES)
            actual_names = set(policy)
            if actual_names != expected_names:
                missing = ", ".join(sorted(expected_names - actual_names)) or "none"
                extra = ", ".join(sorted(actual_names - expected_names)) or "none"
                issues.append(error(
                    "The Content-Security-Policy must contain the required restrictive directives only; "
                    f"missing: {missing}; unexpected: {extra}."
                ))
            for name, expected in REQUIRED_CSP_DIRECTIVES.items():
                actual = policy.get(name)
                if actual is None:
                    continue
                if len(actual) != len(expected) or set(actual) != set(expected):
                    issues.append(error(
                        f"Content-Security-Policy directive {name} is too permissive; "
                        f"expected {' '.join(expected)!r}."
                    ))

    if parser.orphan_body_text:
        excerpt = " ".join(parser.orphan_body_text)[:120]
        issues.append(error(
            "prototype.html contains raw text between its editable regions: "
            f"{excerpt!r}. This usually means a closing tag or the STATE VIEWS / ENGINE comment boundary "
            "was duplicated or removed."
        ))

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

    # 2. The generic engine contract. Every runtime hook is looked up by id and
    # therefore must exist exactly once with its expected element type. A
    # duplicate before the real element would otherwise be selected by
    # getElementById(), making the spec, viewport, mask, or rail hook disappear
    # at runtime while a set-based presence check still passed.
    for element_id in REQUIRED_ELEMENT_IDS:
        tags = parser.element_id_tags.get(element_id, [])
        if not tags:
            issues.append(error(f"prototype.html is missing the required element #{element_id}."))
            continue
        if len(tags) != 1:
            issues.append(error(
                f"prototype.html must contain exactly one #{element_id} element; found {len(tags)}."
            ))
        else:
            expected = REQUIRED_ELEMENT_TAGS.get(element_id)
            if expected and tags[0] != expected:
                issues.append(error(
                    f"prototype.html #{element_id} must be <{expected}>, found <{tags[0]}>."
                ))

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

        # 6. Rail vocabulary must never reach a product screen.
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
        expected_spotlights = model["spotlights"].get(record.state_id, [])
        if expected_spotlights:
            for expected_spotlight in expected_spotlights:
                matches = record.spotlights.count(expected_spotlight)
                if matches != 1:
                    issues.append(error(
                        f"Template '{record.key}' needs exactly one data-spotlight=\"{expected_spotlight}\"; "
                        f"found {matches}."
                    ))
            unexpected = sorted(set(record.spotlights) - set(expected_spotlights))
            if unexpected:
                issues.append(error(
                    f"Template '{record.key}' contains undeclared spotlight region(s): {', '.join(unexpected)}."
                ))
            for target, regions in record.goto_spotlights:
                if not set(expected_spotlights) & regions:
                    issues.append(error(
                        f"Template '{record.key}' offers data-goto=\"{target}\" outside its declared "
                        f"spotlight region(s) {', '.join(expected_spotlights)}. Put every action for this step "
                        "inside a focused region."
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
            if not records:
                issues.append(error(f"No <template data-flow=\"{flow_id}\" data-state=\"{state_id}\"> found."))
                continue
            offered = {target for record in records for _, target in record.gotos}
            offered |= set(model["navigation"].get(state_id, {}).values())
            for target in model["transitions"].get(state_id, []):
                if target in offered:
                    continue
                issues.append(error(
                    f"Flow '{flow_id}' declares {state_id} -> {target}, but nothing offers that action. "
                    "Add a button with data-goto, route a nav key to it, or remove the transition."
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

    # 8. The surrounding product shell stays static; the rail stays out of the product.
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
        issues.append(error(
            f"External resource is not permitted in a local artifact: {reference}. "
            "Google Fonts is the only remote-resource exception."
        ))
    script_text = "\n".join("".join(chunks) for name, chunks in parser.scripts.items() if name != "flow-spec")
    if BLOCKING_DIALOGS.search(html):
        issues.append(error("Do not use alert(), confirm(), or prompt() as a product experience."))
    if (
        NETWORK_CALLS.search(script_text)
        or COMPUTED_NETWORK_CALLS.search(script_text)
        or REMOTE_SCRIPT_ASSIGNMENT.search(script_text)
        or REMOTE_DOM_PROPERTY_ASSIGNMENT.search(script_text)
        or REMOTE_DOM_ATTRIBUTE_ASSIGNMENT.search(script_text)
    ):
        issues.append(error("The prototype must run offline; remove network calls."))
    for reference in REMOTE_LITERAL.findall(script_text):
        if is_disallowed_external_url(reference):
            issues.append(error(
                f"External resource is not permitted in a local artifact: {reference}. "
                "Google Fonts is the only remote-resource exception."
            ))
    for reference in CSS_REMOTE_REFERENCE.findall(html):
        if is_disallowed_external_url(reference):
            issues.append(error(
                f"External CSS resource is not permitted in a local artifact: {reference}. "
                "Google Fonts is the only remote-resource exception."
            ))

    # The 13px floor applies to authored product CSS as well as the generic
    # sketchbook system. Small labels are still part of the artifact the room
    # must be able to read.
    if DESIGN_MARKER in html:
        product_css = html.split(DESIGN_MARKER, 1)[1].split("</style>", 1)[0]
        for selector, declarations in CSS_RULE.findall(product_css):
            for declaration in re.findall(
                r"(?:^|;)\s*font(?:-size)?\s*:\s*([^;]+)", declarations, re.IGNORECASE
            ):
                for size in re.findall(r"(?<![\w.])(\d+(?:\.\d+)?)px", declaration):
                    if float(size) < 13:
                        issues.append(error(
                            f"Product CSS selector '{selector.strip()}' uses {size}px text; "
                            "the sketchbook minimum is 13px."
                        ))

    # 9b. Product CSS must not neutralize the generic interaction mask. The
    # design-system byte check only proves the original rule still exists; a
    # later product rule can otherwise override it while appearing compliant.
    if DESIGN_MARKER in html:
        product_css = html.split(DESIGN_MARKER, 1)[1].split("</style>", 1)[0]
        product_css = re.sub(r"/\*.*?\*/", "", product_css, flags=re.S)
        for selector_text, declaration_text in CSS_RULE.findall(product_css):
            selectors = [selector.strip() for selector in selector_text.split(",")]
            declarations = {
                name.strip().lower(): value.strip().lower()
                for item in declaration_text.split(";")
                if ":" in item
                for name, value in [item.split(":", 1)]
            }
            if any("#product-viewport" in selector for selector in selectors):
                for prop in ("position", "z-index"):
                    if prop in declarations:
                        issues.append(error(
                            f"Product CSS overrides #product-viewport {prop}; the generic spotlight owns "
                            "this mask-critical property."
                        ))
            if any(
                token in selector
                for selector in selectors
                for token in ("#interaction-mask", "#spotlight-ring", ".spotlight-ring", ".mask-pane")
            ):
                issues.append(error(
                    "Product CSS styles the generic interaction mask. Spotlight geometry and paint belong to "
                    "the shared engine."
                ))
            if any(".product-context" in selector for selector in selectors):
                for prop in ("filter", "opacity"):
                    if prop in declarations:
                        issues.append(error(
                            f"Product CSS overrides .product-context {prop}; it traps routed navigation beneath "
                            "the interaction mask."
                        ))

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
        print(f"OK: {target} passed flow specification validation.")
        print(
            "Structure only. Whether this is the real entry point, whether a branch is missing, and whether "
            "the screens read like the product are decided by walking it with people."
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
