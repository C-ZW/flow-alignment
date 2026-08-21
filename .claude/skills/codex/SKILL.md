---
name: codex
description: >
  Consult the codex CLI (gpt-5.6-sol, read-only sandbox) as an independent ADVISOR
  and REVIEWER whenever you are NOT highly confident — before you commit to a plan or
  a conclusion. Two roles: ADVISE (second opinion before acting — vet a plan/approach/
  decision, or answer something you don't actually know) and REVIEW (check something
  that already exists — a result that contradicts what you expected, a diff, a doc, a
  claim). codex reads files ITSELF by path (never paste file bodies into the prompt)
  and runs read-only so it can advise/review but physically cannot implement or edit.
  Self-invoke any time confidence < high, regardless of stakes. Triggers: 「問一下 codex」,
  「讓 codex 覆核 / 看一下這個計畫」,「codex review」,「找 codex 當第二意見」. NEVER ask codex to
  write or apply code — it advises, YOU decide and implement. Skip it only for work you
  are already confident in.
---

# codex: independent advisor & reviewer (read-only, never implements)

A second brain you consult through the local `codex` CLI. It is **advisory only** —
enforced at the CLI by `-s read-only` (it can read any file by path and run read
commands, but cannot write, edit, or apply anything). You keep ownership: codex gives
a verdict, **you** decide and do the work.

Smoke-tested working: `codex exec -m gpt-5.6-sol -s read-only` reads a repo file by
path and returns a clean verdict in ~10s (`codex-cli 0.144.6`, this repo is a trusted
codex project). Do NOT invoke `codex` interactively, `codex apply`, `--sandbox
workspace-write`, or `--dangerously-*` — those break the read-only guarantee.

## 1. When to consult (proactive — confidence < high ⇒ ask)

Reach for codex on your OWN initiative, before you commit, whenever you are not
highly confident. The two roles:

- **ADVISE — before acting.** You're about to commit to a plan/approach/design and
  aren't sure it's right; a non-trivial decision has a real fork; you'd otherwise be
  *guessing*; you genuinely don't know the answer to something. → get a second opinion
  FIRST, then proceed. **Give codex the owner's ORIGINAL request verbatim** (§4.1), so
  it weighs the approach against the real goal — not against your framing of it.
- **REVIEW — after something exists.** A result contradicts what you expected; you
  produced a plan/doc/diff/analysis and want an adversarial read before it ships or
  before the owner sees it; you made a factual/API/number claim you're not certain of.
  → have codex review it, reconcile, then finalize. **Always give codex the owner's
  ORIGINAL request verbatim** (§4.1), so it judges the work against the real intent —
  not against your restatement, which carries your bias.

The bar is **confidence, not stakes** — if you're about to write "probably" or "I
think" or move on with a quiet doubt, that doubt IS the trigger. This sits alongside
the repo's internal-iteration rule: use codex to raise your own confidence before the
owner reviews (owner review = taste, not defect-catching).

**Structural trigger — rules/mechanisms/process changes**: any NEW or changed rule,
mechanism, policy, service level, gate, or template you author gets a codex REVIEW
pass **automatically, before adoption** — do NOT gate this class on your own
confidence. You designed it, so your confidence in it is systematically inflated
and the confidence trigger never fires; that is exactly the blind spot this trigger
exists to cover. Urgent changes may land first, but the review follows immediately
and is not optional (the owner may explicitly waive a case).

**The structural trigger covers SEMANTIC VERIFICATION DESIGN, not only what you
decide.** This is the half that gets missed, and missing it is expensive. A prompt
you write for a subagent or a workflow is not a neutral container: it specifies
**what property is being demonstrated, by what method, and what counts as proof**.
A prompt that names the wrong method produces a wrong number carrying the full
authority of a measurement — and a verification instruction that cannot surface a
defect looks exactly like a verification that found nothing.

IN SCOPE, reviewed **before the work runs**:

- **workflow scripts and subagent prompts** — but only where they define semantics:
  the acceptance criteria, the measurement method, the verdict vocabulary, and what
  the agent is told counts as evidence. Routine task framing, tone and logistics are
  not in scope.
