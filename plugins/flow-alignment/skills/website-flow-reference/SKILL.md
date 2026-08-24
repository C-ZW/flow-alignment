---
name: website-flow-reference
description: Research a public website as an evidence-backed reference before adapting one of its flows. Use when given a URL and you need its information architecture, observable user journeys, screenshots, layout structure, and explicit limitations captured in an auditable artifact. Triggers on "analyse this site", "benchmark this website", "capture the IA", "how does this site handle this flow", "reference this URL for a prototype".
---

# Website Flow Reference

Research a URL before recreating or adapting anything from it. The output is an
audit trail, not a copy: every claim carries an evidence id, and anything not
observed is labelled as inferred or listed as a limitation.

## Required outputs

Write only under `references/<site-key>/`:

| File | Purpose |
| --- | --- |
| `reference.json` | Source metadata, evidence records, observations, journeys, limitations |
| `ia.md` | Page topology and information architecture in visual order |
| `journeys.md` | Journeys with evidence and adaptation opportunity |
| `evidence.md` | Capture log, viewport coverage, unresolved unknowns |
| `screenshots/` | Only screenshots that were actually captured |

Derive `<site-key>` from the host and pathname; keep it readable and
collision-safe. Never write generated artifacts under `.claude/skills/`.

## Workflow

1. **Load the contract before writing JSON.** Read
   [the reference contract](references/reference-contract.md) before creating
   `reference.json`. Do not infer field names from prose. If the caller
   explicitly forbids loading supporting files, use the minimum contract
   checklist below and treat the validator as the
   final authority.
2. **Check access.** Confirm the URL is reachable and appropriate to research.
   Respect terms and robots guidance. Never bypass authentication, paywalls,
   CAPTCHAs, or access controls.
3. **Plan claims before captures.** Record the canonical URL, site key, output
   folder, viewports, and the one to three journeys worth studying. Decide the
   downstream intent before opening additional pages: evidence-only research, a
   generic flow wireframe, or a wireframe that should retain observed layout
   structure. Make a small claim-to-evidence table with one row for the entry,
   every selected journey link, and every layout statement the downstream work
   will preserve. Name the browser action or screenshot that can prove each row.
4. **Capture the smallest sufficient evidence set.** At minimum inspect the
   initial desktop render, then walk the selected journey in one browser session
   per required viewport. Reuse one capture for every claim it genuinely proves.
   - Interaction records, rendered destinations, or DOM inspection prove route
     causality. Do not add a screenshot solely to duplicate that proof.
   - In `wireframe` or evidence-only work, capture a state only when its visible
     content or structure supports a claim. A screenshot of every click is not a
     completion requirement.
   - For a reference-shaped wireframe, capture the entry and each
     layout-distinct selected journey state at one shared desktop viewport.
     Capture a narrow state only when its responsive structure will be preserved
     or its action graph differs.
   - Do not save both viewport and full-page versions of the same state unless
     the off-screen structure supports a separate recorded claim.
   - Sweep hover, scroll, and additional breakpoints only when the selected
     journey or an observed control makes them relevant.
   - A screenshot of the entry page does not support the layout of a destination
     page. Missing state or breakpoint coverage remains a limitation; do not fill
     it from memory.
   Stop capturing when every row in the claim-to-evidence table has valid
   evidence. More files after that point add review cost without strengthening
   the handoff.
5. **Record every observation** in `reference.json` with an evidence id. Keep
   `observed` facts and `inferred` hypotheses in separate records, and list every
   capture limitation.
6. **Write IA from the rendered page**, in visual order, marking each section's
   interaction model: static, click, hover, scroll, time, or unknown.
   For a reference-shaped wireframe, also state the observable layout decisions
   that survive abstraction: shell orientation, section order and relative
   proportions, repeated-component density, and responsive reflow. Cite the
   screenshot evidence for each statement.
7. **Record journeys link by link.** Every step declares what was done, where it
   led, what was visible there, and the evidence for that one link. A journey may
   call itself `observed` only when its entry point and every step are observed;
   if the destination was blocked, mark that step `partial` and say so in its
   outcome rather than inventing one. Handing over a `partial` journey is fine.
   Handing over a `partial` journey labelled `observed` is not.
8. **Name the adaptation opportunity**: what to preserve (the decision, its
   context, the wording that carries meaning) and what to abstract (branding,
   decorative media, unrelated features).
9. **Validate and fix.** Run the validator before writing the narrative files so
   schema errors are corrected while the evidence model is still in working
   context; run it again after every material JSON change.

   ```bash
   python3 .claude/skills/website-flow-reference/scripts/validate_reference.py references/<site-key>/reference.json
   ```

