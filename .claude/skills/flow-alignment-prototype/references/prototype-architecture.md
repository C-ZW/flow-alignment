# Prototype Architecture

`prototype.html` is a view layer over `flow.json`. It has four regions.

```
┌─ #observer-hud ─────┬─ #app-shell ─────────────────────────────┐
│ [Restart]           │  .product-context   product chrome       │
│ Flow                │   ┌─ #product-viewport ──────────────┐   │
│ [flow ▾]            │   │ the page the journey is on        │   │
│                     │   └───────────────────────────────────┘   │
│ Purpose …           │  spotlight → tight hole, amber ring       │
│ Entry [ASSUMED] …   │  scope: shell → routed nav focus          │
│ + Preconditions     │                                          │
│ − View route map    │  292px rail, sticky. Folds to a top bar   │
│ 1. Home             │  below 900px.                             │
│ 2. Account settings │                                          │
│ This step …         │  Every route row is a direct jump.       │
└─────────────────────┴──────────────────────────────────────────┘
  #state-views   <div>, exactly once; <template data-flow data-state> per state
  #flow-spec     <script>, exactly once; the exact contents of flow.json
```


## What you edit

Do not edit the generated `prototype.html` directly. Initialize
`authoring/product-shell.html`, `authoring/state-views.html`, and
`authoring/product.css` with `scripts/build_prototype.py --init`, edit those
fragments plus `flow.json`, and run the builder to assemble the standalone file.
This keeps the product-owned surface physically separate from the generic engine.

The builder reads `assets/prototype-template.html` and inserts these
product-owned inputs:

1. **The product shell** inside `#app-shell` — header and navigation for the real
   product. Keep `class="product-context"`; give each navigable item a stable
   `data-nav` key.
2. **`#flow-spec`** — one `<script type="application/json">`, exactly once;
   paste the exact contents of `flow.json`.
3. **`#state-views`** — one `<div>`, exactly once, containing one `<template>`
   per state and holding real product markup. Duplicate containers are invalid:
   the runtime selects the first matching id, so a hidden duplicate can make the
   source pass a presence check while the browser renders the wrong content.
4. **Product-specific CSS after the designated marker** — style only the product
   shell and state views. Everything before the marker remains generic and
   byte-identical to the canonical template.

Leave the engine `<script>` alone. It is generic: it reads the spec, renders the
rail, clones the matching template into the viewport, wires the shell navigation
for the current step, and refuses any transition the specification does not
declare. A test asserts it stays byte-identical across every prototype.

The template also carries the artifact's security boundary. Keep its single
Content-Security-Policy meta tag inside `<head>` and before every base, link,
style, script, or refresh directive: inline engine/product CSS and scripts
are required for a file-based prototype (inline event attributes remain blocked),
Google Fonts is the only remote style and font exception, and images/media are
limited to local or data URLs. Network
connections, frames, objects, workers, manifests, and form submissions are
blocked. The validator rejects a missing, duplicated, or weakened policy.

For an artifact created before fragment authoring, run
`scripts/build_prototype.py prototypes/<flow-name> --extract` once. Review the
three extracted files, then rebuild. The command refuses to overwrite existing
fragments.

## State views

```html
<template data-flow="subscription-pause-offer" data-state="retention-offer">
  <p class="view-eyebrow">Account settings / Subscription / Cancel</p>
  <h1 class="view-title">There is another option before you cancel</h1>
  <div class="offer-grid">
    <div class="offer-card">
      <h2>Pause subscription</h2>
      <p>Pause for one to three months with <strong>no charges</strong> during that period.</p>
      <button class="btn-sketch-primary" type="button" data-goto="pause-duration">Pause subscription</button>
    </div>
  </div>
</template>
```

- One template per state, and only one. An alternative design or
  technical-failure journey is a separate complete flow.
- Actions are `<button data-goto="…">`. No `onclick`, no `href`, no `alert()`.
- Every `data-goto` must be a declared transition **out of that state**, and
  every declared transition needs something that offers it — a button here, or a
  nav key routed by `navTargets`.
- Write product language and specific data. A client corrects
  `Next billing date: 2026-09-21`; they cannot correct `[Date]`.

## Visual-reference product structure

When `adaptation.json` selects `visual-reference`, do not begin from the sample
product shell as a design suggestion. It is only placeholder markup. Build the
product regions from the cited layout evidence:

- Match the observed chrome orientation: horizontal media navigation should not
  become a dashboard sidebar, and vice versa.
- Preserve section order, dominant-area proportions, and repeated-item density.
  Use enough neutral placeholder items for the same wireframe silhouette; one
  oversized card is not a substitute for an observed dense grid.
- Keep journey actions on the observed surface. Do not add a synthetic list or
  navigation screen solely to make the artifact longer.
- Implement observed responsive reflow. When no narrow evidence exists, use a
  conservative usable adaptation and declare that assumption instead of calling
  it source behavior.

The sketchbook tokens still apply, and third-party assets still do not. The goal
is an evidence-backed low-fidelity composition that a person recognizes as the
same kind of page, not a branded reproduction.

### When several actions lead to the same screen

A picker is normal: six open time slots all going to `confirm`, three locked ones
all going to `blocked`; ten list rows all opening one detail view. The engine
looks a state up by id and nothing carries a payload, so **the destination cannot
know which one was clicked** — every path renders the same copy.

Write that screen as one representative example, and if the exact value matters
to the discussion, say so in the state's `instruction` so it appears in the rail
while you walk it:

```json
{ "id": "reschedule-blocked", "instruction": "Every locked-slot choice shows the same representative slot in this prototype." }
```

