# Flow Contract (`flow.json`, version 2)

`flow.json` is the single source of truth for the flow and for everything the
navigator rail shows. `prototype.html` embeds the same object and renders it; it
never holds flow logic the specification does not declare.

```json
{
  "version": 2,
  "flows": [
    {
      "id": "subscription-pause-offer",
      "title": "取消流程中的暫停選項",
      "task": "使用者接下來一兩個月不會用這個工具,不想被扣款,但也不想弄丟資料。",
      "initialState": "app-home",
      "errorSimulation": { "supported": false },
      "states": [
        {
          "id": "app-home",
          "title": "我的筆記",
          "step": 1,
          "scope": "shell",
          "navTargets": { "settings": "account-settings" },
          "instruction": "從產品首頁開始。讓走的人自己找進去。",
          "transitions": ["account-settings"]
        },
        {
          "id": "account-settings",
          "title": "帳戶設定",
          "step": 2,
          "scope": "shell",
          "navTargets": { "notes": "app-home" },
          "instruction": "訂閱方案在這一頁的哪個位置?",
          "transitions": ["subscription-plan", "app-home"]
        },
        {
          "id": "subscription-plan",
          "title": "訂閱方案",
          "step": 3,
          "instruction": "從這裡開始是這次要確認的區段。",
          "transitions": ["retention-offer"]
        },
        {
          "id": "retention-offer",
          "title": "取消前的選擇畫面",
          "step": 4,
          "instruction": "這是要確認的關鍵畫面:暫停與取消並排呈現。",
          "transitions": ["pause-duration", "cancel-confirmed", "subscription-plan"]
        },
        {
          "id": "pause-duration",
          "title": "選擇暫停天數",
          "step": 5,
          "instruction": "暫停長度與恢復日期。",
          "transitions": ["pause-confirmed", "retention-offer"]
        },
        {
          "id": "pause-confirmed",
          "title": "訂閱已暫停",
          "step": 6,
          "terminal": true,
          "instruction": "暫停後的狀態、資料保留、恢復日期。",
          "transitions": ["subscription-plan"]
        },
        {
          "id": "cancel-confirmed",
          "title": "訂閱已取消",
          "step": 6,
          "terminal": true,
          "instruction": "取消後的資料保留期限與復訂條件。",
          "transitions": ["subscription-plan"]
        }
      ]
    }
  ]
}
```

## Rules

### Document

- `version` is `2`. Version 1 stored a single flow at the top level and is rejected.
- `flows` is a non-empty array with unique kebab-case ids.
- Write **one** flow by default; up to three flows of the same product are fine
  when one meeting covers several journeys. The validator warns above three.

### Flow

- Required: `id`, `title`, `task`, `initialState`, `states`.
  - `title` is what appears in the flow selector — name the journey, not the feature.
  - `task` is the scenario in one or two sentences: what the person is trying to
    do and why. It is shown in the rail and is safe to read aloud to a client.
- Optional: `hypothesis` and `successSignal`. Fill them in only when the artifact
  will be used for a moderated participant session; the rail hides the `Brief`
  control entirely when both are absent. An empty string is rejected — omit the
  field instead.
- Optional: `errorSimulation`. Omit it when the flow has no failure worth showing.
  When `supported` is `true`, `label` is the message the product would really
  show, and at least one state needs an error view.

  **`errorSimulation` is for technical or environmental failure** — the save did
  not go through, the service is down — something the person driving toggles on
  top of whatever screen is showing. **It is not for a business rule.** A rule
  the user hits by their own choice ("this slot is inside 24 hours, so it needs a
  phone call", "this plan cannot be downgraded mid-term") is an ordinary branch:
  a sibling state the user reaches by clicking, with its own outcome. If which
  branch you land on depends on what the user picked, it is a transition, not an
  error.
- `initialState` must name a declared state, and should be the real entry point —
  where a user would actually be standing, not the screen under discussion.

### States

- At least two states. Ids are unique within the flow and kebab-case.
- Required per state: `title`, a positive integer `step`, an `instruction` (the
  note shown in the rail for this screen), and an explicit `transitions` array.
- **Steps that share a number are alternatives.** `pause-confirmed` and
  `cancel-confirmed` are both step 6, so the rail draws them as two branches of
  one node rather than two consecutive steps. Use this deliberately: it is how a
  reader sees that a decision forks.
- Every transition target must exist, every state must be reachable from
  `initialState`, and at least one reachable state must be `terminal: true`.
- A terminal state keeps an outgoing transition when it is a natural product
  continuation ("back to the subscription page"), never a walkthrough reset.

### Navigation and scope

- `scope` is `viewport` (default) or `shell`.
  - `viewport` — the current page is spotlit, the surrounding shell dimmed and inert.
  - `shell` — the whole app is bright and its declared navigation is clickable.
- `navTargets` maps shell navigation keys to states: `{ "settings": "account-settings" }`.
  - Every value must be a declared transition **from that state**.
  - Every key must exist as a `data-nav` attribute on a shell element.
  - A state with `navTargets` must declare `scope: "shell"`; otherwise the
    navigation it points at stays dimmed and unusable.
  - A `shell` state with no `navTargets` is allowed but warned: the shell is open
    and nothing in it leads anywhere.

Use navigation steps to make the path real, not to reproduce the product. Two or
three steps of genuine navigation before the screen under discussion is usually
enough.

## Prototype integration

Embed the same object in `prototype.html`:

```html
<script id="flow-spec" type="application/json">…</script>
```

Each state gets one `<template data-flow data-state>` view, plus an optional
`data-variant="error"` view. Product actions are `data-goto="<state-id>"` on a
`<button>`. See [the prototype architecture](prototype-architecture.md).

The validator rejects a mismatch between the embedded spec and `flow.json`, a
`data-goto` that is not a declared transition out of that state, a declared
transition that nothing offers, a nav key with no shell element, and rail
controls inside a product screen.
