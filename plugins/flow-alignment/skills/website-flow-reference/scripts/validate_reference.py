#!/usr/bin/env python3
"""Validate the source-of-truth JSON for website flow research.

A journey is a chain of claims, and each link carries its own evidence. One
screenshot of a landing page is evidence that the landing page exists — it is not
evidence that clicking the button goes anywhere. Every step must
declare its own action, destination, outcome, status, and evidence, so a journey
can only call itself observed when every link in it was actually seen.
"""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path, PureWindowsPath
from urllib.parse import urlparse


REFERENCE_VERSION = 1
ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STATUSES = ("observed", "partial", "inferred")
OBSERVATION_KINDS = ("observed", "inferred")
# These verbs describe an action whose result is being claimed, rather than a
# passive inspection of a screen.  A screenshot can show that a control or
# destination exists, but cannot by itself show that the action caused the
# destination.  Keep this list intentionally imperative; verbs such as
# "inspect", "read", and "compare" remain screenshot-friendly observations.
INTERACTION_ACTION_PATTERN = re.compile(
    r"\b(?:click|tap|press|open|type|enter|submit|select|choose|pick|fill|"
    r"search|navigate|go(?:\s+to)?|follow|activate|visit|load|scroll|hover|"
    r"drag|drop|toggle|expand|collapse|close|dismiss|play|pause|upload|"
    r"download|filter|sort|check|uncheck|sign\s+in|log\s+in|watch)\b",
    re.IGNORECASE,
)
EVIDENCE_KINDS = {"screenshot", "interaction", "rendered-page", "dom-inspection"}


def valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def valid_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
    except (UnicodeError, ValueError):
        return False
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError, OverflowError):
        return False
    return True


def validate_evidence_refs(
    cited: object,
    evidence_ids: set[str],
    label: str,
    *,
    required: bool = False,
) -> list[str]:
    """Validate a citation list without trusting its JSON shape.

    ``required`` is used for observations and journey links.  A wholly
    inferred journey link may deliberately use ``[]`` to record that no direct
    capture supports it, but the field still has to be present and an array.
    """
    if cited is None:
        if required:
            return [f"{label}.evidence is required and must be an array of evidence ids."]
        return []
    if not isinstance(cited, list) or not all(isinstance(one, str) for one in cited):
        return [f"{label}.evidence must be an array of evidence ids."]
    return [f"{label} cites unknown evidence {one}." for one in cited if one not in evidence_ids]


def validate_claim_evidence(
    cited: object,
    status: object,
    evidence_ids: set[str],
    label: str,
    *,
    action: object | None = None,
    evidence_kinds: dict[str, object] | None = None,
) -> list[str]:
    """Apply certainty rules to an entry or journey step.

    Observed and partial claims must cite at least one record.  An inferred
    claim must still carry an evidence array, but an empty array is allowed for
    an explicit, wholly unobserved inference (the surrounding outcome or
    limitations must explain that gap).
    """
    errors = validate_evidence_refs(cited, evidence_ids, label, required=True)
    if status in ("observed", "partial") and isinstance(cited, list) and not cited:
        if status == "observed":
            errors.append(
                f"{label} is marked observed but cites no evidence. Seeing a control is not seeing where it goes."
            )
        else:
            errors.append(f"{label} is marked partial but cites no evidence.")
    if (
        status in ("observed", "partial")
        and isinstance(action, str)
        and INTERACTION_ACTION_PATTERN.search(action)
        and isinstance(cited, list)
        and cited
        and evidence_kinds is not None
    ):
        known_kinds = [
            evidence_kinds[evidence_id]
            for evidence_id in cited
            if evidence_id in evidence_kinds
        ]
        has_non_screenshot = any(
            isinstance(kind, str) and bool(kind.strip()) and kind != "screenshot"
            for kind in known_kinds
        )
        if known_kinds and not has_non_screenshot:
            errors.append(
                f"{label} claims an interaction or navigation action but cites only screenshot evidence. "
                "Add at least one non-screenshot evidence record (for example interaction, rendered-page, "
                "or dom-inspection) that supports the action and destination."
            )
    return errors


def validate_viewports(coverage: object) -> tuple[list[str], set[str]]:
    """Validate viewport declarations and return their names for cross-checks."""
    if not isinstance(coverage, dict):
        return ["coverage must include at least one viewport and be an object."], set()

    errors: list[str] = []
    viewports = coverage.get("viewports")
    viewport_ids: set[str] = set()
    if not isinstance(viewports, list) or not viewports:
        errors.append("coverage must include at least one viewport.")
        return errors, viewport_ids

    for index, viewport in enumerate(viewports):
        label = f"coverage.viewports[{index}]"
        if not isinstance(viewport, dict):
            errors.append(f"{label} must be an object with name, width, and height.")
            continue

        name = viewport.get("name")
        if not is_text(name):
            errors.append(f"{label}.name must be a non-empty string.")
        elif name in viewport_ids:
            errors.append(f"Duplicate viewport id: {name}.")
        else:
            viewport_ids.add(name)

        for dimension in ("width", "height"):
            value = viewport.get(dimension)
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                errors.append(f"{label}.{dimension} must be a positive integer.")

    sweeps = coverage.get("sweeps")
    if sweeps is not None and (
        not isinstance(sweeps, list) or not all(is_text(sweep) for sweep in sweeps)
    ):
        errors.append("coverage.sweeps must be an array of non-empty strings when present.")
    return errors, viewport_ids


