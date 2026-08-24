#!/usr/bin/env python3
"""Walk a generated flow artifact in a real browser and audit runtime mechanics.

The script is runner-neutral. It uses Playwright when available, opens the
artifact from disk, and never changes it. Human review is still required for
product meaning, visual resemblance, and omitted journeys.
"""

from __future__ import annotations

import argparse
import json
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_VIEWPORTS = (("desktop", 1440, 1000), ("mobile", 390, 844))


@dataclass(frozen=True)
class Viewport:
    name: str
    width: int
    height: int


def parse_viewport(value: str) -> Viewport:
    """Parse NAME=WIDTHxHEIGHT or WIDTHxHEIGHT."""
    name, separator, dimensions = value.partition("=")
    if not separator:
        dimensions = name
        name = dimensions
    width_text, separator, height_text = dimensions.lower().partition("x")
    if not separator:
        raise argparse.ArgumentTypeError("viewport must be NAME=WIDTHxHEIGHT or WIDTHxHEIGHT")
    try:
        width = int(width_text)
        height = int(height_text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("viewport width and height must be integers") from exc
    if width < 240 or height < 240:
        raise argparse.ArgumentTypeError("viewport width and height must be at least 240")
    return Viewport(name=name, width=width, height=height)


def shortest_path(flow: dict[str, Any], target: str) -> list[str] | None:
    """Return a shortest state-id path from the declared entry to target."""
    states = {state["id"]: state for state in flow["states"]}
    entry = flow["entry"]["state"]
    queue: deque[list[str]] = deque([[entry]])
    visited = {entry}
    while queue:
        path = queue.popleft()
        current = path[-1]
        if current == target:
            return path
        for destination in states[current].get("transitions", []):
            if destination not in visited:
                visited.add(destination)
                queue.append([*path, destination])
    return None


def transition_cases(flow: dict[str, Any]) -> list[tuple[str, str, list[str]]]:
    """Plan one entry-led browser walk for every declared transition edge."""
    cases = []
    for state in flow["states"]:
        path = shortest_path(flow, state["id"])
        if path is None:
            continue
        for destination in state.get("transitions", []):
            cases.append((state["id"], destination, path))
    return cases


AUDIT_JAVASCRIPT = r"""
({ expectedState }) => {
  const failures = [];
  const warnings = [];
  const tolerance = 2;
  const close = (a, b) => Math.abs(a - b) <= tolerance;
  const visible = (element) => {
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return style.display !== 'none' && style.visibility !== 'hidden'
      && rect.width > 0 && rect.height > 0
      && rect.left >= -tolerance && rect.right <= innerWidth + tolerance
      && rect.top >= -tolerance && rect.bottom <= innerHeight + tolerance;
  };
  const describe = (element) => element.dataset.goto || element.dataset.nav
    || element.textContent.trim().replace(/\s+/g, ' ').slice(0, 80) || element.tagName;

  const engineReady = typeof FlowPrototype !== 'undefined';
  if (!engineReady) failures.push('FlowPrototype did not initialize.');
  if (engineReady && FlowPrototype.stateId !== expectedState) {
    failures.push(`Expected state ${expectedState}, got ${FlowPrototype.stateId}.`);
  }
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + tolerance) {
    failures.push(`Horizontal overflow: ${document.documentElement.scrollWidth}px content in ${document.documentElement.clientWidth}px viewport.`);
  }

  const actions = engineReady
    ? [...FlowPrototype.liveProductActions, ...FlowPrototype.liveNavigation]
    : [];
  const actionStatus = (action) => {
    const isVisible = visible(action);
    const enabled = !(action.disabled || action.getAttribute('aria-disabled') === 'true'
      || getComputedStyle(action).pointerEvents === 'none');
    const rect = action.getBoundingClientRect();
    const x = Math.max(0, Math.min(innerWidth - 1, rect.left + rect.width / 2));
    const y = Math.max(0, Math.min(innerHeight - 1, rect.top + rect.height / 2));
    const hit = document.elementFromPoint(x, y);
    const uncovered = !isVisible || !hit || hit === action || action.contains(hit);
    return { isVisible, enabled, uncovered };
  };
  for (const action of actions) {
    const label = describe(action);
    const status = actionStatus(action);
    if (!status.enabled) {
      failures.push(`Live control is disabled or blocked: ${label}.`);
    }
    if (status.isVisible && !status.uncovered) {
      failures.push(`Live control is covered at its center: ${label}.`);
    }
  }
  if (engineReady) {
    const state = FlowPrototype.state();
    for (const destination of state.transitions || []) {
      const candidates = actions.filter((action) => action.dataset.goto === destination
        || (action.dataset.nav && (state.navTargets || {})[action.dataset.nav] === destination));
      const reachable = candidates.some((action) => {
        const status = actionStatus(action);
        return status.isVisible && status.enabled && status.uncovered;
      });
      if (!reachable) {
        failures.push(`No visible, enabled control reaches declared transition ${state.id} -> ${destination}.`);
      }
    }
  }

  const mask = document.getElementById('interaction-mask');
  const targets = engineReady
    ? FlowPrototype.spotlightTargets.filter((target) => target && target.isConnected)
    : [];
  if (!mask || mask.hidden) failures.push('Interaction mask is missing or hidden.');
  const rings = mask
    ? Array.from(mask.querySelectorAll('.spotlight-ring')).filter((ring) => {
        const style = getComputedStyle(ring);
        return !ring.hidden && style.display !== 'none' && style.visibility !== 'hidden';
      })
    : [];
  const shellRect = document.getElementById('app-shell')?.getBoundingClientRect();
  const shellBounds = shellRect ? {
    left: Math.max(0, shellRect.left), top: Math.max(0, shellRect.top),
    right: Math.min(innerWidth, shellRect.right), bottom: Math.min(innerHeight, shellRect.bottom)
  } : null;
  const ringExpected = !(document.body.dataset.scope === 'shell'
    && document.body.dataset.focusSource === 'product');
  if (ringExpected && rings.length !== targets.length) {
    failures.push(`Expected ${targets.length} visible spotlight ring(s), found ${rings.length}.`);
  }
  if (ringExpected && shellBounds) {
    targets.forEach((target, index) => {
      const targetRect = target.getBoundingClientRect();
      const padding = target === FlowPrototype.viewport ? 0 : 10;
      const expected = {
        left: Math.min(shellBounds.right, Math.max(shellBounds.left, targetRect.left - padding)),
        top: Math.min(shellBounds.bottom, Math.max(shellBounds.top, targetRect.top - padding)),
        right: Math.max(shellBounds.left, Math.min(shellBounds.right, targetRect.right + padding)),
        bottom: Math.max(shellBounds.top, Math.min(shellBounds.bottom, targetRect.bottom + padding))
      };
      const ring = rings[index];
      if (!ring) return;
      const actual = ring.getBoundingClientRect();
      if (![['left', actual.left], ['top', actual.top], ['right', actual.right], ['bottom', actual.bottom]]
          .every(([key, value]) => close(value, expected[key]))) {
        failures.push(`Spotlight ring ${index + 1} does not track its target within ${tolerance}px.`);
      }
      const area = Math.max(0, expected.right - expected.left) * Math.max(0, expected.bottom - expected.top);
      const shellArea = Math.max(1, (shellBounds.right - shellBounds.left) * (shellBounds.bottom - shellBounds.top));
      if (target !== FlowPrototype.viewport && area / shellArea > 0.8) {
        warnings.push(`Spotlight ${index + 1} covers more than 80% of the visible product shell; check that its focus is specific.`);
      }
    });
  }
  return { failures, warnings };
}
"""


class RuntimeAudit:
    def __init__(self, page: Any, viewport: Viewport):
        self.page = page
        self.viewport = viewport
        self.failures: list[str] = []
        self.warnings: list[str] = []
        self.checks = 0

    def wait_for_state(self, state_id: str) -> None:
        self.page.wait_for_function(
            "state => typeof FlowPrototype !== 'undefined' && FlowPrototype.stateId === state", arg=state_id
        )
        self.page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))"
        )

    def inspect(self, flow_id: str, state_id: str, context: str) -> None:
        result = self.page.evaluate(AUDIT_JAVASCRIPT, {"expectedState": state_id})
        self.checks += 1
        prefix = f"{self.viewport.name}/{flow_id}/{state_id} [{context}]"
        self.failures.extend(f"{prefix}: {message}" for message in result["failures"])
        self.warnings.extend(f"{prefix}: {message}" for message in result["warnings"])

    def select_flow(self, flow_id: str) -> None:
        self.page.evaluate("flowId => FlowPrototype.selectFlow(flowId)", flow_id)

    def restart(self, entry: str) -> None:
        self.page.locator("#reset-flow").click()
        self.wait_for_state(entry)

    def click_transition(self, source: str, destination: str) -> None:
        if self.page.evaluate("FlowPrototype.stateId") != source:
            raise RuntimeError(f"Expected {source} before clicking to {destination}")
        candidates = self.page.locator(
            f'#product-viewport [data-goto="{destination}"], #app-shell [data-nav]'
        ).element_handles()
        clicked = False
        for candidate in candidates:
            usable = candidate.evaluate(
                """(control, destination) => {
                  const state = FlowPrototype.state();
                  const routesThere = control.dataset.goto === destination
                    || (control.dataset.nav
                      && (state.navTargets || {})[control.dataset.nav] === destination);
                  const live = FlowPrototype.liveProductActions.includes(control)
                    || FlowPrototype.liveNavigation.includes(control);
                  const rect = control.getBoundingClientRect();
                  return routesThere && live && rect.width > 0 && rect.height > 0
                    && rect.left >= 0 && rect.right <= innerWidth
                    && rect.top >= 0 && rect.bottom <= innerHeight;
                }""",
                destination,
            )
            if usable:
                candidate.click()
                clicked = True
                break
        if not clicked:
            raise RuntimeError(f"No live product control routes {source} -> {destination}")
        self.wait_for_state(destination)

    def audit_flow(self, flow: dict[str, Any]) -> None:
        flow_id = flow["id"]
        entry = flow["entry"]["state"]
        self.select_flow(flow_id)
        self.wait_for_state(entry)
        self.inspect(flow_id, entry, "entry")
        for state in flow["states"]:
            state_id = state["id"]
            self.page.locator(f'[data-jump="{state_id}"]').click()
            self.wait_for_state(state_id)
            self.inspect(flow_id, state_id, "route jump")
            self.restart(entry)
            if state_id != entry:
                self.inspect(flow_id, entry, f"restart from {state_id}")
        for source, destination, path in transition_cases(flow):
            self.restart(entry)
            try:
                for path_source, path_destination in zip(path, path[1:]):
                    self.click_transition(path_source, path_destination)
                self.inspect(flow_id, source, f"before {source} -> {destination}")
                self.click_transition(source, destination)
                self.inspect(flow_id, destination, f"after {source} -> {destination}")
            except RuntimeError as exc:
                self.failures.append(f"{self.viewport.name}/{flow_id}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Walk every flow edge and audit masks, actions, jumps, restart, and overflow."
    )
    parser.add_argument("artifact_dir", type=Path, help="prototypes/<flow-name> directory")
    parser.add_argument(
        "--viewport", type=parse_viewport, action="append",
        help="repeatable NAME=WIDTHxHEIGHT; defaults to desktop=1440x1000 and mobile=390x844",
    )
    parser.add_argument("--headed", action="store_true", help="show the browser while auditing")
    parser.add_argument("--report", type=Path, help="optionally write the JSON result to this path")
    args = parser.parse_args()
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: Runtime audit requires the optional Python Playwright package.")
        print("Install it with: python3 -m pip install playwright && python3 -m playwright install chromium")
        return 2

    artifact_dir = args.artifact_dir.resolve()
    try:
        document = json.loads((artifact_dir / "flow.json").read_text(encoding="utf-8"))
        prototype_path = artifact_dir / "prototype.html"
        if not prototype_path.is_file():
            raise FileNotFoundError(f"prototype.html is missing: {prototype_path}")
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError) as exc:
        print(f"ERROR: Cannot load artifact: {exc}")
        return 1
    viewports = args.viewport or [Viewport(*item) for item in DEFAULT_VIEWPORTS]
    started = time.monotonic()
    failures: list[str] = []
    warnings: list[str] = []
    checks = 0
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                for viewport in viewports:
                    context = browser.new_context(viewport={"width": viewport.width, "height": viewport.height})
                    page = context.new_page()
                    page.set_default_timeout(5_000)
                    page_errors: list[str] = []
                    page.on("console", lambda message: page_errors.append(f"console error: {message.text}") if message.type == "error" else None)
                    page.on("pageerror", lambda error: page_errors.append(f"page error: {error}"))
                    page.goto(prototype_path.as_uri(), wait_until="load")
                    page.wait_for_function(
                        "() => typeof FlowPrototype !== 'undefined' && FlowPrototype.stateId"
                    )
                    audit = RuntimeAudit(page, viewport)
                    for flow in document["flows"]:
                        audit.audit_flow(flow)
                    failures.extend(audit.failures)
                    failures.extend(f"{viewport.name}: {message}" for message in page_errors)
                    warnings.extend(audit.warnings)
                    checks += audit.checks
                    context.close()
            finally:
                browser.close()
    except Exception as exc:
        failures.append(f"Browser audit could not complete: {exc}")

    elapsed = round(time.monotonic() - started, 3)
    result = {
        "artifact": str(artifact_dir), "elapsedSeconds": elapsed, "checks": checks,
        "viewports": [viewport.__dict__ for viewport in viewports],
        "failures": failures, "warnings": warnings,
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    for message in warnings:
        print(f"WARNING: {message}")
    for message in failures:
        print(f"ERROR: {message}")
    if failures:
        print(f"Runtime audit failed after {checks} state checks in {elapsed:.3f}s.")
        return 1
    print(f"OK: runtime audit passed {checks} state checks in {elapsed:.3f}s.")
    if warnings:
        print(f"Review {len(warnings)} warning(s) above; runtime mechanics passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
