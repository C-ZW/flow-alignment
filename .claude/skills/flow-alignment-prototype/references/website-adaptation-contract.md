# Website Adaptation Contract (`adaptation.json`, version 1)

`adaptation.json` records how researched website journeys became validation flows.
It exists so a reader can tell what came from evidence, what was abstracted away,
and what was assumed — per flow. An artifact carrying three website-derived flows
needs three entries; a reader must never have to guess which evidence backs which
flow. Required only when the prototype starts from a `website-flow-reference`
artifact.

```json
{
  "version": 1,
  "id": "research-brief-flow",
  "reference": {
    "path": "references/example-site/reference.json",
    "id": "example-site"
  },
  "adaptations": [
    {
      "flowId": "research-brief-flow",
      "journeyId": "journey-research-to-build",
      "mode": "wireframe",
      "hypothesis": "A structured brief helps a builder understand what to make before implementation.",
      "task": "Prepare a brief for the selected website journey.",
      "preserve": [
        "The research-before-build sequence",
        "The explicit evidence boundary"
      ],
      "abstract": [
        "Third-party branding and logos",
        "Pixel-level styling",
        "Unrelated navigation"
      ],
      "assumptions": [
        "The destination page was not observed; the outcome copy is invented."
      ],
      "claims": [
        "This flow adapts one documented journey. It is not a clone of the source website."
      ]
    }
  ]
}
```

## Rules

### Document

- `version` is `1`.
- `id` is kebab-case and matches the prototype folder.
- `reference.id` must match the source `reference.json`; `reference.path` points
  at it from the repository root. The validator resolves that path, requires
  the file to exist and contain JSON, and checks that it is the same reference
  JSON supplied to the validator (including the source id; the CLI also checks
  the supplied file contents). A path to a different or missing reference is an
  invalid handoff, even when the in-memory objects happen to look compatible.
  Resolution follows real filesystem targets: a repository-relative path or
  symlink that escapes the repository (or the validator's explicit base
  directory) is invalid and is never read.
- `adaptations` is non-empty. No two entries may claim the same `flowId`.

### Each entry

- `flowId` must name a flow declared in `flow.json`.
- `journeyId` must name a journey in the reference.
- `task` must be identical to that flow's value. `hypothesis` is optional, for
  the same reason it is optional on a flow — a journey being confirmed with a
  client has a scenario, not a research question — but when present it must match
  the flow's. The adaptation and the prototype cannot disagree about what is
  being confirmed.
- `mode` is `wireframe` (default) or `visual-reference`. `visual-reference` may
  preserve evidence-supported product structure; it never claims visual
  equivalence. See the required layout map below.
- `preserve` and `abstract` each need at least one item. Preserve the decision,
  its context, and the wording that carries meaning. Abstract branding,
  third-party assets, long source copy, and unrelated features.
- `assumptions` is required whenever the journey status is `partial` or
  `inferred`, and is the right place to say "the source documents a command-line
  sequence, so every screen here is invented".
- `claims` states the scope and must not contain `pixel-perfect`, `1:1`,
  `exact clone`, or `fully cloned`.

Before drawing, write a small state-alignment table in the working notes: one row
for the reference entry and one for each journey step, naming the prototype state
that represents its destination. Compare the final graph back to that table.
States beyond it are proposals, not evidence-backed source behavior; either
remove them from a reference-alignment flow or declare the changed behavior as a
separate proposed flow with an unsettled ledger entry. Never insert an extra
confirmation action merely because the prototype outcome model asks what changed.

### `visualReference` — required in visual-reference mode

A mode label alone does not make the product canvas resemble the reference.
When `mode` is `visual-reference`, add:

```json
"visualReference": {
  "evidence": ["ev-home-desktop", "ev-detail-desktop", "ev-home-mobile"],
  "shell": ["Compact horizontal header with search above a global nav row"],
  "hierarchy": ["Wide banner, notice strip, section tabs, then the dated content timeline"],
  "density": ["Six repeated cards per desktop row; two per observed mobile row"],
  "responsive": ["Global nav collapses while the content grid becomes two columns"]
}
```

- `evidence` cites one or more screenshot records from `reference.json`.
- `shell`, `hierarchy`, and `density` are non-empty lists of observed structural
  decisions the prototype will preserve.
- `responsive` is optional. Include it only for observed breakpoint behavior;
  otherwise record the responsive treatment in `assumptions` as adapted.
- The statements describe layout, not exact CSS values, protected assets, or
  visual-equivalence claims.

The prototype should visibly implement this map in its product shell, state
views, and product-specific CSS. The generic observer rail and engine do not
change. Before handoff, compare source and prototype renders at the cited
viewport using shell orientation, region order, proportions, repeated-item
density, and responsive reflow—not pixel matching.

## The prototype cannot be more certain than the research

Three checks connect the two files, so a gap in the evidence cannot quietly close
on the way into the prototype:

- If the flow's `entry.basis` is `observed`, every id in `entry.evidence` must
  exist in `reference.json`, and the journey's own `entry.status` must be
  `observed` too.
- If the journey is `inferred`, the flow's `entry.basis` may not be `observed`.
- If the journey is `partial` or `inferred`, the flow's review ledger must carry
  at least one `open` or `assumed` point.

That last one is the important one. An assumption recorded only here is absent
from the facilitator's review material. `adaptation.json` is an audit trail for
a reader; the ledger supplies questions to `walkthrough.md`. Research gaps have
to travel all the way to the room.

The same certainty rule applies to copy. A screen may say "the signup boundary
was reached" when that was observed. It may not say "after signup the user
returns to the same job" while research stopped before account creation; that
belongs in an open ledger question until evidence or a domain owner settles it.

## Mixing derived and original flows

An artifact may hold both. Only the derived flows need entries — but any flow
that borrows a decision, a sequence, or wording from the source **is** derived,
and leaving it undeclared misrepresents where it came from.

## Selecting a journey

Prefer a journey with status `observed`, which requires its entry point and every
step to have been seen. A `partial` journey is acceptable when the unobserved
part is recorded as an assumption *and* carried into the ledger. Build from an
`inferred` journey only when the user asks for it explicitly, and say so in
`claims`.
