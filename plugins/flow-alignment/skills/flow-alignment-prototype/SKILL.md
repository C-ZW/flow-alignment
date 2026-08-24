---
name: flow-alignment-prototype
description: Build a clickable, low-fidelity flow artifact so the people responsible for a journey can walk it from the real starting point, correct mismatched assumptions, and settle what remains undecided before design or engineering commits. Use when turning a proposed flow, feature idea, or researched website journey into a navigable alignment wireframe, including a reference-shaped wireframe that preserves evidence-backed structure without cloning protected assets. It is not a product-introduction or sales-demo skill. Triggers on "confirm the flow", "align the journey", "review with the client", "flow walkthrough", "clickable prototype", "wireframe prototype", "prototype this flow", or "validate this flow".
---

# Flow Alignment Prototype

Build one standalone browser artifact that the people responsible for a journey
walk together, so the room can answer: **are we describing the same flow, which
claims are wrong, and what have we not decided yet?** The driver facilitates the
walk; they do not introduce or pitch the product. Prefer a believable journey and
honest branches over visual polish or product coverage.

The promise is not “this design is good.” It is “we are now discussing the same complete, concrete journey.”

## What a good artifact does

- **Starts at the beginning.** From where a real user is actually standing,
  through the real navigation, to the screen under discussion. It never opens on
  that screen — getting there is part of what is being confirmed. The artifact
  also says *why* it starts there and on whose authority, because that is a claim
  someone in the room may need to correct.
- **Shows every branch.** When a step has alternative outcomes, they are visible
  as alternatives, and each one lands somewhere real. "What if they say no?" is
  the most common question in the room; the artifact answers it in one click.
- **Ends on what changed.** Each outcome says what happened and shows the product
  afterwards — not the screen the walker already passed, which would quietly undo
  the result in front of everyone.
- **Says what is still open.** The review ledger keeps unsettled questions in the
  validated specification, and `walkthrough.md` tells the facilitator when to ask
  them. The browser rail stays focused on navigation rather than rendering the ledger.
- **Is concrete enough to contradict.** Use product language, plausible data,
  and plausible context so domain owners can point to a wrong step, branch, or
  postcondition. This is discussion material, not product-introduction copy.

It does not establish usability metrics, product-market fit, visual design, or
feasibility. Do not report those.

## Required outputs

Write only under `prototypes/<flow-name>/`:

| File | Purpose |
| --- | --- |
| `flow.json` | Source of truth: entry, focus, review ledger, steps, transitions, navigation, outcomes |
| `prototype.html` | Standalone view layer that embeds the same specification |
| `walkthrough.md` | The order to walk it in, and what to watch for |
| `adaptation.json` | Only when adapting a `website-flow-reference` artifact |
| `authoring/` | Product shell, state-view, and product-CSS fragments used to build the HTML |

Never write generated artifacts under `.claude/skills/`.

## Workflow

1. **Find the beginning.** Not the feature — the moment before it. Where is the
   person standing, what have they already done, and what is this journey going
   to skip? Write that down as `entry`: the state, the reason, whether it was
   observed, provided by the client, or assumed by you, and the preconditions you
   are leaving out. If you cannot infer it safely, ask one concise question.
2. **Name the focus.** Which screens is this meeting actually about? Everything
   between the entry point and the focus is the navigation the walkthrough tests
   as much as the destination. The entry state may not be a focus state — that is
   the rule “do not skip directly to the discussion screen,” made checkable.
3. **Model it** in `flow.json` following [the flow contract](references/flow-contract.md).
   Give every branch an outcome, and give every outcome a screen showing what it
   changed.
4. **Fill in the review ledger.** Take a position on all five: entry point,
   navigation, branches, failure and recovery, ending state. `open` is a valid
   position and usually the honest one. Leaving an aspect out is not — the
   validator rejects it, because silence in a meeting reads as agreement.
5. **Choose the adaptation mode when research is provided.** Use `wireframe` when
   the request is about the journey and the source is only behavioral context.
   Use `visual-reference` when the user asks for a wireframe that resembles,
   follows, or is shaped like the reference site. In that mode, read the
   screenshot evidence and IA before drawing, then declare the evidence-backed
   layout map required by the adaptation contract.
   First map the reference entry and each observed journey step to prototype
   states. The map audits behavioral alignment; it is not a prompt to make the
   journey longer. If the observed route lands on a list, article body, signup
   boundary, or other destination, that destination may be terminal. Never add a
   synthetic confirmation click merely to manufacture a postcondition. Proposed
   extra behavior is a separately declared proposal or alternative flow, not
   source behavior.
