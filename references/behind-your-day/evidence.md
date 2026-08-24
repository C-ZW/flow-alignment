# Behind Your Day — evidence log

## Capture plan

- Canonical URL: `https://behindyourday.com/`
- Site key: `behind-your-day`
- Captured: 2026-08-24, Asia/Taipei (`+08:00`)
- Desktop viewport: 1440×1000 CSS pixels
- Mobile viewport: 390×844 CSS pixels
- Browser: fresh Playwright Chromium contexts, device scale factor 1
- Output: screenshot files under `screenshots/`; the viewport-sized files are
  exactly the declared dimensions. `*-full.png` files preserve the full scroll
  for IA review.

## Capture log

| Capture | URL / hash | Desktop | Mobile | What was checked |
|---|---|---|---|---|
| Landing | `/` | `landing-desktop.png`, `landing-desktop-full.png` | `landing-mobile.png`, `landing-mobile-full.png` | Initial render, hero CTA, shell, responsive stacking, full-page scroll |
| Add record | `/#input` | `input-desktop.png`, `input-desktop-full.png` | `input-mobile.png`, `input-mobile-full.png` | CTA navigation, region selector, category grid, empty estimate panel |
| Item picker | `/#input` | `item-picker-desktop.png` | `item-picker-mobile.png` | Food & drink selection and three visible item choices |
| Amount form | `/#input` | `amount-form-desktop.png` | `amount-form-mobile.png` | Coffee & drinks selection, amount field, currency, save action |
| Estimate preview | `/#input` | `estimate-preview-desktop.png` | `estimate-preview-mobile.png` | Entered `$12`, live estimate, range, industries, regions |
| Saved result | `/#input` | `saved-result-desktop.png`, `saved-result-desktop-full.png` | `saved-result-mobile.png`, `saved-result-mobile-full.png` | Save action, SAVED status, recent record, dashboard link |
| Dashboard context | `/#dashboard` | `dashboard-desktop.png`, `dashboard-desktop-full.png` | `dashboard-mobile.png`, `dashboard-mobile-full.png` | Follow-on route and responsive summary layout |

Each screenshot evidence record in `reference.json` identifies its viewport and
path. Each journey link also cites a non-screenshot `interaction` record for
the action that caused the destination; a screenshot alone is not treated as
proof of navigation.

## Interaction and responsive sweep

1. Loaded the landing page at both viewports after the client-side data shell
   became available.
2. Scrolled to the bottom of each landing page to inspect the How it works,
   method, privacy, and footer sections.
3. Hovered the landing Add a purchase CTA in both contexts; no hover-only route
   or content was observed.
4. Clicked/tapped Add a purchase, Food & drink, Coffee & drinks, entered `12`,
   and submitted Save this record in both contexts.
5. Followed View dashboard after save to verify the observed destination and
   captured it as context for the IA. This route is not selected for the
   prototype.
6. Checked URL hashes (`#input` and `#dashboard`), visible text, control counts,
   and local browser storage after save. The saved event persisted in browser
   storage and the Recent records row rendered.

## Unresolved or bounded claims

- Only one representative category/item path was walked. The other six area
  buttons and two other food items were seen but their destinations and result
  calculations are not claimed here.
- The source uses a client-side estimation-data load and briefly exposes a
  loading placeholder. That transient state is outside the selected journey.
- No account, upload, or network-backed submission was attempted; the site’s
  visible copy and local-storage behavior were recorded as rendered evidence.
- The capture uses the current 2022 model/data-year label and a fresh-browser
  default country context. Values can change with future source data updates.
- The site owner authorized these demo captures. They remain research evidence,
  not prototype assets; unrelated third-party material visible in a capture
  retains its own rights.
