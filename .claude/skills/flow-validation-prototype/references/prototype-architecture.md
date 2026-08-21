# Prototype Architecture

`prototype.html` is a view layer over `flow.json`. It has four regions.

```
┌─ #observer-hud ─┬─ #app-shell ─────────────────────────────────┐
│ 流程 Flow       │  .product-context   product chrome           │
│ [flow ▾]        │   ┌─ #product-viewport ──────────────────┐   │
│                 │   │ the page the flow is on               │   │
│ 1. 我的筆記      │   │                                       │   │
│ 2. 帳戶設定      │   └───────────────────────────────────────┘   │
│ 3. 訂閱方案      │                                              │
│ 4. 取消前的選擇   │   scope: "viewport" → shell dimmed, masked   │
│ 5. 選擇暫停天數   │   scope: "shell"    → whole app live, no mask│
│ ├ 訂閱已暫停     │                                              │
│ └ 訂閱已取消     │   264px rail, sticky. Folds to a top bar     │
│                 │   below 900px.                                │
│ 這一步 …         │                                              │
│ 情境 …           │                                              │
│ [Brief][Err][↺][簡報] │                                        │
└─────────────────┴──────────────────────────────────────────────┘
  #state-views   <template data-flow data-state> per state
  #flow-spec     the exact contents of flow.json
```

## What you edit

Copy `assets/prototype-template.html`, then change exactly three things:

1. **The product shell** inside `#app-shell` — header and navigation for the real
   product. Keep `class="product-context"`; give each navigable item a stable
   `data-nav` key.
2. **`#flow-spec`** — paste the exact contents of `flow.json`.
3. **`#state-views`** — one `<template>` per state, holding real product markup.

Leave the engine `<script>` alone. It is generic: it reads the spec, renders the
rail, clones the matching template into the viewport, wires the shell navigation
for the current step, and refuses any transition the specification does not
declare. A test asserts it stays byte-identical across every prototype.

## State views

```html
<template data-flow="subscription-pause-offer" data-state="retention-offer">
  <p class="view-eyebrow">帳戶設定 / 訂閱方案 / 取消訂閱</p>
  <h1 class="view-title">在你取消之前,還有一個選擇</h1>
  <div class="offer-grid">
    <div class="offer-card">
      <h2>暫停訂閱</h2>
      <p>先暫停 1-3 個月,這段期間<strong>不會扣款</strong>。</p>
      <button class="btn-sketch-primary" type="button" data-goto="pause-duration">暫停訂閱</button>
    </div>
  </div>
</template>
```

- One base template per state; add `data-variant="error"` for the view shown
  while error simulation is on.
- Actions are `<button data-goto="…">`. No `onclick`, no `href`, no `alert()`.
- Every `data-goto` must be a declared transition **out of that state**, and
  every declared transition needs something that offers it — a button here, or a
  nav key routed by `navTargets`.
- Write product language and specific data. A client corrects
  `下次扣款日 2026/09/21`; they cannot correct `[Date]`.

### When several actions lead to the same screen

A picker is normal: six open time slots all going to `confirm`, three locked ones
all going to `blocked`; ten list rows all opening one detail view. The engine
looks a state up by id and nothing carries a payload, so **the destination cannot
know which one was clicked** — every path renders the same copy.

Write that screen as one representative example, and if the exact value matters
to the discussion, say so in the state's `instruction` so it appears in the rail
while you walk it:

```json
{ "id": "reschedule-blocked", "instruction": "不管點哪一個鎖定時段,畫面固定顯示同一個示範時段。" }
```

Do not split a picker into one state per option to work around this. Ten
near-identical states make the flow unreadable, which is the one thing the
artifact exists to prevent.

### A navigation step can also have its own actions

`scope: "shell"` opens the surrounding navigation; it does not mean the page is
inert. A list screen usually does both — the left nav is live *and* a row has a
`data-goto` button into the next step. Both routes are declared transitions from
that state, and the walker may take either.

## Product shell and navigation

```html
<nav class="sketch-card shell-nav product-context" aria-label="Product navigation">
  <button class="shell-link" type="button" data-nav="notes">我的筆記</button>
  <button class="shell-link" type="button" data-nav="settings">帳戶設定</button>
</nav>
```

The shell is shared by every state and every flow, so a nav item cannot name a
target state. It carries a stable key; each state's `navTargets` decides where
that key leads for that step. A key a state does not route simply does nothing.

- Keys must be unique within the shell.
- `data-nav` belongs to the shell only — never to a state view or the rail.
- Only elements carrying `data-nav` become clickable, and only while the state
  says `scope: "shell"`. Nothing else in the shell ever receives pointer events,
  so future chrome cannot become silently interactive.
- The navigation a flow depends on must remain reachable at every width. Do not
  hide `.shell-nav` at a breakpoint — a flow that cannot be completed on a narrow
  screen is a broken flow that the validator cannot see.

## What must never appear in a state view

Rail vocabulary, because it belongs to the person driving, not the product:
`reset flow`, `restart flow`, `restart test`, `simulate error`,
`error simulation`, `hypothesis`, `observer guide`, `observer hud`,
`participant task`, `validation flow`, `test plan`, `telemetry`, `event log`,
`facilitator` — and their Chinese equivalents: `重置流程`, `重新開始流程`,
`重啟流程`, `重新測試`, `模擬錯誤`, `錯誤模擬`, `驗證假說`, `驗證假設`,
`驗證流程`, `觀察者指引`, `測試任務`, `測試計畫`, `測試腳本`, `遙測`
(simplified variants included).

The list is narrow on purpose — `重設密碼` and `Reset password` are ordinary
product copy and pass. If your product genuinely needs one of these words, rename
the rail control rather than the product screen, or extend the list in
`scripts/validate_flow_spec.py`.

`data-jump` is likewise rail-only: a product screen must never offer a way to
skip ahead. A terminal state ends with a credible product continuation.

## Presenting

`簡報` hides every internal note in the rail — the step note, the scenario, the
brief — leaving the flow name and its steps. Use it when the client is in the
room; switch it off to discuss internally without reloading.

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