6. **Initialize product-owned fragments, then build.** Read
   [the prototype architecture](references/prototype-architecture.md), then run:

   ```bash
   python3 .claude/skills/flow-alignment-prototype/scripts/build_prototype.py \
     prototypes/<flow-name> --init
   ```

   `--init` creates only the three files under `authoring/`; it deliberately
   does not invent `flow.json` or `walkthrough.md`.
   Edit `flow.json`, `authoring/product-shell.html`,
   `authoring/state-views.html`, and `authoring/product.css`; then run the same
   command without `--init` to generate `prototype.html`. Never edit
   `prototype.html` directly. The builder owns every generic byte and makes
   engine drift impossible in the normal authoring path. Do not load the full
   template or generated HTML into model context unless a failing validator or
   browser check requires debugging it; work in the much smaller fragments.
7. **Write the screens** in product language, with data specific enough to be
   wrong. `$199/month · next billing date 2026-09-21` invites a correction;
   `[Price]` does not.
8. **Write `walkthrough.md`** as an alignment guide: the order to walk, the claim
   to pause on before each click, and the question the room must settle. Do not
   write a product talk track, feature pitch, or scripted introduction. Every
   open question belongs in the ledger in `flow.json`, not only here — a question
   that lives only in Markdown is a second, unvalidated copy of the flow.
   End the guide by summarizing corrections for the agent. The browser rail is
   read-only and does not collect meeting data.
9. **Build, check, then validate.** Regenerate from product-owned fragments and
   require both the authoring match and generic-wrapper check before validators:

   ```bash
   python3 .claude/skills/flow-alignment-prototype/scripts/build_prototype.py \
     prototypes/<flow-name>
   python3 .claude/skills/flow-alignment-prototype/scripts/build_prototype.py \
     prototypes/<flow-name> --check
   python3 .claude/skills/flow-alignment-prototype/scripts/sync_prototype_wrapper.py \
     prototypes/<flow-name>/prototype.html --check
   python3 .claude/skills/flow-alignment-prototype/scripts/validate_flow_spec.py \
     prototypes/<flow-name>/flow.json prototypes/<flow-name>/prototype.html
   ```

   For the final deterministic gate, use one command. It checks required files,
   wrapper drift, the flow, and any website reference/adaptation it discovers:

   ```bash
   python3 .claude/skills/flow-alignment-prototype/scripts/validate_handoff.py \
     prototypes/<flow-name>
   ```

   Add `--require-preview` only when the user or containing repository requires a
   README/demo preview. The script derives the reference from `adaptation.json`;
   use `--reference references/<site-key>/reference.json` to require a specific
   research handoff. Add `--runtime` to include the optional Playwright browser
   audit. Run individual validators above when diagnosing a failure.

   Errors block handoff. Warnings are judgement calls — resolve or explain them.
10. **Audit it in a browser and walk every branch from the entry point**, including the
   navigation steps and every modeled failure/recovery flow. The route map may jump directly to any state
   for discussion, but that does not verify the transitions into it; perform one
   complete product-action walk per branch before handoff. The validator checks the graph; only you can see whether the screen
   reads like the product. Smoke-check at `1440×1000` and `390×844` in fresh
   browser profiles. At both widths confirm there is no horizontal overflow, the
   rail does not hide the current product action or outcome, every
   spotlight ring tracks after scroll and resize, and the final screen visibly
   shows its postcondition. Record the final URL/hash when the source journey is
   client-routed. When Python Playwright is available, mechanize the repeated
   checks first:

   ```bash
   python3 .claude/skills/flow-alignment-prototype/scripts/audit_runtime.py \
     prototypes/<flow-name>
   ```

   This runner-neutral script walks every declared transition and route-map jump
   at both required widths, exercises Restart, and checks action reachability,
   horizontal overflow, mask and spotlight geometry, and browser errors. If
   Playwright is unavailable, follow its installation hint or perform the same
   checks manually. Its pass does not judge whether the screen reads like the
   product, whether a reference-shaped wireframe preserves the right hierarchy,
   or whether the declaration omitted a real branch; a person still inspects
   those claims.

