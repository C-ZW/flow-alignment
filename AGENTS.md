# Working in this repository

This repo builds agent skills that produce clickable flow artifacts — the kind a
team walks end to end to confirm a proposed journey, and then walks a client
through. Read [PROJECT_GOALS.md](PROJECT_GOALS.md) first: it defines what an
artifact must prove and what it must not claim.

## The two skills

- `.claude/skills/flow-validation-prototype/` — hypothesis or researched journey → clickable prototype
- `.claude/skills/website-flow-reference/` — public URL → evidence-backed research

Everything else was retired. Do not resurrect a "high-fidelity clone" or
"pixel-perfect extraction" skill: claiming visual parity without evidence is an
explicit non-goal.

## Rules that are not negotiable

1. **Output location.** Generated artifacts go to `prototypes/<flow-name>/` or
   `references/<site-key>/` at the repository root. Never write them under
   `.claude/skills/`, which holds skill definitions, templates, and scripts only.
2. **`flow.json` is the source of truth.** It declares flows, states,
   transitions, and observer guidance. `prototype.html` embeds the same object
   and renders it. Never encode a transition only in markup or JavaScript.
3. **The engine is generic.** Copy `assets/prototype-template.html` and edit
   exactly three regions: the dimmed product shell, `#flow-spec`, and
   `#state-views`. A test asserts every prototype's engine block is byte-identical
   to the template's.
4. **Tooling stays outside the product.** Flow selector, step list, step note,
   scenario, brief, reset, error simulation, and the presentation toggle belong
   to the rail. A product screen containing any of them is a defect, not a style
   choice. `data-goto` is the product; `data-jump` and `data-nav` are not.
5. **Journeys are complete.** Start where a real user would be standing and walk
   the real navigation; never open directly on the screen under discussion. Every
   branch lands somewhere real, and terminal states continue in product language
   — "Back to pending members", never "Restart flow".
6. **Runs from disk.** No backend, build step, network call, analytics, or
   blocking dialog. Google Fonts is the only permitted remote reference.
7. **One flow, one journey.** An artifact may carry up to three flows of the
   same product for one meeting; each declares its own scenario. More than three
   and it stops being about anything in particular. `hypothesis` and
   `successSignal` are optional — fill them in only for a moderated participant
   session.
8. **Evidence discipline.** For website research, separate observed from
   inferred, record limitations, and never claim an interaction you did not see.
   Do not reuse third-party logos, images, or protected copy.

## Sketchbook visual language

Patrick Hand with a Comic Neue fallback, dotted graph-paper canvas
(`radial-gradient(#d4d4d8 1.2px, transparent 1.2px)`), wobbly borders
(`255px 15px 225px 15px / 15px 225px 15px 255px`), native `<button>` elements
with `.btn-sketch-primary` / `.btn-sketch-secondary` / `.btn-sketch-danger`.
Never below 13px. Low visual fidelity is deliberate: it keeps feedback on the
flow rather than the styling.

## Before handing anything over

```bash
python3 .claude/skills/flow-validation-prototype/scripts/validate_flow_spec.py <flow.json> <prototype.html>
python3 -m unittest discover -s tests
```

Errors block handoff; warnings are judgement calls to resolve or explain. Then
open the file and walk every branch yourself. The validator checks structure —
only a person can check that the screen reads like a real product.

These artifacts confirm that a flow is complete and correct. They do not measure
users. Never report a usability result before a session with a participant has
happened.