Do not split a picker into one state per option to work around this. Ten
near-identical states make the flow unreadable, which is the one thing the
artifact exists to prevent.

### A navigation step can also have its own actions

`scope: "shell"` opens the surrounding navigation. When that navigation is the
only action, the engine uses the sole routed link as the one spotlight and leaves
the page context dimmed; an uncovered but inert context region would falsely look
clickable. A list screen may still do both — the left nav is live *and* a row has
a `data-goto` button into the next step. Both routes are then declared transitions
from that state, and every exposed focus is operable.

## Product shell and navigation

```html
<nav class="sketch-card shell-nav product-context" aria-label="Product navigation">
  <button class="shell-link" type="button" data-nav="notes">My notes</button>
  <button class="shell-link" type="button" data-nav="settings">Account settings</button>
</nav>
```

The shell is shared by every state and every flow, so a nav item cannot name a
target state. It carries a stable key; each state's `navTargets` decides where
that key leads for that step. A key a state does not route simply does nothing.

- Keys must be unique within the shell.
- `data-nav` belongs to the shell only — never to a state view or the rail.
- Only a `data-nav` element the current state routes becomes clickable, and only
  while the state says `scope: "shell"`. Nothing else in the shell ever receives
  pointer events, so future chrome cannot become silently interactive.

### How the mask is built

Each state declares one stable `spotlight` key or two to three `spotlights`, and
its template marks exactly one wrapper for each matching `data-spotlight`. One
region uses four fixed panes. Multiple regions use engine-generated rectangular
panes that cover the exact space outside every hole; the area between separated
regions stays dimmed and inert. Each region receives its own amber ring. A
navigation-only shell step instead focuses the sole routed navigation control.
Additional routed navigation is lifted above the panes at `z-index: 21` only when
the page also contains a declared action.

Two things follow, and both have bitten:

- **Focus the current decision, not the page.** Use the smallest wrapper that
  contains the context and every action needed on this step. When separated
  regions must be compared, declare two or three rather than one oversized box.
  A card row, form
  section, age gate, confirmation panel, or changed record are credible targets;
  the entire state root is usually not. Every `data-goto` must sit inside it.
- **Never style `#interaction-mask`, `.mask-pane`, `.spotlight-ring`, or `#spotlight-ring` in
  product CSS.** Their paint and geometry belong to the generic engine. Likewise,
  do not override the viewport's `position` or `z-index`.
- **Never put `filter` or `opacity` on `.product-context`** to grey the chrome.
  Either one opens a stacking context, and a descendant cannot escape its
  ancestor's filter — the punched-through links get trapped back underneath.
- **The mask panes block pointer events.** Declared holes and routed shell links
  are the only live product regions. Open the file and verify every hole still
  tracks its target after resize and scroll.
- The navigation a flow depends on must remain reachable at every width. Do not
  hide `.shell-nav` at a breakpoint — a flow that cannot be completed on a narrow
  screen is a broken flow that the validator cannot see.

## What must never appear in a state view

Rail vocabulary, because it belongs to the person driving, not the product:
`reset flow`, `restart flow`, `restart test`, `simulate error`,
`error simulation`, `hypothesis`, `observer guide`, `observer hud`,
`participant task`, `validation flow`, `test plan`, `telemetry`, `event log`,
`facilitator`.

The list is narrow on purpose — `Reset password` is ordinary
product copy and pass. If your product genuinely needs one of these words, rename
the rail control rather than the product screen, or extend the list in
`scripts/validate_flow_spec.py`.

`data-jump` is likewise rail-only: a product screen must never offer a way to
skip ahead. A terminal state ends with a credible product continuation.

## The route map is navigation

The stepper shows the shape of the journey and where the walker currently is.
Every row is a `data-jump` button that immediately renders that state, regardless
of the declared transitions. This makes screen comparison and non-linear client
discussion fast. It does not modify `flow.json`, mark a transition as valid, or
replace walking each branch through product actions before handoff.

The complete route map is open by default, and its highlighted node is the only
current-position indicator. Do not add a duplicate current-step card or progress
counter. Entry preconditions and secondary current-state review points use native
disclosures; their existence remains visible without their full text occupying
the rail continuously.

The rail has exactly one fixed button at its top: `Restart`. Its remaining
controls are the flow selector, Purpose and Entry disclosures, the route map,
and the selected state's facilitator note. A technical failure that needs to be
walked is a separate complete flow with its own entry and scenario.

## Agent-mediated review changes

The review ledger is agent-facing data in `flow.json`, not a browser panel.
`walkthrough.md` tells the facilitator when to raise its questions. People give
corrections to the agent in conversation.
The agent then updates `flow.json` and affected state views together, validates
the artifact, and restarts every affected branch from entry. The runtime never
mutates the embedded specification or implies that spoken feedback is already
implemented.

## Language

Write the artifact in the language of the product and the people in the room.
The rail reads `task` and `instruction` from `flow.json`, so they follow the same
language as the screens.

## Fidelity and scope

- Sketchbook language: Patrick Hand with Comic Neue fallback, dotted graph-paper
  canvas, wobbly `255px 15px 225px 15px / 15px 225px 15px 255px` borders, native
  buttons. Never below 13px. Low fidelity is deliberate: it keeps the
  conversation on the flow instead of the styling.
- Deterministic mock data held in the markup. No backend, build step, network
  call, or analytics. The file must open directly from disk; Google Fonts is the
  only permitted remote reference and the page must stay legible without it.
- Everything outside the flow stays static, so the discussion stays on the one
  journey the artifact exists to settle.
- Every outcome ends on a screen showing what changed, not on a screen the walker
  already passed. See [the flow contract](flow-contract.md) on outcomes.