11. **Apply a completion gate.** Before reporting success, verify that every
    required file in the output table exists and is non-empty, both wrapper
    checks and validators pass, and the browser walk above is complete. A preview
    screenshot is required only when the user or containing repository asks for
    one. If browser automation stalls, stop that run and retry only the smallest
    unfinished smoke check; do not expand the artifact or report completion.
    When the check still cannot finish, preserve the files and report the exact
    unfinished gate as a blocker.

The template's Content-Security-Policy is a runtime boundary, not movable
metadata. Keep it inside `<head>` before every base, link, style, script, or
refresh directive so it applies before anything can load or execute.

## Reference-shaped wireframes

`visual-reference` changes the product canvas, not the observer rail or generic
engine. It is for requests such as “make a wireframe shaped like the reference website.” Before writing
HTML, turn the cited screenshots and IA into a small layout map:

- product shell orientation and navigation placement;
- section order and relative proportions;
- repeated-component shape and density at the captured viewport;
- responsive reflow that was actually observed.

Record that map in `adaptation.json.visualReference`, then implement it in the
product shell, state views, and product-specific CSS after the marker. A source
with a horizontal media header and a dense six-card timeline must not silently
become a generic sidebar dashboard with one card. Likewise, do not invent an
extra navigation page merely to make the flow longer when the observed entry
links directly to the destination.

Preserve the structural silhouette and information scent with neutral
placeholders. Abstract logos, licensed imagery, brand decoration, long protected
copy, ads, and exact pixel values. When a state or breakpoint lacks screenshot
evidence, label its layout as adapted in assumptions and keep the uncertainty in
the review ledger where it affects the flow.

Before handoff, render the source screenshot and prototype at the same viewport
and compare structure, not pixels: chrome orientation, region order, dominant
area proportions, repeated-item count, and mobile reflow. A validator cannot see
that a technically valid file fell back to the wrong product archetype.

## The flow navigator

The left rail is tooling, not product. It contains `Restart`, the flow selector,
collapsed Purpose and Entry disclosures, the expanded branch-aware route map,
and the collapsible facilitator note for the selected state. `Restart` is its
only fixed button;
its highlighted node is the current position, so do not repeat that state in a
separate current-step card or add progress counts. Purpose and entry stay
collapsed until the room needs them.

- **Every step is a jump control.** The route map is also a screen index: selecting
  any node immediately renders that state. This is for comparing and discussing
  screens; it does not change the declared transition graph or prove the skipped
  route works.
- **Branches are shown as branches.** Steps sharing a number are drawn as
  alternatives under one node in the expandable route map, and the validator
  checks that against the graph. The active node is the current-position indicator.
- **The ledger remains agent-facing.** Review items stay in `flow.json`, and the
  facilitator-facing questions stay in `walkthrough.md`.
- **The room answers through the agent, not a form.** The browser rail is
  read-only: no reviewer field, confirm button, feedback editor, draft state, or
  export control. The agent receives corrections conversationally, updates
  `flow.json` and affected views deliberately, validates, and re-walks the
  branch. Never report a requested change as implemented before that work is
  complete.
- **Structured records are optional agent input.** If an external workflow
  already provides review JSON, read the
  [review application contract](references/review-application-contract.md) and
  use `scripts/apply_review_session.py` plan-first. The browser artifact does not
  create that file.
- The rail never contains product actions, and a product screen never contains
  rail controls — `data-jump` is rail navigation, `data-goto` is the product, and
  `data-nav` is product-shell navigation.

## Complete journeys, and when the shell is live

A state declares `scope`:

- `viewport` (default) — the state's declared `spotlight`, or the two or three
  regions in `spotlights`, are the only holes in the mask and are ringed in
  amber. The surrounding page and shell are covered and inert.
- `shell` — the mask stays. When routed navigation is the only action, that one
  navigation control is the single spotlight and the page context remains
  dimmed. If the page also contains a declared `data-goto` action, its spotlight
  keeps the hole without the ring and routed navigation is punched through
  beside it, so every exposed focus is actually operable.

