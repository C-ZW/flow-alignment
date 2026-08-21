---
name: flow-validation-prototype
description: Build a clickable, low-fidelity prototype of a proposed product flow so a team — and their client — can walk it end to end and confirm it is complete and correct before design or engineering commits. Use when turning a proposed flow, a feature idea, or a researched website journey into a navigable wireframe with a flow navigator, real in-product navigation, deterministic mock data, and a machine-validated state graph. Triggers on "確認流程", "跟客戶確認", "flow walkthrough", "clickable prototype", "wireframe prototype", "prototype this flow", "validate this flow".
---

# Flow Validation Prototype

Build one standalone browser artifact that a team can walk end to end, and then
walk a client through, to answer: **is this flow complete, and is it the flow we
want?** Prefer a believable journey and honest branches over visual polish or
product coverage.

## What a good artifact does

- **Walks completely.** From a believable entry point in the product, through the
  real navigation, to a natural outcome. It never opens directly on the screen
  under discussion — getting there is part of what is being confirmed.
- **Shows every branch.** When a step has alternative outcomes, they are visible
  as alternatives, and each one lands somewhere real. "What if they say no?" is
  the most common question in the room; the artifact should answer it in one click.
- **Reads as the product.** Product language, plausible data, plausible context.
  A client judges whether this matches their business, so the content has to be
  specific enough to argue with.
- **Presents.** It can be projected in a client meeting without internal notes on
  screen.

It does not establish usability metrics, product-market fit, visual design, or
feasibility. Do not report those.

## Required outputs

Write only under `prototypes/<flow-name>/`:

| File | Purpose |
| --- | --- |
| `flow.json` | Source of truth: flows, steps, transitions, navigation, notes |
| `prototype.html` | Standalone view layer that embeds the same specification |
| `walkthrough.md` | What to show, in what order, and the questions to settle |
| `adaptation.json` | Only when adapting a `website-flow-reference` artifact |

Never write generated artifacts under `.claude/skills/`.

## Workflow

1. **Establish the journey.** Where does a real user enter the product, what are
   they trying to do, and what are the outcomes? If the entry point or the
   outcomes are unclear and cannot be inferred safely, ask one concise question.
2. **Model it** in `flow.json` following [the flow contract](references/flow-contract.md).
   Include the navigation steps that get the user there — not every screen in the
   product, but enough that the path is real. Give every branch an outcome.
3. **Copy the template.** `assets/prototype-template.html` →
   `prototypes/<flow-name>/prototype.html`. Change three things and nothing else:
   the product shell, the `#flow-spec` JSON, and the `#state-views` templates.
   Read [the prototype architecture](references/prototype-architecture.md) first.
4. **Write the screens** in product language, with data specific enough to be
   wrong. `NT$199 / 月 · 下次扣款日 2026/09/21` invites a correction;
   `[Price]` does not.
5. **Write `walkthrough.md`**: the order to demo the flows, what to point at, the
   open questions this artifact exists to settle, and what it deliberately does
   not cover.
6. **Validate and fix.**

   ```bash
   python3 .claude/skills/flow-validation-prototype/scripts/validate_flow_spec.py \
     prototypes/<flow-name>/flow.json prototypes/<flow-name>/prototype.html
   ```

   Errors block handoff. Warnings are judgement calls — resolve or explain them.
7. **Open it and walk every branch yourself**, including the navigation steps and
   the error view. The validator checks the graph; only you can see whether the
   screen reads like the product.

## The flow navigator

The left rail is tooling, not product. It holds the flow selector, a
branch-aware step list where every step jumps straight to that screen, the note
for the current step, the scenario, an optional brief, and the reset, error, and
presentation controls.

- **Branches are shown as branches.** Steps sharing a number are drawn as
  alternatives under one node, not as consecutive steps.
- **`簡報` hides every internal note**, leaving the flow and its steps. Use it
  when the client is in the room.
- The rail never contains product actions, and a product screen never contains
  rail controls — `data-goto` is the product, `data-jump` is the rail.

## Complete journeys, and when the shell is live

A state declares `scope`:

- `viewport` (default) — the page under discussion is spotlit; the surrounding
  shell is dimmed and inert.
- `shell` — the whole app is bright and the declared navigation is clickable, so
  the walker genuinely navigates to the target instead of appearing there.

Navigation is wired by stable keys: shell links carry `data-nav="settings"`, and
each state's `navTargets` says which keys lead where. One shared shell therefore
serves every flow and every step. See [the flow contract](references/flow-contract.md).

## Scope rules

- One flow, one journey. An artifact may carry up to three flows of the same
  product so a single meeting covers several related journeys; the rail switches
  between them. Above three, the validator warns.
- Deterministic local state only: no backend, auth, analytics, build step, or
  external API. The file must open straight from disk.
- Include the navigation that makes the path real; leave the rest of the product
  static so the discussion stays on this flow.
- Add an error branch when the failure is part of what needs confirming.

## Optional: running a participant session

The same artifact works for a moderated session. `hypothesis` and
`successSignal` are optional fields; fill them in when a session needs a stated
question and a stated signal, and the rail will show them behind `Brief`. Leave
them out when the flow is being confirmed internally or with a client.

Never report a usability result before a session with a participant has happened.

## Resources

- [Flow contract](references/flow-contract.md) — `flow.json` shape and rules
- [Prototype architecture](references/prototype-architecture.md) — regions, screens, navigation, what you edit
- [Website adaptation contract](references/website-adaptation-contract.md) — evidence handoff
- `assets/prototype-template.html` — the generic engine; start every prototype here
- `scripts/validate_flow_spec.py` — graph and view-layer validator
- `scripts/validate_adaptation.py` — website handoff validator
