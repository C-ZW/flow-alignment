#!/usr/bin/env python3
"""Validate the source-of-truth JSON for website flow research."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse


ID_PATTERN = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(ID_PATTERN.fullmatch(value))


def valid_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def valid_timestamp(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate(data: object, base_dir: Path | None = None) -> list[str]:
    """Validate a reference document. base_dir resolves screenshot paths."""
    if not isinstance(data, dict):
        return ["Reference must be a JSON object."]
    errors: list[str] = []
    if data.get("version") != 1:
        errors.append("version must equal 1.")
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
    if not isinstance(coverage, dict) or not isinstance(coverage.get("viewports"), list) or not coverage["viewports"]:
        errors.append("coverage must include at least one viewport.")

    evidence = data.get("evidence")
    evidence_ids: set[str] = set()
    if not isinstance(evidence, list) or not evidence:
        errors.append("At least one evidence record is required.")
    else:
        for item in evidence:
            if not isinstance(item, dict) or not valid_id(item.get("id")):
                errors.append("Each evidence record needs a kebab-case id.")
                continue
            if item["id"] in evidence_ids:
                errors.append(f"Duplicate evidence id: {item['id']}.")
            evidence_ids.add(item["id"])
            for key in ("kind", "method"):
                if not isinstance(item.get(key), str) or not item[key].strip():
                    errors.append(f"Evidence {item['id']} is missing {key}.")
            if not valid_url(item.get("url")):
                errors.append(f"Evidence {item['id']} has an invalid URL.")
            if not valid_timestamp(item.get("capturedAt")):
                errors.append(f"Evidence {item['id']} has an invalid capturedAt timestamp.")
            if item.get("kind") == "screenshot":
                relative = item.get("path")
                if not isinstance(relative, str) or not relative.strip():
                    errors.append(f"Screenshot evidence {item['id']} needs a path.")
                elif base_dir is not None and not (base_dir / relative).is_file():
                    errors.append(
                        f"Screenshot evidence {item['id']} points at a missing file: {relative}. "
                        "Record only screenshots that were actually captured."
                    )

    observations = data.get("observations")
    if not isinstance(observations, list) or not observations:
        errors.append("At least one observation is required.")
    else:
        for observation in observations:
            if not isinstance(observation, dict) or not valid_id(observation.get("id")):
                errors.append("Each observation needs a kebab-case id.")
                continue
            if observation.get("kind") not in {"observed", "inferred"}:
                errors.append(f"Observation {observation['id']} must be observed or inferred.")
            if not isinstance(observation.get("summary"), str) or not observation["summary"].strip():
                errors.append(f"Observation {observation['id']} is missing summary.")
            for evidence_id in observation.get("evidence", []):
                if evidence_id not in evidence_ids:
                    errors.append(f"Observation {observation['id']} cites unknown evidence {evidence_id}.")

    journeys = data.get("journeys")
    if not isinstance(journeys, list) or not journeys:
        errors.append("At least one journey is required.")
    else:
        for journey in journeys:
            if not isinstance(journey, dict) or not valid_id(journey.get("id")):
                errors.append("Each journey needs a kebab-case id.")
                continue
            if journey.get("status") not in {"observed", "partial", "inferred"}:
                errors.append(f"Journey {journey['id']} needs a valid status.")
            if not isinstance(journey.get("steps"), list) or len(journey["steps"]) < 2:
                errors.append(f"Journey {journey['id']} needs at least two steps.")
            if not journey.get("evidence"):
                errors.append(f"Journey {journey['id']} needs evidence.")
            for evidence_id in journey.get("evidence", []):
                if evidence_id not in evidence_ids:
                    errors.append(f"Journey {journey['id']} cites unknown evidence {evidence_id}.")

    if not isinstance(data.get("limitations"), list) or not any(isinstance(item, str) and item.strip() for item in data["limitations"]):
        errors.append("limitations must contain at least one non-empty item.")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: validate_reference.py <reference.json>", file=sys.stderr)
        return 2
    path = Path(sys.argv[1])
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
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
