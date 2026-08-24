#!/usr/bin/env python3
"""Validate that a website-derived prototype has an evidence-backed handoff.

An artifact may carry several flows. Each flow derived from a researched journey
needs its own adaptation entry, so a reader can tell which evidence backs which
flow, and what was assumed where.

The load-bearing check is the last one: an assumption recorded only here is an
assumption nobody in the meeting will ever see. When the research was incomplete,
the prototype's review ledger has to carry that forward.

Usage:
    validate_adaptation.py <adaptation.json> <reference.json> <flow.json>

Exit codes: 0 = valid, 1 = errors found, 2 = bad invocation.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path, PureWindowsPath

ADAPTATION_VERSION = 1
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
FORBIDDEN_CLAIM = re.compile(r"pixel[ -]?perfect|1:1|exact clone|fully cloned", re.IGNORECASE)
UNSETTLED = {"open", "assumed"}


def _repository_root() -> Path:
    """Return the canonical repository root when this script is run directly."""
    # The canonical source lives at ``<root>/.claude/skills/.../scripts``.  A
    # caller may still run the validator from another working directory, so
    # keep cwd as the first choice for ordinary CLI use and fall back to the
    # source-relative root for programmatic calls.
    cwd = Path.cwd().resolve()
    if (cwd / ".claude").is_dir() or (cwd / "references").is_dir():
        return cwd
    return Path(__file__).resolve().parents[4]


def _resolve_declared_reference(
    declared: object,
    supplied_path: Path | str | None,
    base_dir: Path | str | None,
) -> tuple[Path | None, list[str]]:
    """Resolve and verify ``reference.path`` against the supplied input path."""
    if not isinstance(declared, str) or not declared.strip():
        return None, []

    path_text = declared.strip()
    declared_path = Path(path_text).expanduser()
    windows_path = PureWindowsPath(path_text)
    if (
        declared_path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in declared_path.parts
        or ".." in windows_path.parts
    ):
        return None, [
            "adaptation.reference.path must be a repository-relative path without parent traversal."
        ]
    errors: list[str] = []

    # When a caller supplies a base directory, it is a security boundary, not
    # merely a lookup hint.  Resolving the path before checking containment
    # catches an otherwise repository-relative symlink that points out of the
    # repository (or out of the caller's explicit base directory).
    roots = []
    if base_dir is not None:
        roots.append(Path(base_dir).expanduser().resolve())
    else:
        roots.extend(root for root in (_repository_root(), Path.cwd().resolve()) if root not in roots)

    candidates: list[Path] = []
    for root in roots:
        try:
            candidate = (root / declared_path).resolve()
            candidate.relative_to(root)
        except (OSError, RuntimeError, ValueError):
            errors.append(
                "adaptation.reference.path must resolve inside the repository/base directory; "
                "a symlink or path component escapes that boundary."
            )
            continue
        if candidate not in candidates:
            candidates.append(candidate)

    supplied = Path(supplied_path).expanduser().resolve() if supplied_path is not None else None
    supplied_inside = supplied is None or any(
        _is_within(supplied, root) for root in roots
    )
    if supplied is not None and not supplied_inside:
        errors.append(
            "adaptation.reference supplied reference must resolve inside the repository/base directory; "
            "a symlink or path component escapes that boundary."
        )

    if supplied is not None:
        if not supplied.is_file():
            errors.append(f"adaptation.reference supplied reference does not exist: {supplied}.")
        if supplied_inside and not any(candidate == supplied for candidate in candidates):
            errors.append(
                "adaptation.reference.path does not resolve to the reference JSON supplied to the validator."
            )
        selected = supplied if supplied_inside else None
    else:
        existing = [candidate for candidate in candidates if candidate.is_file()]
        selected = existing[0] if existing else None

    if selected is None or not selected.is_file():
        errors.append(
            f"adaptation.reference.path does not point to an existing reference JSON: {declared!r}."
        )
        return None, errors
    return selected, errors


def _load_reference_file(path: Path) -> tuple[object | None, list[str]]:
    """Load a declared reference path without leaking parser/type exceptions."""
    try:
        return json.loads(path.read_text(encoding="utf-8")), []
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [f"adaptation.reference.path cannot be read as JSON: {exc}."]


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def is_kebab(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def is_text_list(value: object) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(item, str) and item.strip() for item in value)


def _is_within(candidate: Path, root: Path) -> bool:
    """Return whether a resolved path remains inside a resolved root."""
    try:
        candidate.relative_to(root)
    except ValueError:
        return False
    return True


def validate_entry(entry: object, index: int, journeys: dict, flows: dict,
                   evidence_kinds: dict[str, str]) -> list[str]:
    label = f"adaptations[{index}]"
    if not isinstance(entry, dict):
        return [f"{label} must be an object."]

    errors: list[str] = []
    flow_id = entry.get("flowId")
    if not is_kebab(flow_id):
        errors.append(f"{label}.flowId must be kebab-case.")
    else:
        label = f"adaptation for flow '{flow_id}'"

    mode = entry.get("mode")
    if not isinstance(mode, str) or mode not in {"wireframe", "visual-reference"}:
        errors.append(f"{label}.mode must be wireframe or visual-reference.")
    if mode == "visual-reference":
        visual = entry.get("visualReference")
        if not isinstance(visual, dict):
            errors.append(
                f"{label}.visualReference is required in visual-reference mode so the product canvas does "
                "not fall back to a generic layout."
            )
        else:
            cited = visual.get("evidence")
            if not is_text_list(cited):
                errors.append(f"{label}.visualReference.evidence needs at least one screenshot evidence id.")
            else:
                for one in cited:
                    if one not in evidence_kinds:
                        errors.append(
                            f"{label}.visualReference cites evidence '{one}', which reference.json does not record."
                        )
                    elif evidence_kinds[one] != "screenshot":
                        errors.append(
                            f"{label}.visualReference evidence '{one}' is not a screenshot. Layout claims need "
                            "rendered visual evidence."
                        )
            for field in ("shell", "hierarchy", "density"):
                if not is_text_list(visual.get(field)):
                    errors.append(f"{label}.visualReference.{field} needs at least one observed layout decision.")
            if "responsive" in visual and not is_text_list(visual.get("responsive")):
                errors.append(
                    f"{label}.visualReference.responsive must be a non-empty list when present; otherwise "
                    "record the adapted breakpoint behavior in assumptions."
                )
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

    journey_id = entry.get("journeyId")
    journey = journeys.get(journey_id) if isinstance(journey_id, str) else None
    status = None
    if journey is None:
        errors.append(f"{label} cites journey '{journey_id}', which is not in reference.json.")
    else:
        status = journey.get("status")
        if not isinstance(status, str) or status not in {"observed", "partial", "inferred"}:
            errors.append(f"{label} selected a journey with an invalid status.")
            status = None
        elif status in {"partial", "inferred"} and not is_text_list(entry.get("assumptions")):
            errors.append(f"{label} adapts a {status} journey and must record an assumption.")

    flow = flows.get(flow_id) if isinstance(flow_id, str) else None
    if flow is None:
        if is_kebab(flow_id):
            errors.append(f"{label}: flow.json declares no flow with that id.")
        return errors

    if flow.get("task") != entry.get("task"):
        errors.append(f"{label}.task does not match the same field in flow.json.")
    if "hypothesis" in entry and flow.get("hypothesis") != entry["hypothesis"]:
        errors.append(f"{label}.hypothesis does not match the same field in flow.json.")

    # The prototype's starting point is a claim about the real site. If the flow
    # says it was observed, the evidence has to be in the research.
    flow_entry = flow.get("entry") if isinstance(flow.get("entry"), dict) else {}
    if flow_entry.get("basis") == "observed":
        cited = flow_entry.get("evidence")
        if not is_text_list(cited):
            errors.append(f"{label}: the flow's entry claims to be observed but cites no evidence ids.")
        else:
            for one in cited:
                if one not in evidence_kinds:
                    errors.append(f"{label}: the flow's entry cites evidence '{one}', which reference.json "
                                  "does not record.")
        journey_entry = journey.get("entry") if isinstance(journey, dict) else None
        if isinstance(journey_entry, dict) and journey_entry.get("status") != "observed":
            errors.append(
                f"{label}: the flow's entry claims to be observed, but the journey's own entry point is "
                f"'{journey_entry.get('status')}'. The prototype cannot be more certain than the research."
            )
    if status == "inferred" and flow_entry.get("basis") == "observed":
        errors.append(
            f"{label}: the journey is inferred, so the flow's entry cannot claim basis 'observed'."
        )

    # An assumption that stops here is one the room never sees. A flow derived
    # from incomplete research has to carry at least one unsettled review point.
    if status in {"partial", "inferred"}:
        review = flow.get("review") if isinstance(flow.get("review"), list) else []
        unsettled = [
            item for item in review
            if isinstance(item, dict) and item.get("status") in UNSETTLED
        ]
        if not unsettled:
            errors.append(
                f"{label} adapts a {status} journey, but every review point on the flow is settled. Carry the "
                "gaps into the flow's review ledger and facilitator walkthrough, not only this file."
            )
    return errors


def validate(
    adaptation: object,
    reference: object,
    flow_spec: object,
    *,
    reference_path: Path | str | None = None,
    base_dir: Path | str | None = None,
    artifact_dir_name: str | None = None,
) -> list[str]:
    if not isinstance(adaptation, dict) or not isinstance(reference, dict) or not isinstance(flow_spec, dict):
        return ["All three inputs must be JSON objects."]

    errors: list[str] = []
    if type(adaptation.get("version")) is not int or adaptation.get("version") != ADAPTATION_VERSION:
        errors.append(f"adaptation.version must equal {ADAPTATION_VERSION}.")
    if not is_kebab(adaptation.get("id")):
        errors.append("adaptation.id must be kebab-case.")
    elif artifact_dir_name is not None and adaptation.get("id") != artifact_dir_name:
        errors.append(
            f"adaptation.id must match its prototype directory {artifact_dir_name!r}."
        )

    link = adaptation.get("reference")
    if not isinstance(link, dict):
        errors.append("adaptation.reference must be an object.")
    else:
        if link.get("id") != reference.get("id"):
            errors.append("adaptation.reference.id does not match reference.json.")
        if not isinstance(link.get("path"), str) or not link["path"].strip():
            errors.append("adaptation.reference.path is required.")
        else:
            resolved, path_errors = _resolve_declared_reference(
                link["path"], reference_path, base_dir
            )
            errors.extend(path_errors)
            if resolved is not None:
                on_disk, read_errors = _load_reference_file(resolved)
                errors.extend(read_errors)
                if isinstance(on_disk, dict):
                    if on_disk.get("id") != reference.get("id"):
                        errors.append(
                            "adaptation.reference.path resolves to a different reference JSON than the "
                            "one supplied to the validator."
                        )
                    # When the CLI supplies an explicit reference path, the
                    # object loaded from that path is the source of truth. A
                    # stale or substituted object must not validate by accident.
                    if reference_path is not None and on_disk != reference:
                        errors.append(
                            "adaptation.reference.path does not match the reference JSON supplied to the "
                            "validator."
                        )
                elif on_disk is not None:
                    errors.append("adaptation.reference.path must point to a JSON object.")

    journeys: dict[str, dict] = {}
    raw_journeys = reference.get("journeys")
    if not isinstance(raw_journeys, list):
        errors.append("reference.journeys must be an array.")
        raw_journeys = []
    for index, journey in enumerate(raw_journeys):
        if not isinstance(journey, dict):
            errors.append(f"reference.journeys[{index}] must be an object.")
            continue
        journey_id = journey.get("id")
        if not isinstance(journey_id, str):
            errors.append(f"reference.journeys[{index}].id must be a string.")
            continue
        journeys[journey_id] = journey

    flows: dict[str, dict] = {}
    raw_flows = flow_spec.get("flows")
    if not isinstance(raw_flows, list):
        errors.append("flow.json.flows must be an array.")
        raw_flows = []
    for index, flow in enumerate(raw_flows):
        if not isinstance(flow, dict):
            errors.append(f"flow.json.flows[{index}] must be an object.")
            continue
        flow_id = flow.get("id")
        if not isinstance(flow_id, str):
            errors.append(f"flow.json.flows[{index}].id must be a string.")
            continue
        flows[flow_id] = flow

    evidence_kinds: dict[str, str] = {}
    raw_evidence = reference.get("evidence")
    if not isinstance(raw_evidence, list):
        errors.append("reference.evidence must be an array.")
        raw_evidence = []
    for index, item in enumerate(raw_evidence):
        if not isinstance(item, dict):
            errors.append(f"reference.evidence[{index}] must be an object.")
            continue
        evidence_id = item.get("id")
        if not isinstance(evidence_id, str):
            errors.append(f"reference.evidence[{index}].id must be a string.")
            continue
        evidence_kinds[evidence_id] = item.get("kind")

    entries = adaptation.get("adaptations")
    if not isinstance(entries, list) or not entries:
        errors.append("adaptation.adaptations needs one entry per derived flow.")
        return errors

    seen: set[str] = set()
    for index, entry in enumerate(entries):
        errors.extend(validate_entry(entry, index, journeys, flows, evidence_kinds))
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
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: Cannot read JSON input: {exc}")
        return 1
    errors = validate(
        adaptation,
        reference,
        flow_spec,
        reference_path=Path(argv[2]),
        base_dir=_repository_root(),
        artifact_dir_name=Path(argv[1]).resolve().parent.name,
    )
    for message in errors:
        print(f"ERROR: {message}")
    if errors:
        return 1
    count = len(adaptation.get("adaptations", []))
    print(f"OK: {count} flow(s) linked to documented website journeys.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
