# Website Reference Contract

`reference.json` is the evidence index for an adapted website flow. Keep narrative detail in the companion Markdown files; keep IDs and facts here.

```json
{
  "version": 1,
  "id": "github-ai-website-cloner-template",
  "source": {
    "url": "https://example.com/path",
    "canonicalUrl": "https://example.com/path",
    "capturedAt": "2026-08-21T10:00:00+08:00"
  },
  "coverage": {
    "viewports": [{ "name": "desktop", "width": 1440, "height": 1000 }],
    "sweeps": ["initial-render", "scroll", "click", "hover", "responsive"]
  },
  "evidence": [
    { "id": "ev-page", "kind": "rendered-page", "method": "browser", "url": "https://example.com/path", "capturedAt": "2026-08-21T10:00:00+08:00", "viewport": "desktop" },
    { "id": "ev-shot-desktop", "kind": "screenshot", "method": "browser", "path": "screenshots/desktop.png", "url": "https://example.com/path", "capturedAt": "2026-08-21T10:00:00+08:00", "viewport": "desktop" }
  ],
  "observations": [
    { "id": "obs-hero", "kind": "observed", "summary": "The page has a hero with a primary call to action.", "evidence": ["ev-page"] }
  ],
  "journeys": [
    { "id": "journey-start", "title": "Start a task", "entry": "Hero call to action", "steps": ["Open the page", "Select the primary action"], "outcome": "Destination was observed", "evidence": ["ev-page"], "status": "observed" }
  ],
  "limitations": ["Only the initial desktop render was available."]
}
```

## Rules

- Use `version: 1` and a unique kebab-case `id`.
- Include at least one evidence record and one observation linked to valid evidence IDs.
- Set observation `kind` to `observed` or `inferred`.
- Include a non-empty `limitations` array, even when coverage is broad.
- Each journey must cite evidence and set `status` to `observed`, `partial`, or `inferred`.
- Evidence with `kind: "screenshot"` needs a `path` relative to `reference.json`, and the validator fails when that file is missing. Never create an evidence id for a capture that did not happen.
- Each journey needs at least two steps, and `outcome` must say plainly when the destination was not observed.