def validate_screenshot_path(relative: object, label: str, base_dir: Path | None) -> list[str]:
    """Check that a screenshot path is relative and confined to the reference directory."""
    if not is_text(relative):
        return [f"Screenshot evidence {label} needs a path."]

    path_text = relative.strip()
    path = Path(path_text)
    windows_path = PureWindowsPath(path_text)
    if (
        path.is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.drive)
        or ".." in path.parts
        or ".." in windows_path.parts
    ):
        return [f"Screenshot evidence {label} path must be relative to the reference directory."]

    # Resolve both the candidate and root so ../ escapes and symlinks pointing
    # outside the reference directory are rejected before checking existence.
    try:
        root = Path(base_dir) if base_dir is not None else Path.cwd()
        root = root.resolve()
        candidate = (root / path).resolve()
        candidate.relative_to(root)
    except (OSError, RuntimeError, TypeError, ValueError):
        return [
            f"Screenshot evidence {label} path must stay inside the reference directory: {path_text}."
        ]

    if base_dir is not None:
        try:
            exists = candidate.is_file()
        except OSError:
            exists = False
        if not exists:
            return [
                f"Screenshot evidence {label} points at a missing file: {path_text}. "
                "Record only screenshots that were actually captured."
            ]
    return []


def validate_journey_step(
    step: object,
    label: str,
    evidence_ids: set[str],
    evidence_kinds: dict[str, object],
) -> tuple[list[str], str | None]:
    """One link in the chain: what was done, where it led, and whether that was seen."""
    if not isinstance(step, dict):
        return [f"{label} must be an object with action, destination, outcome, status, and evidence."], None

    errors: list[str] = []
    for field in ("action", "destination", "outcome"):
        if not is_text(step.get(field)):
            errors.append(f"{label} is missing {field}.")
    status = step.get("status")
    if status not in STATUSES:
        errors.append(f"{label}.status must be one of: {', '.join(STATUSES)}.")
        status = None
    errors.extend(
        validate_claim_evidence(
            step.get("evidence"),
            status,
            evidence_ids,
            label,
            action=step.get("action"),
            evidence_kinds=evidence_kinds,
        )
    )
    return errors, status


def validate_journey(
    journey: object,
    evidence_ids: set[str],
    evidence_kinds: dict[str, object],
) -> list[str]:
    if not isinstance(journey, dict) or not valid_id(journey.get("id")):
        return ["Each journey needs a kebab-case id."]

    label = f"Journey {journey['id']}"
    errors: list[str] = []
    if not is_text(journey.get("title")):
        errors.append(f"{label} is missing title.")
    if not is_text(journey.get("outcome")):
        errors.append(f"{label} is missing outcome. Say plainly when the destination was not observed.")

    declared = journey.get("status")
    if declared not in STATUSES:
        errors.append(f"{label} needs a status of: {', '.join(STATUSES)}.")

    link_statuses: list[str | None] = []
    entry = journey.get("entry")
    if not isinstance(entry, dict):
        errors.append(
            f"{label} needs an 'entry' object saying where the journey starts, on what evidence. A prototype "
            "derived from this journey has to start somewhere, and that starting point is a claim."
        )
    else:
        if not is_text(entry.get("description")):
            errors.append(f"{label}.entry is missing description.")
        entry_status = entry.get("status")
        if entry_status not in STATUSES:
            errors.append(f"{label}.entry.status must be one of: {', '.join(STATUSES)}.")
            entry_status = None
        errors.extend(validate_claim_evidence(entry.get("evidence"), entry_status, evidence_ids, f"{label}.entry"))
        link_statuses.append(entry_status)

    steps = journey.get("steps")
    if not isinstance(steps, list) or len(steps) < 2:
        errors.append(f"{label} needs at least two steps.")
    else:
        for index, step in enumerate(steps):
            step_errors, status = validate_journey_step(
                step,
                f"{label}.steps[{index}]",
                evidence_ids,
                evidence_kinds,
            )
            errors.extend(step_errors)
            link_statuses.append(status)

    # The whole chain is only as observed as its weakest link.
    if declared == "observed" and link_statuses:
        weak = [status for status in link_statuses if status != "observed"]
        if weak:
            errors.append(
                f"{label} claims status 'observed' but {len(weak)} of its links are not. Set the journey to "
                "'partial' and record what was inferred."
            )
    errors.extend(validate_evidence_refs(journey.get("evidence"), evidence_ids, label))
    return errors


