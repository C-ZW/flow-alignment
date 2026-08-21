# Flow Validation

Two agent skills for building clickable flow artifacts that a team — and their
client — can walk end to end, to confirm a proposed flow before anyone commits to
design or engineering.

The output is not a mockup and not a usability lab instrument. It is a navigable
artifact that makes a proposed journey concrete enough to agree or disagree with:
it starts where a real user would be standing, walks the real navigation, and
gives every branch an outcome. See [PROJECT_GOALS.md](PROJECT_GOALS.md) for what
it must prove — and what it deliberately does not.

## The two skills

| Skill | Input | Output |
| --- | --- | --- |
| [`flow-validation-prototype`](.claude/skills/flow-validation-prototype/SKILL.md) | A hypothesis, or a researched journey | `prototypes/<flow-name>/` |
| [`website-flow-reference`](.claude/skills/website-flow-reference/SKILL.md) | A public URL | `references/<site-key>/` |

Start from a hypothesis and you need only the first skill. Start from a real
website and you run the second one first, then adapt exactly one documented
journey.

```
  a hypothesis ─────────────────────────────────┐
                                                ▼
  a URL ──▶ website-flow-reference ──▶ flow-validation-prototype ──▶ prototypes/<flow>/
              references/<site>/          adaptation.json              flow.json
              reference.json                                           prototype.html
              ia · journeys · evidence                                 test-plan.md
```

## How an artifact is put together

`flow.json` is the source of truth. It declares every flow, state, transition,
and piece of observer guidance. `prototype.html` embeds the same object and
renders it — it is a view layer, never a second copy of the flow logic.

Three regions, and the separation between them is the point:

- **Flow navigator rail** — a 264px column on the left: flow selector, a
  branch-aware step list where every step jumps straight to that screen, the note
  for this step, the scenario, an optional brief, and reset, error, and
  presentation controls. Tooling, never product.
- **Product viewport** — the page the flow is currently on.
- **Product shell** — product chrome, plus the navigation the journey passes
  through.

Each step declares its scope. On a `viewport` step the page is spotlit and the
shell is dimmed and inert. On a `shell` step the whole app is bright and its
declared navigation is clickable, so the walker genuinely navigates to the
target instead of appearing there.

One artifact may carry up to three flows of the same product. `簡報` hides every
internal note, so the same file serves an internal review and a client
walkthrough.

A facilitator control inside the product stops the session testing the product
and starts it testing the test. The validator enforces this, not just convention.

## Working in this repository

```bash
# validate a prototype
python3 .claude/skills/flow-validation-prototype/scripts/validate_flow_spec.py \
  prototypes/<flow-name>/flow.json prototypes/<flow-name>/prototype.html

# validate website research
python3 .claude/skills/website-flow-reference/scripts/validate_reference.py \
  references/<site-key>/reference.json

# validate a website-derived handoff
python3 .claude/skills/flow-validation-prototype/scripts/validate_adaptation.py \
  prototypes/<flow-name>/adaptation.json \
  references/<site-key>/reference.json \
  prototypes/<flow-name>/flow.json

# run every test (stdlib only, no dependencies)
python3 -m unittest discover -s tests

# open an artifact
open prototypes/<flow-name>/prototype.html
```

## What the validators actually check

Not CSS classes and label strings. The rules that matter:

- The embedded specification matches `flow.json` exactly.
- Every state is reachable, every transition target exists, a terminal state can
  be reached, and step numbers are real.
- Every `data-goto` action is a declared transition **out of that state**, and
  every declared transition has a button that offers it. A graph you cannot walk
  is a graph that lies.
- Rail vocabulary never appears inside a product screen; only declared navigation
  is ever clickable in the shell; the rail carries no product action.
- Every nav key a step routes exists in the shell, exactly once.
- The page runs from disk: no network calls, no blocking dialogs, no build step.
- Screenshot evidence points at a file that exists.

The suite tests these rules by injecting one defect at a time into a known-good
artifact and asserting the validator names it.

## Layout

```
.claude/skills/
  flow-validation-prototype/     SKILL.md · references/ · assets/ · scripts/
  website-flow-reference/        SKILL.md · references/ · scripts/
prototypes/<flow-name>/          flow.json · prototype.html · walkthrough.md
references/<site-key>/           reference.json · ia.md · journeys.md · evidence.md
tests/                           validator rules, driven by fixtures under tests/fixtures/
```

The repository ships **skills, not demo content**. `prototypes/` and
`references/` hold whatever you generate; the test suite proves the rules using
its own fixtures, so it never depends on example artifacts being present.
Generated artifacts never live under `.claude/skills/`. A test enforces that too.
