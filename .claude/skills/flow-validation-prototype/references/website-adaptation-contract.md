# Website Adaptation Contract (`adaptation.json`, version 3)

`adaptation.json` records how researched website journeys became validation flows.
It exists so a reader can tell what came from evidence, what was abstracted away,
and what was assumed — per flow. An artifact carrying three website-derived flows
needs three entries; a reader must never have to guess which evidence backs which
flow. Required only when the prototype starts from a `website-flow-reference`
artifact.

```json
{
  "version": 3,
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

- `version` is `3`. Versions 1 and 2 held a single flow at the top level and are
  rejected.
- `id` is kebab-case and matches the prototype folder.
- `reference.id` must match the source `reference.json`; `reference.path` points
  at it from the repository root.
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
  use evidence-supported hierarchy and density; it never claims visual
  equivalence.
- `preserve` and `abstract` each need at least one item. Preserve the decision,
  its context, and the wording that carries meaning. Abstract branding,
  third-party assets, long source copy, and unrelated features.
- `assumptions` is required whenever the journey status is `partial` or
  `inferred`, and is the right place to say "the source documents a command-line
  sequence, so every screen here is invented".
- `claims` states the scope and must not contain `pixel-perfect`, `1:1`,
  `exact clone`, or `fully cloned`.

## Mixing derived and original flows

An artifact may hold both. Only the derived flows need entries — but any flow
that borrows a decision, a sequence, or wording from the source **is** derived,
and leaving it undeclared misrepresents where it came from.

## Selecting a journey

Prefer a journey with status `observed`. A `partial` journey is acceptable when
the unobserved part is recorded as an assumption. Build from an `inferred`
journey only when the user asks for it explicitly, and say so in `claims`.
