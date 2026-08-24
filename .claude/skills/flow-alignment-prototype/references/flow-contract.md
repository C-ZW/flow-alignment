# Flow Contract (`flow.json`, version 1)

`flow.json` is the single source of truth for the journey, its review ledger, and
the navigation rendered in the rail. `prototype.html` embeds the same object and
never holds flow logic the specification does not declare. `entry` says where
the journey starts and on whose authority, `focus` says which screens the meeting
is about, and `review` records what is still open for the agent and facilitator.

```json
{
  "version": 1,
  "flows": [
    {
      "id": "subscription-pause-offer",
      "title": "Pause option during cancellation",
      "task": "The user will not need the product for a month or two and wants to avoid charges without losing data.",
      "entry": {
        "state": "app-home",
        "basis": "assumed",
        "why": "This is the first screen a paying user sees after opening the product and where cancellation discovery begins.",
        "preconditions": ["Signed in", "Has an active paid subscription"]
      },
      "focus": ["retention-offer"],
      "review": [
        {
          "aspect": "entry-point",
          "status": "assumed",
          "proposal": "Start from the signed-in product home.",
          "states": ["app-home"],
          "question": "Do people start cancellation in the product or from a billing email link?",
          "alternatives": ["Enter the subscription page directly from a billing notice"]
        },
        {
          "aspect": "navigation",
          "status": "open",
          "proposal": "Home → Account settings → Subscription.",
          "states": ["app-home", "account-settings"],
          "question": "Can users find subscription management under account settings?"
        },
        {
          "aspect": "branches",
          "status": "open",
          "proposal": "Pause and cancel are shown side by side, and both routes are complete.",
          "states": ["retention-offer"],
          "question": "Does the side-by-side layout make cancellation harder to find?"
        },
        {
          "aspect": "failure-recovery",
          "status": "not-applicable",
          "proposal": "This journey does not include a technical failure; build one as a separate complete flow when it needs review.",
          "states": []
        },
        {
          "aspect": "ending-state",
          "status": "assumed",
          "proposal": "After pausing, the subscription page shows the resumption date; after cancellation, it shows the data-retention deadline.",
          "states": ["plan-paused-view", "plan-cancelled-view"],
          "question": "Can users still read existing data while paused?"
        }
      ],
      "states": [
        {
          "id": "app-home",
          "title": "My notes",
          "step": 1,
          "scope": "shell",
          "spotlight": "home-summary",
          "navTargets": { "settings": "account-settings" },
          "instruction": "Start from product home and let the walker find the route.",
          "transitions": ["account-settings"]
        },
        {
          "id": "account-settings",
          "title": "Account settings",
          "step": 2,
          "scope": "shell",
          "spotlight": "subscription-row",
          "navTargets": { "notes": "app-home" },
          "instruction": "Where is the subscription plan on this page?",
          "transitions": ["subscription-plan", "app-home"]
        },
        {
          "id": "subscription-plan",
          "title": "Subscription plan",
          "step": 3,
          "spotlight": "plan-card",
          "instruction": "The section under review begins here.",
          "transitions": ["retention-offer"]
        },
        {
          "id": "retention-offer",
          "title": "Options before cancellation",
          "step": 4,
          "spotlight": "retention-choice",
          "instruction": "This is the focus screen: pause and cancel appear side by side.",
          "transitions": ["pause-duration", "cancel-confirmed", "subscription-plan"]
        },
        {
          "id": "pause-duration",
          "title": "Choose pause duration",
          "step": 5,
          "spotlight": "pause-options",
          "instruction": "Review the pause duration and resumption date.",
          "transitions": ["pause-confirmed", "retention-offer"]
        },
        {
          "id": "pause-confirmed",
          "title": "Subscription paused",
          "step": 6,
          "terminal": true,
          "spotlight": "pause-result",
          "instruction": "Review the paused status, data retention, and resumption date.",
          "outcome": {
            "happened": "The subscription is paused for two months and resumes automatically on 2026-10-21.",
            "changed": ["Subscription status: active → paused", "Next billing date: 2026-09-21 → 2026-10-21"],
            "continuation": "plan-paused-view"
          },
          "transitions": ["plan-paused-view"]
        },
        {
          "id": "cancel-confirmed",
          "title": "Subscription cancelled",
          "step": 6,
          "terminal": true,
          "spotlight": "cancel-result",
          "instruction": "Review the data-retention deadline and reactivation conditions.",
          "outcome": {
            "happened": "The subscription is cancelled, with access retained through the current billing period.",
            "changed": ["Subscription status: active → cancelled", "Data retained until 2026-12-21"],
            "continuation": "plan-cancelled-view"
          },
          "transitions": ["plan-cancelled-view"]
        },
        {
          "id": "plan-paused-view",
          "title": "Subscription plan — paused",
          "step": 7,
          "spotlight": "paused-plan",
          "instruction": "The same page after pausing, with the resumption date and resume-now action.",
          "transitions": []
        },
        {
          "id": "plan-cancelled-view",
          "title": "Subscription plan — cancelled",
          "step": 7,
          "spotlight": "cancelled-plan",
          "instruction": "The same page after cancellation, with retention details and a reactivation entry point.",
          "transitions": []
        }
      ]
    }
  ]
}
```

