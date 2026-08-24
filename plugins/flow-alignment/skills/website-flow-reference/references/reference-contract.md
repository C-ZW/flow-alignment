# Website Reference Contract (`reference.json`, version 1)

`reference.json` is the evidence index for a researched website flow. Keep
narrative detail in the companion Markdown files; keep ids and facts here.

A journey is a chain of claims. Each link — the entry point and every step —
carries its own evidence, because one screenshot of a landing page is evidence
that the landing page exists, not evidence that its button goes anywhere.

```json
{
  "version": 1,
  "id": "example-checkout",
  "source": {
    "url": "https://example.com/path",
    "canonicalUrl": "https://example.com/path",
    "capturedAt": "2026-08-21T10:00:00+08:00"
  },
  "coverage": {
    "viewports": [{ "name": "desktop", "width": 1440, "height": 1000 }],
    "sweeps": ["initial-render", "scroll", "click", "hover", "responsive"]
  },
  "evidence": [
    { "id": "ev-page", "kind": "rendered-page", "method": "browser", "url": "https://example.com/path", "capturedAt": "2026-08-21T10:00:00+08:00", "viewport": "desktop" },
    { "id": "ev-shot-desktop", "kind": "screenshot", "method": "browser", "path": "screenshots/desktop.png", "url": "https://example.com/path", "capturedAt": "2026-08-21T10:00:00+08:00", "viewport": "desktop" }
  ],
  "observations": [
    { "id": "obs-hero", "kind": "observed", "summary": "The page has a hero with a primary call to action.", "evidence": ["ev-page"] }
  ],
  "journeys": [
    {
      "id": "journey-start",
      "title": "Start a task",
      "entry": {
        "description": "The hero call to action on the landing page.",
        "status": "observed",
        "evidence": ["ev-shot-desktop"]
      },
      "steps": [
        {
          "action": "Open the landing page",
          "destination": "Landing page",
          "outcome": "The hero and its primary button render above the fold.",
          "status": "observed",
          "evidence": ["ev-shot-desktop"]
        },
        {
          "action": "Press the primary button",
          "destination": "Sign-up form",
          "outcome": "A three-field form appears; the submit destination was not reached.",
          "status": "partial",
          "evidence": ["ev-page"]
        }
      ],
      "outcome": "The form was reached. What happens after submitting was not observed.",
      "status": "partial"
    }
  ],
  "limitations": ["Submitting the form would have created an account, so it was not attempted."]
}
```

## Rules

- Use `version: 1` and a unique kebab-case `id`.
- `coverage.viewports` is a non-empty array of objects. Every viewport has a
  unique non-empty `name`, a positive integer `width`, and a positive integer
  `height`. Evidence may name only one of these declared viewports.
- Include at least one evidence record and one observation citing valid ids.
- Evidence `kind` is one of `screenshot`, `interaction`, `rendered-page`, or
  `dom-inspection`. Custom labels are invalid because an arbitrary
  non-screenshot label must not satisfy the interaction-evidence rule.
- Observation `kind` is `observed` or `inferred`; every observation must carry a
  non-empty `evidence` array of known ids. An inferred observation is a
  hypothesis grounded in the cited records, not an uncited guess.
- `limitations` needs at least one non-empty item, even when coverage is broad.
- Evidence with `kind: "screenshot"` needs a `path` relative to `reference.json`,
  and the validator fails when that file is missing or escapes the reference
  directory. Never create an evidence id for a capture that did not happen.
- Screenshot evidence remains third-party research material unless its rights
  say otherwise. A project license does not silently relicense it; exclude it
  from redistribution or carry an explicit provenance and rights notice.

### Journeys

- Required per journey: `id`, `title`, `entry`, `steps`, `outcome`, `status`.
- `entry` declares `description`, `status`, and `evidence`. This is the field the
  prototype's own entry point is derived from, so it is a claim in its own right.
- `entry.evidence` is always required as an array of known ids. An `observed`
  or `partial` entry must cite at least one record; an `inferred` entry may use
  an explicit empty array only when the entry is wholly unobserved and the gap
  is stated in the outcome or limitations.
- `steps` holds at least two objects, each with:
  - `action` — what was done.
  - `destination` — where it led.
  - `outcome` — what was visible there. Say plainly when it was not reached.
  - `status` — `observed`, `partial`, or `inferred`.
  - `evidence` — the ids backing this link.
- `step.evidence` is always required as an array of known ids. A step marked
  `observed` or `partial` must cite at least one record. An `inferred` step may
  use an explicit empty array only when its outcome says what was not observed;
  this keeps an unsupported destination from being presented as fact while
  preserving a documented research gap.
- When an `observed` or `partial` step's `action` claims an interaction or
  navigation (for example click, open, type, submit, select, search, or
  navigate), its citations must include at least one non-screenshot evidence
  record such as `interaction`, `rendered-page`, or `dom-inspection`. A
  screenshot can establish that a control or destination is visible, but cannot
  establish that the action caused the destination. Passive actions such as
  inspect, read, or compare may rely on screenshots alone. An `inferred` step
  with no direct evidence remains valid when its outcome documents the gap.
- Seeing a control is not seeing where it goes: the entry and every step cite
  their own records rather than borrowing the journey's.
- **A journey may only claim `status: "observed"` when its entry and every one of
  its steps are `observed`.** Otherwise it is `partial` — which is a perfectly
  good thing to hand off, as long as it says so.

## Handoff

`reference.json` is the input to `flow-alignment-prototype`. Anything a journey
marks `partial` or `inferred` becomes an assumption the prototype has to carry in
its review ledger, not a detail that stops at `adaptation.json`. See
[the website adaptation contract](../../flow-alignment-prototype/references/website-adaptation-contract.md).

### Layout evidence for visual-reference handoff

When the requested prototype should retain the source's layout structure, the
research must make that structure observable rather than leaving a builder to
guess from one landing-page screenshot. Capture against a claim-to-evidence
plan, not a page-count target.

- Capture the entry and every selected journey state at a shared desktop
  viewport. Capture a narrow entry state when responsive structure is in scope.
- Add observations for the product shell orientation, visual section order and
  relative proportions, repeated-component density, and observed responsive
  reflow. Each observation cites the screenshot evidence that shows it.
- Do not infer a destination layout from entry-page evidence. Missing state or
  breakpoint coverage belongs in `limitations` and later in the adaptation's
  assumptions.
- Do not retain viewport and full-page duplicates unless each supports a
  different recorded layout claim. Do not capture every state at every viewport
  by default; narrow destination evidence is needed only when responsive
  structure or the action graph is part of the handoff.

These observations do not claim visual parity. They give the downstream skill
enough evidence to reproduce the source's wireframe silhouette with neutral
placeholders instead of falling back to a generic application shell.
