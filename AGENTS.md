# Working in this repository

This repo builds agent skills that produce clickable flow artifacts — the kind a
team walks end to end to confirm a proposed journey, and then walks a client
through. Read [PROJECT_GOALS.md](PROJECT_GOALS.md) first: it defines what an
artifact must prove and what it must not claim.

## The two skills

- `.claude/skills/flow-alignment-prototype/` — proposed or researched journey → clickable prototype
- `.claude/skills/website-flow-reference/` — public URL → evidence-backed research

These are the only skill entry points in this repository. A "high-fidelity
clone" or "pixel-perfect extraction" capability is outside the project scope:
claiming visual parity without evidence is an explicit non-goal.

The canonical skill sources remain under `.claude/skills/`. The Codex marketplace
package under `plugins/flow-alignment/skills/` is a distributable mirror, not a
third skill. After changing either canonical skill, run
`python3 scripts/sync_plugin_skills.py`; tests reject package drift.

## Rules that are not negotiable

1. **Output location.** Generated artifacts go to `prototypes/<flow-name>/` or
   `references/<site-key>/` at the repository root. Never write them under
   `.claude/skills/`, which holds skill definitions, templates, and scripts only.
2. **`flow.json` is the source of truth.** It declares flows, the entry point and
   its basis, the focus screens, each state's spotlight region, the review ledger, states, transitions, outcome
   postconditions and observer guidance. `prototype.html`
   embeds the same object and renders it. Never encode a transition only in
   markup or JavaScript. Review positions remain in the specification, while
   `walkthrough.md` tells the facilitator when to raise them.
3. **The engine and the design system are generic.** Use the prototype skill's
   `scripts/build_prototype.py`. Edit `flow.json` and only the product shell,
   state views, and product CSS under the artifact's `authoring/` directory;
   never edit generated `prototype.html` directly. The builder owns `#flow-spec`
   and every generic byte. Tests assert that both the engine block and everything
   in `<style>` before the product marker remain byte-identical to the template,
   so a fix to the rail or mask reaches every artifact or fails loudly.
4. **Tooling stays outside the product.** Restart is the rail's only fixed button
   and sits at its top. Flow selector, entry declaration, expanded clickable
   route map, step note, and scenario also belong there. A product screen
   containing any of them is a defect, not a style choice. `data-goto` is the
   product; `data-jump` and `data-nav` are not.
5. **Journeys start at the beginning.** `entry.state` is step 1 and may not be a
   `focus` state, so an artifact cannot open on the screen under discussion. The
   entry declaration also records *why* it starts there, on what basis, and what
   it skips. Every branch lands somewhere real, and every outcome continues to a
   screen showing what changed — never one the walker already passed, which shows
   the world before the action and undoes the result in front of the room.
6. **The route map jumps directly.** It is open by default, every state is
   selectable, and its highlighted node replaces a separate current-step card
   and progress count. A jump is for discussion and does not prove skipped edges;
   every branch still needs a complete product-action walk before handoff.
7. **Runs from disk.** No backend, build step, network call, analytics, or
   blocking dialog. Google Fonts is the only permitted remote reference.
8. **One flow, one journey.** An artifact may carry up to three flows of the
   same product for one meeting; each declares its own scenario. More than three
   and it stops being about anything in particular. `hypothesis` and
   `successSignal` are optional — fill them in only for a moderated participant
   session.
9. **A design alternative is a second flow.** Two competing ways a screen could
   work are not two buttons on one screen. Build both, each complete from its own
   entry point, and link them with `alternativeFlows`. Writing "the client should
   see both options" while building one is the failure this rule exists to stop.
10. **Nothing is settled by silence.** All five review aspects — entry point,
    navigation, branches, failure and recovery, ending state — need a stated
    position. `open` is a valid and usually honest one; leaving an aspect out is
    not, and the validator rejects it.
11. **Evidence discipline.** For website research, separate observed from
    inferred, record limitations, and never claim an interaction you did not see.
    Each journey step carries its own evidence, and gaps travel forward into the
    prototype's review ledger. Do not reuse third-party logos, images, or
    protected copy.
12. **Review changes are agent-mediated.** The browser has no Review interface;
    do not add confirmation, feedback, reviewer, draft, or export inputs. Take
    corrections through the agent, update `flow.json` and affected views
    deliberately, then validate and re-walk every affected branch from entry.

## Sketchbook visual language

Patrick Hand with a Comic Neue fallback, dotted graph-paper canvas
(`radial-gradient(#d4d4d8 1.2px, transparent 1.2px)`), wobbly borders
(`255px 15px 225px 15px / 15px 225px 15px 255px`), native `<button>` elements
with `.btn-sketch-primary` / `.btn-sketch-secondary` / `.btn-sketch-danger`.
Never below 13px. Low visual fidelity is deliberate: it keeps feedback on the
flow rather than the styling.

## Before handing anything over

```bash
python3 .claude/skills/flow-alignment-prototype/scripts/validate_flow_spec.py <flow.json> <prototype.html>
python3 -m unittest discover -s tests
```

Errors block handoff; warnings are judgement calls to resolve or explain. Then
open the file and walk every branch yourself. The validator checks structure —
only a person can check that the screen reads like a real product.

These artifacts show that the journey *as declared* is complete, and put its
claims where people can contradict them. They do not prove the declaration is
right — no static check knows about a branch nobody thought of — and they do not
measure users. Never report a usability result before a session with a
participant has happened.