## Rules

### Document

- `version` is `1`.
- `flows` is a non-empty array with unique kebab-case ids.
- Write **one** flow by default; up to three flows of the same product are fine
  when one meeting covers several journeys. The validator rejects more than three.

### Flow

- Required: `id`, `title`, `task`, `entry`, `focus`, `review`, `states`.
  - `title` is what appears in the flow selector — name the journey, not the feature.
  - `task` is the scenario in one or two sentences: what the person is trying to
    do and why. It is available in the Purpose disclosure and is phrased as a claim the
    room can correct, not product-introduction copy.
- Optional: `hypothesis` and `successSignal`. Fill them in only when the artifact
  will be used for a moderated participant session. They remain part of the
  specification and walkthrough rather than adding another rail control. An
  empty string is rejected — omit the field instead.

### `entry` — where the journey starts, and on whose authority

The rule the whole artifact rests on is **every flow starts at the beginning; do not skip directly to the discussion screen**.
A validator cannot know whether your starting screen is where people really
start. What it can do is refuse to let the claim go unwritten.

```json
"entry": {
  "state": "app-home",
  "basis": "assumed",
  "why": "This is the first screen a paying user sees after opening the product.",
  "preconditions": ["Signed in", "Has an active paid subscription"],
  "evidence": []
}
```

- `state` must be a declared state, must be `step: 1`, and must not be terminal.
- `basis` is one of:
  - `observed` — seen on a real product or a researched site. Requires a non-empty
    `evidence` array of ids from the accompanying `reference.json`.
  - `provided` — the client or the team told us this is where people start.
  - `assumed` — we picked it. Say so.
- `why` must say why a real user is standing here when the journey starts.
- `preconditions` lists what this journey assumes has already happened and
  therefore skips — signing in, having a subscription, having received an
  invitation. Use `[]` to state plainly that there is nothing; the validator warns
  so the emptiness is a decision rather than an omission.

The rail shows all of this, including the basis badge. "We assumed people start
here" is exactly the kind of claim a
domain owner is in the room to correct.

### `focus` — which screens this meeting is about

- A non-empty array of declared state ids.
- **The entry state may not be in `focus`.** This is the field that makes
  “do not skip directly to the discussion screen” checkable: if the screen under discussion is also where the
  artifact opens, the journey to it was never built.
- Every focus state must be reachable from the entry point by walking declared
  transitions. The rail marks them with `◆`.

Everything between entry and focus is the navigation the walkthrough exists to
test as much as the destination. Two or three steps of genuine navigation is
usually enough; you are not reproducing the product.

### `review` — the ledger of what is not settled

Five aspects, each declared exactly once. Silence reads as agreement, so the
validator rejects a missing aspect — but never rejects `open`. An unanswered
question is why this artifact exists.

| aspect | the question behind it |
| --- | --- |
| `entry-point` | Is this where people actually start? |
| `navigation` | Is this how they get there, and is a step missing? |
| `branches` | Are these all the choices, and does each land somewhere real? |
| `failure-recovery` | What happens when it fails, and can they get out? |
| `ending-state` | Where does this leave them, and does the product say so? |

Each entry carries:

- `aspect` — one of the five, unique within the flow.
- `status` — `open`, `assumed`, `confirmed`, or `not-applicable`.
- `proposal` — what this artifact currently proposes. Required.
- `states` — the screens it is about. The facilitator walkthrough raises the
  point beside those screens. Required and non-empty unless the status is
  `not-applicable`.
