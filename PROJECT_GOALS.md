# Flow Validation Skills — Project Goals

## Purpose

This project builds reusable agent skills for creating clickable flow artifacts
that a team — and their client — can walk end to end to confirm a proposed flow
before anyone commits to design or engineering. The output is not a static
mockup and not a usability lab instrument: it is a navigable artifact that makes
a proposed journey concrete enough to agree or disagree with.

## What a successful artifact proves

1. The journey is **complete**: it starts where a real user would be standing,
   goes through the real navigation, and ends somewhere real.
2. Every **branch** has an outcome. "What if they say no?" is answered in one
   click, not in conversation.
3. The decision, friction, or value proposition under discussion is visible in
   believable product context, with data specific enough to be corrected.
4. It can be **presented**: walked in a client meeting without internal notes on
   screen, and without the person driving explaining the tooling.

The artifact does not prove product-market fit, usability metrics, visual taste,
implementation feasibility, or final-brand quality.

## Output modes

### 1. Flow prototype

Create a low-fidelity, Balsamiq-style web prototype of a proposed flow. Use this
when a team needs to confirm a new or changed journey with each other or with a
client.

- Output: `prototypes/<flow-name>/`
- Includes: `prototype.html`, `flow.json`, and `walkthrough.md`
- Visual language: Patrick Hand, dotted graph-paper background, grayscale sketch
  borders, native sketchy buttons.
- Interaction depth: complete on the target journey, including the navigation
  that reaches it; static elsewhere.
- Optional input: an evidence-backed website reference. Record selected journey,
  preservation, abstraction, and assumptions in `adaptation.json`.

### 2. Website flow reference

Analyse a real URL to capture information architecture, visible copy,
screenshots, and candidate journeys. Use this to benchmark an existing product
before proposing a new flow.

- Output: `references/<site-name>/`
- Includes: source URL, capture timestamp, screenshots or capture notes, IA map,
  observed journeys, and explicit assumptions.
- Rule: distinguish verified observations from inferences. Do not claim an
  interaction exists when it was not observed.

## Required interaction architecture

Every artifact separates the tooling from the product.

| Area | Contains | Must not contain |
| --- | --- | --- |
| Flow navigator rail | flow selector, branch-aware step list, step note, scenario, optional brief, reset, error simulation, presentation toggle | product navigation or business actions |
| Product viewport | believable product content and product-language actions | reset, restart, step notes, scenario, hypothesis, telemetry, or error controls |
| Product shell | product chrome, and the declared navigation the journey passes through | interactive paths the flow does not declare |

Each step declares its interaction scope. On a `viewport` step the page under
discussion is spotlit and the shell is dimmed and inert. On a `shell` step the
whole app is bright and its declared navigation is clickable, so the walker
genuinely navigates instead of appearing at the destination. Only elements the
specification declares ever become interactive.

The rail can hide every internal note with one control, so the same file serves
an internal review and a client walkthrough.

## Source-of-truth rule

Use a machine-readable flow specification as the single source of truth. For the
core skill this is `flow.json`.

- It declares the flows, the scenario, the steps, explicit transitions, terminal
  outcomes, navigation routing, interaction scope, and optional error simulation.
- The prototype embeds the same specification and renders the rail from it.
- The validator reads the specification directly, checks graph reachability, and
  rejects HTML that references undeclared states or navigation.
- HTML is a view layer, not the only record of the flow logic.

## Quality bar

- One flow, one journey. An artifact may carry up to three flows of the same
  product when one meeting covers several related journeys.
- The journey begins from a believable entry point and ends with a natural
  product continuation. An artifact never opens directly on the screen under
  discussion.
- Every declared transition has something that offers it, and every branch lands
  somewhere real.
- Error and recovery branches exist when the failure is part of what needs
  confirming.
- The prototype works from a local file without a build system, backend, or
  external product APIs, at every supported width.
- Non-critical areas are intentionally static so the discussion stays focused.
- Generated artifacts never live under `.claude/skills/`.
- Every generated artifact has a walkthrough note and passes its structural
  validator.

## Non-goals

- A generic prompt that produces an entire product from vague requirements.
- A fake test suite based only on matching CSS classes, labels, or HTML strings.
- A high-fidelity clone that claims exact visual parity without evidence.
- Putting tooling controls on a product screen, or product actions in the rail.
- Rebuilding external products or relying on live APIs to make a prototype work.

## Optional: moderated participant sessions

The same artifact supports a moderated session. `hypothesis` and `successSignal`
are optional fields on a flow; fill them in when a session needs a stated
question and a stated signal. Leave them out when the flow is being confirmed
internally or with a client. Never report a usability result before a session
with a participant has happened.

## Skill roadmap

1. Use `flow-validation-prototype` for new flow artifacts and reference-derived
   adaptations.
2. Use `website-flow-reference` to create evidence-backed IA and journey research
   from URLs.
3. Retire or replace the current overlapping skills once the two-skill workflow
   has been exercised on representative examples.