- **exit and stopping conditions** — "hunt until N clean rounds", round caps, budget
  caps. Ask specifically what a clean result would *prove*. In this project the
  "two consecutive dry rounds" gate was never met across P9/P9b/P9c and cost ~12M
  tokens over 8 rounds; it was **unsuitable as evidence of completeness** against a
  self-contradictory spec — note it could still have returned dry for the wrong
  reasons (hunters missing, scope narrowing), which is precisely why it proved
  nothing either way.
- **how findings are passed between agents** — a defect list truncated inline
  (`slice(0, 4000)`) once meant 14 of 16 confirmed defects went unfixed while every
  gate stayed green.
- **checks and thresholds you author, and check repairs that change semantics.**
  A check is policy in executable form: fixing one can mean deciding what property
  it proves, against what reference, with what tolerance, and whether failing it
  blocks. A docstring records what its author once intended, not what has been
  adopted — this project has a measured case (`_pole_side_check`) whose docstring
  claimed a flipped pole reads red while the IK mechanism forces the relation
  positive, so the docstring itself encoded the wrong model.

**EXEMPT — mechanically semantics-preserving repairs**, which may proceed without a
review round-trip when **all five** hold:

1. the intended property and its authority are already explicit and reviewed;
2. no threshold, tolerance, reference, severity, blocking status or scope changes;
3. the repair has exactly one semantics-preserving interpretation;
4. a mutation or negative control shows the old check missed the named defect and
   the repaired one catches it;
5. existing valid cases stay green.

Qualifying examples: replacing a self-comparison with the independent value the
design already specifies; replacing a literal `True` with an already-defined
predicate, or relabelling it `skipped` where the adopted vocabulary already requires
that; closing a case-sensitivity hole where the binding rule already states the
comparison is case-insensitive.

Still requires review: deciding *what* the independent reference should be,
inventing a predicate behind a literal `True`, expanding what is forbidden, setting
a tolerance, or deciding whether failure blocks. **"Obviously broken" proves the old
check invalid; it does not always determine the replacement.**

**The non-recursive root.** This rule would otherwise require reviewing the prompts
used to conduct reviews, including this one. The root is fixed: **a review prompt is
exempt when it only asks for judgement and names files by path**. It becomes in
scope the moment it asserts findings, supplies numbers, or tells the reviewer what
to conclude — because that is where it can lead the witness. Keep review prompts
question-shaped and they stay outside the recursion.

**What a review can and cannot establish.** Codex reads files and reasons; in this
project it cannot run Blender or the rig. So it can review the method, the scripts,
the provenance, the internal consistency and whether conclusions follow — it **cannot
certify that a measurement is true**. Record a measurement as independently verified
only when the reviewer actually ran the stated reproduction; otherwise the verdict is
"method and reasoning reviewed, measurement not reproduced."

**A review's own quality contract**: map material findings to evidence; distinguish
observed from inferred from unverified; state what could not be inspected or
reproduced; and on a re-review, check that earlier material findings were *answered*,
not merely that the text changed. Where two advisors disagree, resolve factual
disagreement against primary evidence first (§5); an irreducible *policy* disagreement
goes to the owner with both positions and the consequence of each.

The honest test for the in-scope class: *if this instruction were subtly wrong, would
anything downstream reveal it, or would it simply produce confident numbers?*

**One-time backfill**: the verification methodology already in use predates this
rule and was never reviewed. It is recorded at
`canonical-rig/design/VERIFICATION-METHODOLOGY.md` and is under review now; until
that closes, treat measurements produced by it as method-unreviewed.

## 2. When NOT to consult

- **You're already highly confident** — don't burn a call to rubber-stamp settled
  work. This is a doubt-resolver, not a ritual.
- **Trivial / mechanical / fully-verified** edits, or anything a `sd verify` /
  typecheck / test already proves. Codex is for judgement, not for what a gate checks.
- **Anything requiring implementation.** codex NEVER writes code. If the answer is "do
  X", you do X. Do not ask it to produce a patch, and never `codex apply` its output.
- **Secrets / private tokens in the prompt.** Never (see repo memory: OAuth tokens).

## 3. The call (exact form)

```bash
codex exec -m gpt-5.6-sol -s read-only \
  -C "$(git rev-parse --show-toplevel)" \
  -o <scratchpad>/codex-<topic>.md \
  "<advisory/review prompt — reference files by PATH, do NOT paste file bodies>"
```