- `question` — required when the status is `open` or `assumed`. Write the question
  you will actually put to the room.
- `alternatives` — optional. Other ways this could work.
- `basis` — optional. Where the proposal came from, or what limits it.
- `alternativeFlows` — optional. See the next section.

The agent-facing ledger cannot contradict the rest of the file:

- `entry-point` cannot be `confirmed` while `entry.basis` is `assumed`.
- All five `confirmed` warns: if nothing is open, what is the walkthrough for?

Review points remain in `flow.json` and travel into the facilitator's walkthrough;
the browser rail does not render them.

### Product branch or design alternative?

These get confused, and confusing them produces an artifact that claims more
coverage than it has.

- A **product branch** is a choice the user makes inside one product proposal:
  submit the callback request, go back and pick another slot, cancel. It must be a
  declared `transition` with a real outcome the room can click through to.
- A **design alternative** is two competing product definitions the team is
  choosing between: "show the locked slots greyed out" versus "do not show them at
  all". It is not a button on a screen.

If the alternative changes what a screen shows or where the journey goes, build
it as a **second flow**, complete, from its own entry point, and link the two from
the ledger:

```json
{ "aspect": "branches", "status": "open", "alternativeFlows": ["reschedule-hidden-slots"] }
```

The validator checks that the named flow is in this artifact. A design
alternative the room cannot walk is not an alternative yet — it is a sentence in a
document, which is the thing this project exists to replace. If the difference is
only wording or policy, leave it in `alternatives` and do not grow the graph.

### Responsive alternatives

Responsive layout alone does not create a second flow. A responsive change to
the action graph does: a narrow viewport may require opening a menu before search
while the wide viewport exposes search directly. Build both complete journeys
and declare the relationship on either flow:

```json
"responsiveAlternatives": [
  {
    "flowId": "place-search-mobile",
    "viewport": "narrow",
    "reason": "Search is reached through the mobile menu before the same query can be submitted."
  }
]
```

`flowId` must name another flow in the same artifact, `viewport` is `narrow` or
`wide`, and `reason` states what changes in the graph. At most one alternative
may be declared for each viewport. Do not use this field when only columns,
spacing, or control placement reflow.

### States

- At least two states. Ids are unique within the flow and kebab-case.
- Required per state: `title`, a positive integer `step`, an `instruction` (the
  facilitator note shown in the rail), and an explicit
  `transitions` array.
- Every transition target must exist, every state must be reachable from the entry
  point, and at least one reachable state must be `terminal: true`. Every
  reachable branch must also be able to reach a valid terminal outcome; a closed
  loop beside a successful branch is still an invalid journey.
- A state with no transitions must be either terminal or the `continuation` of an
  outcome. Anything else is a dead end nobody meant to build.

#### Steps and branches

**Steps that share a number are drawn as alternatives** — `├` and `└` under one
node rather than consecutive rows. Use it deliberately: it is how a reader sees
that a decision forks.

The validator checks the claim against the graph. If you can walk from one of the
siblings to another without going backwards, they are consecutive screens, not
alternatives, and the rail would be telling the room something the graph
contradicts. A genuine fork whose targets sit at different step numbers warns for
the opposite reason: it is drawn as a straight line and reads as one path.

#### Outcomes

`terminal: true` marks the state where a branch's business action resolves; it
does not necessarily mean the final rendered screen. It may transition once to
an ending-state view that shows the postcondition. Every such outcome state
declares what its branch actually did:

```json
"outcome": {
  "happened": "The subscription is paused for two months and resumes automatically on 2026-10-21.",
  "changed": ["Subscription status: active → paused", "Next billing date: 2026-09-21 → 2026-10-21"],
  "continuation": "plan-paused-view"
}
```

- `happened` — one sentence in product terms.
- `changed` — non-empty list of what is now different. If a branch changes
  nothing, write that; a branch that changes nothing is itself worth confirming.
- `continuation` — the screen the product naturally goes to next, or `null` when
  the journey really stops here (in which case `transitions` must be empty).

The transition cardinality must agree exactly with that value: a non-null
continuation requires exactly one declared transition and it must target that
state; `null` requires zero transitions. A terminal outcome must not quietly
offer an additional route that has no postcondition record.

An observed destination can itself be the terminal state. This matters at
research boundaries: arriving at a signup gate, rendered list, or article body
is already the observed result. Describe the honest postcondition (`changed` may
say that nothing was submitted or mutated), set `continuation` to `null`, and
stop. Do not add "view status", "confirm result", "start reading", or another
button only so the graph has one more screen. That would turn artifact structure
into product behavior the room never agreed exists.

