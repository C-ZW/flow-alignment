#!/usr/bin/env python3
"""Validate that a website-derived prototype has an evidence-backed handoff.

An artifact may carry several flows. Each flow derived from a researched journey
needs its own adaptation entry, so a reader can tell which evidence backs which
flow, and what was assumed where.

Usage:
    validate_adaptation.py <adaptation.json> <reference.json> <flow.json>

Exit codes: 0 = valid, 1 = errors found, 2 = bad invocation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ADAPTATION_VERSION = 3
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
FORBIDDEN_CLAIM = re.compile(r"pixel[ -]?perfect|1:1|exact clone|fully cloned", re.IGNORECASE)


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def is_kebab(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def is_text_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def validate_entry(entry: object, index: int, journeys: dict, flows: dict) -> list[str]:
    label = f"adaptations[{index}]"
    if not isinstance(entry, dict):
        return [f"{label} must be an object."]

    errors: list[str] = []
    flow_id = entry.get("flowId")
    if not is_kebab(flow_id):
        errors.append(f"{label}.flowId must be kebab-case.")
    else:
        label = f"adaptation for flow '{flow_id}'"

    if entry.get("mode") not in {"wireframe", "visual-reference"}:
        errors.append(f"{label}.mode must be wireframe or visual-reference.")
    if not isinstance(entry.get("task"), str) or not entry["task"].strip():
        errors.append(f"{label}.task is required.")
    # hypothesis is optional here for the same reason it is optional on a flow: a
    # journey being confirmed with a client has a scenario, not a research question.
    if "hypothesis" in entry and (not isinstance(entry["hypothesis"], str) or not entry["hypothesis"].strip()):
        errors.append(f"{label} has an empty hypothesis; omit it or fill it in.")
    for field in ("preserve", "abstract"):
        if not is_text_list(entry.get(field)):
            errors.append(f"{label}.{field} needs at least one non-empty item.")
    if not is_text_list(entry.get("claims")):
        errors.append(f"{label}.claims needs at least one scope statement.")
    elif any(FORBIDDEN_CLAIM.search(claim) for claim in entry["claims"]):
        errors.append(f"{label}.claims contains an unsupported cloning or fidelity claim.")

    journey = journeys.get(entry.get("journeyId"))
    if journey is None:
        errors.append(f"{label} cites journey '{entry.get('journeyId')}', which is not in reference.json.")
    else:
        status = journey.get("status")
        if status not in {"observed", "partial", "inferred"}:
            errors.append(f"{label} selected a journey with an invalid status.")
        elif status in {"partial", "inferred"} and not is_text_list(entry.get("assumptions")):
            errors.append(f"{label} adapts a {status} journey and must record an assumption.")

    flow = flows.get(flow_id)
    if flow is None:
        if is_kebab(flow_id):
            errors.append(f"{label}: flow.json declares no flow with that id.")
    else:
        if flow.get("task") != entry.get("task"):
            errors.append(f"{label}.task does not match the same field in flow.json.")
        if "hypothesis" in entry and flow.get("hypothesis") != entry["hypothesis"]:
            errors.append(f"{label}.hypothesis does not match the same field in flow.json.")
    return errors


def validate(adaptation: object, reference: object, flow_spec: object) -> list[str]:
    if not isinstance(adaptation, dict) or not isinstance(reference, dict) or not isinstance(flow_spec, dict):
        return ["All three inputs must be JSON objects."]

    errors: list[str] = []
    if adaptation.get("version") != ADAPTATION_VERSION:
        if adaptation.get("version") in (1, 2):
            errors.append(
                "adaptation.json uses a retired shape. Version 3 carries a top-level 'reference' plus an "
                "'adaptations' array with one entry per derived flow."
            )
        else:
            errors.append(f"adaptation.version must equal {ADAPTATION_VERSION}.")
    if not is_kebab(adaptation.get("id")):
        errors.append("adaptation.id must be kebab-case.")

    link = adaptation.get("reference")
    if not isinstance(link, dict):
        errors.append("adaptation.reference must be an object.")
    else:
        if link.get("id") != reference.get("id"):
            errors.append("adaptation.reference.id does not match reference.json.")
        if not isinstance(link.get("path"), str) or not link["path"].strip():
            errors.append("adaptation.reference.path is required.")

    journeys = {
        journey.get("id"): journey
        for journey in reference.get("journeys", [])
        if isinstance(journey, dict)
    }
    flows = {
        flow.get("id"): flow
        for flow in flow_spec.get("flows", [])
        if isinstance(flow, dict)
    }

    entries = adaptation.get("adaptations")
    if not isinstance(entries, list) or not entries:
        errors.append("adaptation.adaptations needs one entry per derived flow.")
        return errors

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        errors.extend(validate_entry(entry, index, journeys, flows))
        if isinstance(entry, dict) and isinstance(entry.get("flowId"), str):
            if entry["flowId"] in seen:
                errors.append(f"Two adaptations claim the same flow: {entry['flowId']}.")
            seen.add(entry["flowId"])
    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: validate_adaptation.py <adaptation.json> <reference.json> <flow.json>", file=sys.stderr)
        return 2
    try:
        adaptation, reference, flow_spec = (load(Path(argument)) for argument in argv[1:])
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: Cannot read JSON input: {exc}")
        return 1
    errors = validate(adaptation, reference, flow_spec)
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        return 1
    count = len(adaptation.get("adaptations", []))
    print(f"OK: {count} flow(s) linked to documented website journeys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
