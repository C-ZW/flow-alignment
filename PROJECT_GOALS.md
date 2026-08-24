# Flow Alignment Skills — Project Goals

## Purpose

This project builds reusable agent skills for creating clickable flow artifacts
that the people responsible for a journey can walk end to end to align their
understanding before anyone commits to design or engineering. The driver is a
facilitator, not a product presenter; the other people in the room are there to
correct the artifact's claims, not receive a product introduction. The output is
not a static mockup, sales demo, or usability lab instrument: it makes a proposed
journey concrete enough to agree, disagree, and name what remains unknown.

## What a successful artifact establishes

Separate two things that are easy to conflate.

**What the validator proves** — that the journey *as declared* is structurally
complete:

1. It starts at a declared entry point, at step 1, which is not the screen under
   discussion, and it says on whose authority that starting point was chosen.
2. Every declared branch is reachable, offered by something on screen, and lands
   on a state that exists.
3. Every outcome declares what it changed and continues to a screen that shows
   the change, rather than one the walker already passed.
4. Every one of the five review aspects — entry point, navigation, branches,
   failure and recovery, ending state — has a stated position.

**What the artifact makes possible** — that a room can adjudicate whether the
declared journey is the real one:

5. The decision, friction, or value proposition is visible in believable product
   context, with data specific enough to be corrected.
6. What is still undecided is explicit in `flow.json` and routed into the
   facilitator walkthrough, so it can be raised beside the relevant screen.
7. It can be navigated non-linearly in an alignment meeting without the
   facilitator explaining the tooling or pitching the product.

**What neither establishes.** No static check can know that a branch the author
never thought of is missing, that the real product has a step nobody wrote down,
or that people do not in fact start where the entry declaration says. It does not
prove product-market fit, usability metrics, visual taste, implementation
feasibility, or final-brand quality. The artifact's job is to state its claims
specifically enough that a person who knows better can contradict them.

## Output modes

### 1. Flow prototype

Create a low-fidelity, Balsamiq-style web prototype of a proposed flow. Use this
when a team needs to confirm a new or changed journey with each other or with a
client.

- Output: `prototypes/<flow-name>/`
- Includes: `prototype.html`, `flow.json`, and `walkthrough.md`
- `flow.json` carries the entry declaration, the focus screens, and the review
  ledger of what is still open — not only the graph
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
- Every journey step carries its own evidence, and a journey may only call itself
  observed when its entry point and every step were seen. Gaps travel forward
  into the prototype's review ledger.

## Required interaction architecture

Every artifact separates the tooling from the product.

| Area | Contains | Must not contain |
| --- | --- | --- |
| Flow navigator rail | restart at the top, flow selector, entry declaration, expanded clickable route map, step note, and scenario | product navigation, business actions, meeting-data entry, review forms, or injected failures |
| Product viewport | believable product content and product-language actions | restart, step notes, scenario, hypothesis, telemetry, review points, or failure controls |
| Product shell | product chrome, and the declared navigation the journey passes through | interactive paths the flow does not declare |

Each step declares its interaction scope and a named spotlight region. A mask
always covers what the step does not use. On a `viewport` step the smallest
coherent action, decision, or result region is the one hole, ringed in amber. On
a navigation-only `shell` step the mask stays and the single routed navigation
control is the one focus; contextual product content remains dimmed. When the
page also offers a declared action, its region keeps the hole without the ring
and routed navigation is punched through beside it. Only elements the
specification declares ever become interactive; everything else stays covered
and inert, and no uncovered region may imply an action it cannot perform.

The route map is open by default: it shows position and shape, and every node
jumps directly to its state. A jump supports non-linear discussion but does not
prove the skipped transitions; each branch is still walked through product
actions before handoff. Its highlighted node replaces a separate current-step
card and progress counter. Review positions remain in `flow.json` and the
facilitator walkthrough rather than occupying the rail.

## Source-of-truth rule

Use a machine-readable flow specification as the single source of truth. For the
core skill this is `flow.json`.

- It declares the flows, the scenario, the entry point and its basis, the focus
  screens, the review ledger, the steps, explicit transitions, outcome
  postconditions, navigation routing, and interaction scope.
- Open questions and assumptions live here, not only in `walkthrough.md`. A
  question that lives only in a Markdown file is a second, unvalidated copy.
- The prototype embeds the same specification and renders its navigation and
  product states from it; the facilitator walkthrough carries the review prompts.
- The validator reads the specification directly, checks graph reachability, and
  rejects HTML that references undeclared states or navigation.
- HTML is a view layer, not the only record of the flow logic.
- The browser rail is read-only. It shows the scenario, entry declaration,
  route map, and selected-state note, with no meeting-data form. People
  give corrections to the agent; the agent updates `flow.json` and affected
  views deliberately, validates them, and re-walks the complete branch.

## Quality bar

- One flow, one journey. An artifact may carry up to three flows of the same
  product when one meeting covers several related journeys.
- The journey begins from a declared entry point at step 1 and ends on a screen
  that shows what changed. An artifact never opens directly on the screen under
  discussion — the `focus` field makes that checkable.
- Every declared transition has something that offers it, and every branch lands
  somewhere real. A design alternative that changes a screen is a second flow,
  complete from its own entry point — not a note claiming the client will see it.
- A reference-derived alignment flow keeps the observed click count and
  destination order. An observed boundary can be its terminal result; structural
  completeness must never be purchased by inventing another product action.
- A technical failure that needs confirming is a separate complete flow from its
  entry point; otherwise failure and recovery is marked `not-applicable` with a
  reason. Absence is not evidence that anyone considered it.
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

## Known limits

- JSON validators do not semantically compare every review question or evidence
  id with the companion Markdown files. Handoff review must confirm that
  `walkthrough.md`, `ia.md`, `journeys.md`, and `evidence.md` faithfully surface
  the validated source records.
- Static checks cannot see runtime failures: a control hidden at a breakpoint, a
  stacking-context problem, or a route that works in the graph and not on screen.
  Walking the file is not optional.