## Minimum contract checklist

This is a guardrail, not a second copy of the full contract. Use the exact field
names below; read the contract for conditional rules and examples.

- Root: `version: 1`, kebab-case `id`, `source`, `coverage`, non-empty
  `evidence`, non-empty `observations`, `journeys`, and non-empty `limitations`.
- `source`: `url`, `canonicalUrl`, `capturedAt`.
- Evidence: `id`, `kind`, `method`, `url`, `capturedAt`; `kind` is
  `screenshot`, `interaction`, `rendered-page`, or `dom-inspection`. Screenshot
  evidence also needs a relative `path` that stays inside the reference directory. When
  present, `viewport` is the viewport **name** from `coverage.viewports`, not a
  width/height object.
- Viewport: each item in `coverage.viewports` is an object with a unique
  non-empty `name`, positive integer `width`, and positive integer `height`.
- Observation: `id`, `kind` (`observed` or `inferred`), `summary`, and a
  non-empty `evidence` array of known ids.
- Journey: `id`, `title`, `entry`, at least two `steps`, `outcome`, `status`.
- Entry: `description`, `status`, `evidence`.
- Step: `action`, `destination`, `outcome`, `status`, `evidence`.
- Entry, step, and journey status: `observed`, `partial`, or `inferred`. A journey
  is `observed` only when its entry and every step are observed.

Do not substitute near-synonyms such as `type` for `kind`, `claim` for `summary`,
`name` for `title`, `label` for `description`, or `visible` for `outcome`; those
fields do not satisfy the contract.

## Evidence rules

- Every screenshot, DOM inspection, interaction, or source document gets a stable
  evidence id, a `url`, an ISO 8601 `capturedAt`, a capture method, and a viewport
  where applicable.
- Screenshot evidence needs a `path`, and the validator checks the file exists.
  Never record evidence for a capture that did not happen.
- Treat appearance and behaviour as separate observations. Seeing a button is not
  seeing what it does — which is why each journey step carries its own evidence
  rather than borrowing the journey's.
- For an `observed` or `partial` step whose action claims an interaction or
  navigation (click, open, type, submit, select, search, navigate, and similar),
  cite at least one non-screenshot record such as an interaction, rendered-page,
  or DOM-inspection capture. A screenshot-only citation proves visibility, not
  that the action caused the destination. Passive inspect/read/compare steps may
  use screenshots alone. An inferred step may use `evidence: []` only when its
  outcome and limitations state the missing observation.
- The journey's `entry` is a claim too. The prototype built from this research
  starts where this field says people start, so its `evidence` array is always
  required. `observed` and `partial` entries/steps need at least one citation;
  an `inferred` entry or step may use an explicit empty array only when the
  missing direct capture is stated in its outcome or the reference limitations.
- Never write "pixel-perfect", "1:1", or "fully extracted" unless the evidence
  supports that exact claim.
- Do not download or reuse third-party logos, images, copy, or protected assets
  to build a prototype. Use placeholders unless reuse is authorised.
- Treat source screenshots as research records, not automatically
  project-licensed assets. Before publishing or redistributing a reference
  directory, either exclude its captures or document their provenance and
  applicable rights—including explicit site-owner authorization when provided—
  in a notice outside the skill. Never imply that the repository's code license
  alone covers them.

## Handoff

`reference.json` is the input to `flow-alignment-prototype`. A prototype walks
one selected journey; it does not reproduce the source website.

Treat validated research as an execution boundary. When the runner supports a
fresh session or delegated agent, finish this skill first, then start the
prototype skill with `reference.json`, the selected evidence files, and its own
instructions rather than carrying raw browser history and unrelated captures
forward. In a single session, release browser state and keep only the selected
journey and cited evidence in context. This reduces latency without weakening
the evidence handoff and works with any agent runner that can sequence two jobs.

Anything marked `partial` or `inferred` here becomes an open or assumed entry in
that prototype's review ledger. An assumption that stops at `adaptation.json` is
an assumption nobody in the room will ever see, so the adaptation validator
rejects a derived flow whose ledger has settled everything.

When the requested prototype should look structurally like the source, hand off
the screenshot ids and the layout observations above. This supports
`visual-reference` mode: it preserves an observed silhouette and information
density, not branding or pixel values. If screenshots do not cover a journey
state, say so; the prototype must mark that screen's layout as adapted rather
than observed.

## Resources

- [Reference contract](references/reference-contract.md) — `reference.json` shape and rules
- `scripts/validate_reference.py` — evidence and journey validator
