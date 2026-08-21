---
name: website-flow-reference
description: Research a public website as an evidence-backed reference before adapting one of its flows. Use when given a URL and you need its information architecture, observable user journeys, screenshots, and explicit limitations captured in an auditable artifact. Triggers on "analyse this site", "benchmark this website", "capture the IA", "how does <site> handle <flow>", "reference this URL for a prototype".
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

1. **Check access.** Confirm the URL is reachable and appropriate to research.
   Respect terms and robots guidance. Never bypass authentication, paywalls,
   CAPTCHAs, or access controls.
2. **Plan the capture** before capturing: canonical URL, site key, output folder,
   viewports, and the one to three journeys worth studying.
3. **Capture.** At minimum inspect the initial desktop render. When tools allow,
   take full-page desktop and mobile screenshots, then sweep scroll, click,
   hover, and responsive behaviour.
4. **Record every observation** in `reference.json` with an evidence id. Keep
   `observed` facts and `inferred` hypotheses in separate records, and list every
   capture limitation.
5. **Write IA from the rendered page**, in visual order, marking each section's
   interaction model: static, click, hover, scroll, time, or unknown.
6. **Describe only journeys you saw.** If the destination was blocked, mark the
   outcome unobserved rather than inventing it, and set the journey status to
   `partial`.
7. **Name the adaptation opportunity**: what to preserve (the decision, its
   context, the wording that carries meaning) and what to abstract (branding,
   decorative media, unrelated features).
8. **Validate and fix.**

   ```bash
   python3 .claude/skills/website-flow-reference/scripts/validate_reference.py references/<site-key>/reference.json
   ```

## Evidence rules

- Every screenshot, DOM inspection, interaction, or source document gets a stable
  evidence id, a `url`, an ISO 8601 `capturedAt`, a capture method, and a viewport
  where applicable.
- Screenshot evidence needs a `path`, and the validator checks the file exists.
  Never record evidence for a capture that did not happen.
- Treat appearance and behaviour as separate observations. Seeing a button is not
  seeing what it does.
- Never write "pixel-perfect", "1:1", or "fully extracted" unless the evidence
  supports that exact claim.
- Do not download or reuse third-party logos, images, copy, or protected assets
  to build a prototype. Use placeholders unless reuse is authorised.

## Handoff

`reference.json` is the input to `flow-validation-prototype`. A prototype tests
one selected journey; it does not reproduce the source website.

## Resources

- [Reference contract](references/reference-contract.md) — `reference.json` shape and rules
- `scripts/validate_reference.py` — evidence and journey validator