Everything the step does not use stays under the mask, including chrome that
leads somewhere in other steps. That does tell the room where the next action
is — which is the trade this project accepts, because a walkthrough that stalls
on a dead link is spending the meeting on the prototype instead of the flow. If
you need to ask “can the user find it?”, ask it before you click, not from the
picture.

Every state should name the smallest coherent action, decision, or result region
with `spotlight`, and its template marks that wrapper with the matching
`data-spotlight`. When understanding the same step requires separated evidence
(for example a result list and its map marker), use `spotlights` with two or
three keys; do not enlarge one wrapper to include unrelated content. Put every
`data-goto` for that step inside one of the declared regions. A navigation-only
shell step may use that wrapper for context, but the engine focuses the sole live
`data-nav` control instead; never show an uncovered content region that cannot be
acted on. Do not mark the whole screen merely because it is convenient: the mask
exists to direct the room's attention, not to frame the browser. Product CSS must
not style the generic mask elements or change the viewport's `position` or
`z-index`.

Navigation is wired by stable keys: shell links carry `data-nav="settings"`, and
each state's `navTargets` says which keys lead where. One shared shell therefore
serves every flow and every step. See [the flow contract](references/flow-contract.md).

## Scope rules

- One flow, one journey. An artifact may carry up to three flows of the same
  product so a single meeting covers several related journeys; the rail switches
  between them. The validator rejects more than three.
- **A design alternative is a second flow, not a second button.** If the team is
  choosing between two ways a screen could work, build both, each complete from
  its own entry point, and link them from the ledger with `alternativeFlows`.
  Claiming in `walkthrough.md` that the client should "see both options" while
  building one is the failure mode this rule exists to stop.
- **A breakpoint-specific action graph is also a second flow.** If narrow and
  wide layouts change only placement, keep one flow. If they change click count,
  available actions, or destination order, build each complete journey from its
  true entry and link it with `responsiveAlternatives`; never hide a mobile menu
  step in preconditions or invent that click on desktop.
- Deterministic local state only: no backend, auth, analytics, build step, or
  external API. The file must open straight from disk.
- Session decisions are agent input, not browser runtime state. After feedback,
  deliberately update the source specification and screens, then validate and
  re-walk the affected branches.
- Include the navigation that makes the path real; leave the rest of the product
  static so the discussion stays on this flow.
- A reference-derived alignment flow preserves the observed click count and
  destination order. It may stop at an observed research boundary with
  `outcome.continuation: null`; state that nothing was submitted or changed when
  that is the honest postcondition. Do not invent another product action to
  satisfy the artifact's graph shape.
- Add a failure when it is part of what needs confirming — as a declared state
  with a declared trigger and a way out. When there is none, say `not-applicable`
  in the ledger with a reason. Absence is not evidence anyone considered it.

## Optional: running a participant session

The same artifact works for a moderated session. `hypothesis` and
`successSignal` are optional fields; fill them in when a session needs a stated
question and signal, and include both in `walkthrough.md`. Leave them out when
the flow is being confirmed internally or with a client.

Never report a usability result before a session with a participant has happened.

## What this cannot check for you

The validator proves that the declared journey is structurally complete and
internally consistent. It cannot prove runtime walkability, that the entry point
is right, that the real product has no omitted step, or that every branch was
discovered. Browser-walk every branch, then put the remaining claims where a
person can contradict them — that is the whole mechanism.

## Resources

- [Flow contract](references/flow-contract.md) — `flow.json` shape and rules
- [Prototype architecture](references/prototype-architecture.md) — regions, screens, navigation, what you edit
- [Website adaptation contract](references/website-adaptation-contract.md) — evidence handoff
- [Review application contract](references/review-application-contract.md) — optional external record → plan → safe apply / agent work
- `assets/prototype-template.html` — canonical generic source consumed by the builder
- `scripts/apply_review_session.py` — optional agent-side review plan and narrow safe-confirmation updater
- `scripts/validate_flow_spec.py` — graph and view-layer validator
- `scripts/validate_adaptation.py` — website handoff validator
- `scripts/validate_handoff.py` — portable one-command completion gate
- `scripts/audit_runtime.py` — optional Playwright walk of runtime mechanics
- `scripts/build_prototype.py` — assemble generic markup from product-owned fragments
- `scripts/sync_prototype_wrapper.py` — restore and verify generic template regions
