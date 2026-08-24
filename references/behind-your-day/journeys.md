# Behind Your Day — observed journey

## Selected: record a purchase and see the work estimate

Status: **observed**. The entry and every link below were walked in fresh
desktop (1440×1000) and mobile (390×844) browser contexts. The selected branch
uses the representative path United States → Food & drink → Coffee & drinks →
$12 USD.

| # | Action | Destination / visible result | Evidence |
|---|---|---|---|
| Entry | Load the public About page | Hero explains the statistical work estimate and offers Add a purchase. | `ev-landing-desktop-shot`, `ev-landing-mobile-shot` |
| 1 | Click/tap **Add a purchase** | `#input` opens the Record a purchase form with region selector, area grid, empty estimate panel, and no saved record. | `ev-add-record-desktop`, `ev-add-record-mobile`, `ev-input-desktop-shot`, `ev-input-mobile-shot` |
| 2 | Choose **Food & drink** | Area grid becomes an item picker with Back, Coffee & drinks, Eating out, delivery & restaurants, and Groceries & food. | `ev-food-desktop`, `ev-food-mobile`, `ev-item-picker-desktop-shot`, `ev-item-picker-mobile-shot` |
| 3 | Choose **Coffee & drinks** | Amount field, USD currency context, CPI note, and Save this record appear. | `ev-coffee-desktop`, `ev-coffee-mobile`, `ev-amount-form-desktop-shot`, `ev-amount-form-mobile-shot` |
| 4 | Enter **12** | Result preview updates to about 18 minutes, likely range 11–29 minutes, with industry and region breakdowns. | `ev-amount-desktop`, `ev-amount-mobile`, `ev-estimate-desktop-shot`, `ev-estimate-mobile-shot` |
| 5 | Submit **Save this record** | Result is marked SAVED and Recent records contains the $12 USD coffee record at about 18 minutes. | `ev-save-desktop`, `ev-save-mobile`, `ev-saved-result-desktop-shot`, `ev-saved-result-mobile-shot` |

**Outcome.** One purchase is saved in browser storage and its statistical work
estimate is visible. The source states that no account is required and records
are not uploaded. Dashboard is an observed follow-on route, but this handoff
stops at the saved result so it does not add an unrelated summary task.

## Adaptation opportunity

Preserve:

- The “why this is worth doing” context before the form: the estimate is about
  work across raw materials, production, transport, and services.
- The decision sequence and observed destinations: area → item → amount →
  estimate → save.
- The wording/data that carries meaning: purchase region, amount/currency,
  estimate range, industry shares, regional shares, and the saved record.

Abstract:

- Brand logo, exact type scale and color palette, decorative icons, source
  imagery, long legal/privacy copy, and unwalked categories.
- The Dashboard route and any data beyond the one representative saved record.
- Responsive CSS details while keeping the observed desktop side-by-side and
  mobile stacked reading order usable in the wireframe.

The resulting prototype is a flow alignment wireframe, not a reproduction of
Behind Your Day. Any uncertainty that remains (especially unwalked category
branches and whether the saved result should lead directly to Dashboard) is
carried into its review ledger.