- **`-m gpt-5.6-sol`** — the default model (config default, `medium` reasoning; leave
  effort at config unless a call is genuinely hard, then add
  `-c model_reasoning_effort=high`). Owner may name a different model per call.
- **`-s read-only`** — non-negotiable. This is what makes codex an advisor, not an
  actor. Never raise it.
- **`-C <repo root>`** — run from the repo root so codex can open repo files by
  relative path. This repo is already a trusted codex project.
- **`-o <file>`** — write codex's final verdict to a scratchpad file, then read that
  (clean, no transcript noise). Use your **session scratchpad directory** (the absolute
  path is given in your system prompt — it is session-specific, never hardcode it) with
  a short descriptive name, e.g. `<scratchpad>/codex-<topic>.md` where `<topic>` is a
  slug for what you're asking about (`plan-scene3`, `graph-invariant`, …).
- **File paths, never file text (hard rule).** Codex reads files itself. Put PATHS in
  the prompt (`docs/PLAN-foo.md`, `src/core/graph.ts`, a diff written to a temp file);
  do NOT inline whole file contents. For a diff, write it to a temp file
  (`git diff > <scratchpad>/x.diff`) and give codex that path. For files outside the
  repo, use an absolute path (add `--add-dir <dir>` if codex reports it can't read it).
- **Append `< /dev/null` when running in background**: without it, a backgrounded
  `codex exec` hangs forever on "Reading additional input from stdin...". Foreground
  interactive shells don't need it, but background Bash tasks ALWAYS do.

## 4. Writing the prompt

Make it a focused judgement request, not an open task:

1. **Anchor to the owner's ORIGINAL request — verbatim (the bias guard).** Include the
   owner's actual words for what they asked, quoted, in BOTH roles (advise and review).
   Do NOT hand codex only your own summary/framing of the task: if codex sees just your
   interpretation, it inherits your misreadings and blind spots and can only check "does
   this match Claude's plan", never "does this match what the owner asked". Giving it
   the real intent is what makes the second opinion independent instead of an echo of
   yours. The request is the SPEC, not a file body — include it as text (this is the one
   thing you quote, not path-reference); if the requirement also lives in a doc/brief,
   give that path too. Then frame the ask, e.g. "Here is what the owner asked: «…». I
   plan to do / I produced <the artifact, by path>. Judge it against the owner's intent."
2. **State the role + the ask in one line** — "Review this plan for correctness and
   gaps" / "Advise: is approach A or B sounder here, and why" / "I expected X but got
   Y — what am I missing".
3. **Give paths to read**, and say *what to look at* in each ("the schema is
   `src/types.ts`; the invariants are in `tests/graph-invariants.test.ts`").
4. **Ask for a verdict**, not a rewrite — e.g. "List concrete problems ranked by
   severity; if you'd do it differently, say the delta in prose. Do NOT write code or
   propose a patch — advice only."
5. **Pin the output shape** when useful: "End with one line: SOUND / SOUND-WITH-FIXES
   / RETHINK." For a machine-readable verdict, `--output-schema <file.json>`.
6. If the question itself is ambiguous, **ask the owner to clarify scope BEFORE**
   spending a codex call — a vague prompt yields a vague verdict.

## 5. Consuming the verdict

Codex is a **second opinion, not an oracle** — reconcile, don't obey.

- Read the captured verdict. Where it agrees, confidence rises. Where it disagrees,
  figure out who's right (re-check the code/facts) rather than defaulting to either
  side — codex can be confidently wrong, and so can you.
- If codex surfaces a real problem, fix it yourself (never let codex implement), then
  optionally re-run a REVIEW pass on the fix.
- **Record it** per repo discipline: note in `projects/<slug>/journal.md` (or the
  relevant plan/report doc) that codex was consulted, the verdict in one line, and what
  you did with it. This keeps the "why" auditable like any other decision.
- Relay to the owner only what matters (the verdict + your decision), not the raw
  transcript — same as any delegated agent's output.

## 6. Guardrails (do not cross)

- **Read-only, always.** Never `-s workspace-write` / `danger-full-access` /
  `--dangerously-bypass-*`, never `codex apply`, never the interactive TUI. The moment
  codex could write, it stops being an advisor.
- **codex advises; you implement.** No exceptions.
- **Paths in, not file bodies.** (§3)
- **No secrets in prompts.**
- **Confidence-gated, not reflexive.** Consult when unsure; skip when sure.