**A continuation may not be a screen the walker already passed through.** The
engine is stateless: coming back to the appointment page the walker saw at step 3
shows the appointment *before* the change, which undoes the outcome in front of
the room. Declare a separate state — `plan-paused-view` next to `plan-cancelled-view`
— showing the same page after this particular branch. Two outcomes may not share
one continuation, for the same reason.

This costs a screen per branch. That screen is the postcondition, and confirming
it is the point of the `ending-state` review aspect.

### Failure and recovery

The rail exposes `Restart` and direct state navigation. A technical or
environmental failure that needs review is a separate
complete flow with its own scenario and entry point. Reproduce the route from the
beginning, let the relevant product action land on the failure state in that
flow, then show its recovery and ending state. Link the normal and failure flows
with `alternativeFlows` when they are two versions of the same decision.

A business rule the user hits by their own choice ("this slot is inside 24 hours,
so it needs a phone call") remains an ordinary branch inside the journey. If the
user's choice determines the result, it is a transition, not a technical failure.

When there is no failure worth showing, mark
`failure-recovery` as `not-applicable` with a reason. Absence is not evidence
that anyone thought about it.

### Navigation and scope

- `scope` is `viewport` (default) or `shell`.
  - `viewport` — the region named by `spotlight`, or the regions named by
    `spotlights`, are the only holes in the mask, ringed in amber; the surrounding
    page and shell are covered and inert.
  - `shell` — the mask stays. If the sole action is one routed navigation link,
    that link becomes the single ringed hole and the contextual spotlight region
    stays dimmed. If the page also offers a declared `data-goto`, that spotlight
    keeps its hole without the ring and routed navigation is punched through
    beside it. Unrouted chrome stays covered and takes no pointer events.
- `spotlight` is a kebab-case key naming the smallest coherent action, decision,
  or result region for this state. Its template contains exactly one matching
  `data-spotlight` wrapper, and every `data-goto` on the state sits inside it.
  Older artifacts without it fall back to the whole viewport and emit a warning.
- `spotlights` is the multi-region alternative: two or three unique kebab-case
  keys, each with exactly one matching wrapper. Use it only when separated
  regions must be understood together. `spotlight` and `spotlights` are mutually
  exclusive, and every `data-goto` must sit inside at least one declared region.
- `navTargets` maps shell navigation keys to states: `{ "settings": "account-settings" }`.
  - Every value must be a declared transition **from that state**.
  - Every key must exist as a `data-nav` attribute on a shell element.
  - A state with `navTargets` must declare `scope: "shell"`; otherwise the
    navigation it points at stays dimmed and unusable.
  - A shell step may declare at most one `navTargets` entry. Navigation-only
    shell steps focus that one routed control; exposing two routed controls
    would make the declared single-navigation spotlight ambiguous. If the
    product action is also present, the same single routed navigation control
    may be punched through beside it.
  - A `shell` state with no `navTargets` is allowed but warned: the shell is open
    and nothing in it leads anywhere.

## Prototype integration

Embed the same object in `prototype.html`:

```html
<script id="flow-spec" type="application/json">…</script>
```

Each state gets one `<template data-flow data-state>` view. Product actions are
`data-goto="<state-id>"` on a `<button>`. A failure is its own state with its own
ordinary template. See
[the prototype architecture](prototype-architecture.md).

The document must run from disk without network calls or analytics. The only
permitted remote references are exact `fonts.googleapis.com` and
`fonts.gstatic.com` hosts for the sketchbook fonts; a URL merely containing one
of those names is not permitted. Do not use `fetch`, XHR, WebSocket,
`navigator.sendBeacon`, analytics SDK calls, or equivalent telemetry.

The validator rejects a mismatch between the embedded spec and `flow.json`, a
`data-goto` that is not a declared transition out of that state, a declared
transition that nothing offers, a nav key with no shell element, and rail controls
inside a product screen.

## What the validator cannot decide

It checks that the journey you declared is structurally complete and internally
consistent. It cannot prove runtime walkability, tell you that “patient home” is
not where patients actually start, detect a real-product step nobody declared, or
know that a third branch is missing. Those are settled by browser-walking the
artifact with the people who know — which is what the artifact is for.