def validate(data: object, base_dir: Path | None = None) -> list[str]:
    """Validate a reference document. base_dir resolves screenshot paths."""
    if not isinstance(data, dict):
        return ["Reference must be a JSON object."]
    errors: list[str] = []
    if type(data.get("version")) is not int or data.get("version") != REFERENCE_VERSION:
        errors.append(f"version must equal {REFERENCE_VERSION}.")
    if not valid_id(data.get("id")):
        errors.append("id must be kebab-case.")

    source = data.get("source")
    if not isinstance(source, dict):
        errors.append("source must be an object.")
    else:
        for key in ("url", "canonicalUrl"):
            if not valid_url(source.get(key)):
                errors.append(f"source.{key} must be an http(s) URL.")
        if not valid_timestamp(source.get("capturedAt")):
            errors.append("source.capturedAt must be ISO 8601.")

    coverage = data.get("coverage")
    viewport_errors, viewport_ids = validate_viewports(coverage)
    errors.extend(viewport_errors)

    evidence = data.get("evidence")
    evidence_ids: set[str] = set()
    evidence_kinds: dict[str, object] = {}
    if not isinstance(evidence, list) or not evidence:
        errors.append("At least one evidence record is required.")
    else:
        for index, item in enumerate(evidence):
            if not isinstance(item, dict) or not valid_id(item.get("id")):
                errors.append(f"Evidence record at index {index} needs a kebab-case id and must be an object.")
                continue
            if item["id"] in evidence_ids:
                errors.append(f"Duplicate evidence id: {item['id']}.")
            evidence_ids.add(item["id"])
            evidence_kinds[item["id"]] = item.get("kind")
            for key in ("kind", "method"):
                if not is_text(item.get(key)):
                    errors.append(f"Evidence {item['id']} is missing {key}.")
            if is_text(item.get("kind")) and item["kind"] not in EVIDENCE_KINDS:
                errors.append(
                    f"Evidence {item['id']} has unsupported kind {item['kind']!r}; "
                    f"use one of: {', '.join(sorted(EVIDENCE_KINDS))}."
                )
            if not valid_url(item.get("url")):
                errors.append(f"Evidence {item['id']} has an invalid URL.")
            if not valid_timestamp(item.get("capturedAt")):
                errors.append(f"Evidence {item['id']} has an invalid capturedAt timestamp.")
            if "viewport" in item and (
                not is_text(item.get("viewport")) or item["viewport"] not in viewport_ids
            ):
                errors.append(
                    f"Evidence {item['id']} has an unknown viewport: {item.get('viewport')!r}. "
                    "Use a name declared in coverage.viewports."
                )
            if item.get("kind") == "screenshot":
                errors.extend(validate_screenshot_path(item.get("path"), item["id"], base_dir))

    observations = data.get("observations")
    if not isinstance(observations, list) or not observations:
        errors.append("At least one observation is required.")
    else:
        observation_ids: set[str] = set()
        for index, observation in enumerate(observations):
            if not isinstance(observation, dict) or not valid_id(observation.get("id")):
                errors.append(f"Observation at index {index} needs a kebab-case id and must be an object.")
                continue
            observation_id = observation["id"]
            if observation_id in observation_ids:
                errors.append(f"Duplicate observation id: {observation_id}.")
            observation_ids.add(observation_id)
            kind = observation.get("kind")
            if kind not in OBSERVATION_KINDS:
                errors.append(f"Observation {observation_id} must be observed or inferred.")
            if not is_text(observation.get("summary")):
                errors.append(f"Observation {observation_id} is missing summary.")
            errors.extend(validate_evidence_refs(
                observation.get("evidence"), evidence_ids, f"Observation {observation_id}", required=True
            ))
            if kind in OBSERVATION_KINDS and isinstance(observation.get("evidence"), list) and not observation["evidence"]:
                errors.append(f"Observation {observation_id} is marked {kind} but cites no evidence.")

    journeys = data.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        errors.append("At least one journey is required.")
    else:
        journey_ids: set[str] = set()
        for index, journey in enumerate(journeys):
            if isinstance(journey, dict) and valid_id(journey.get("id")):
                journey_id = journey["id"]
                if journey_id in journey_ids:
                    errors.append(f"Duplicate journey id: {journey_id}.")
                journey_ids.add(journey_id)
            elif not isinstance(journey, dict):
                errors.append(f"Journey at index {index} must be an object.")
            errors.extend(validate_journey(journey, evidence_ids, evidence_kinds))

    if not isinstance(data.get("limitations"), list) or not any(
        is_text(item) for item in data["limitations"]
    ):
        errors.append("limitations must contain at least one non-empty item.")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_reference.py <reference.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        print(f"ERROR: Cannot read reference JSON: {error}")
        return 1
    errors = validate(data, path.parent)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"OK: {path} is a valid website flow reference.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
