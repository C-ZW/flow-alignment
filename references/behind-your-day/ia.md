# Behind Your Day — rendered information architecture

Source: [https://behindyourday.com/](https://behindyourday.com/), captured at
1440×1000 and 390×844 on 2026-08-24. This is a rendered-page map, not a claim
about implementation internals.

## Shell and route topology

The shared shell is a compact horizontal header on desktop: brand mark and
“Behind Your Day” at left, About / Add record / Dashboard tabs in the middle,
and language plus “Data year 2022” controls at right. At 390px the brand and
utility controls remain at the top while the tabs wrap below. The tabs are
clickable routes; the language and data-year controls are visible controls whose
downstream behavior was not part of the selected journey. [ev-landing-desktop-shot]
[ev-landing-mobile-shot]

```text
About (#about)
├─ hero → Add a purchase → Add record (#input)
├─ How it works (scroll content)
├─ Reading the result / method note
└─ Your data / browser-storage note

Add record (#input)
├─ purchase region selector
├─ area-of-life grid
│  └─ chosen area → item picker → amount + currency → estimate / save
├─ estimated result panel
└─ Saved / Recent records → View dashboard (#dashboard)

Dashboard (#dashboard)
├─ time-period filters
├─ headline metrics
├─ area-of-life, work-region, industry, and region summaries
└─ selected-period purchase records → Add record
```

The diagram shows observed routes where the capture actually followed them;
controls that were visible but not walked are left as topology rather than
claimed behavior.

## About page, in visual order

1. **Hero / entry.** A small uppercase “SEE THE WORK BEHIND SPENDING” eyebrow,
   oversized border-work headline, explanatory paragraph, one-person-hour
   caveat, three data facts, and the primary “Add a purchase →” action. This is
   the selected journey entry. [ev-landing-desktop-shot]
   [ev-landing-mobile-shot]
2. **How it works.** A dark-green band begins with “Start with one purchase. See
   the work behind it.” and presents three numbered cards: enter a purchase,
   estimate work time, and see where it comes from. This is scroll content, not a
   separate route in the selected flow. [ev-landing-desktop-full-shot]
   [ev-landing-mobile-full-shot]
3. **Reading the result.** A method note says the result is an estimate rather
   than a stopwatch measurement and links to data sources / calculation detail.
   [ev-landing-desktop-full-shot] [ev-landing-mobile-full-shot]
4. **Your data.** A privacy note states that records stay in the browser and no
   account is required, followed by footer links for data sources/licences and
   privacy/advertising. [ev-landing-desktop-full-shot]
   [ev-landing-mobile-full-shot]

Interaction model: hero CTA and shell tabs are click/tap routes; the lower
sections are scroll/read content. No hover-only route or content was observed.

## Add record route, in visual order

1. **Intro.** “ADD RECORD” / “Record a purchase” plus a one-sentence
   instruction, a “How is this calculated?” link, and the two-level categories
   label. [ev-input-desktop-shot] [ev-input-mobile-shot]
2. **Purchase form.** A country select is followed by an explanatory note and
   an eight-item area-of-life grid. The desktop workspace keeps the form and
   estimate panel side by side; mobile reflows them into a vertical stack.
   [ev-input-desktop-full-shot] [ev-input-mobile-full-shot]
3. **Item picker.** Choosing Food & drink replaces the area grid with Back and
   three item buttons: Coffee & drinks, Eating out, delivery & restaurants, and
   Groceries & food. [ev-item-picker-desktop-shot]
   [ev-item-picker-mobile-shot]
4. **Amount entry.** Choosing Coffee & drinks reveals an amount field, USD
   currency context, a CPI note, and “Save this record →”. [ev-amount-form-desktop-shot]
   [ev-amount-form-mobile-shot]
5. **Estimate panel.** Entering 12 updates the result with about 18 minutes,
   a likely 11–29 minute range, five visible industry rows, and a regional
   breakdown. The source shows this preview before save. [ev-estimate-desktop-shot]
   [ev-estimate-mobile-shot]
6. **Saved history.** Submitting Save this record marks the result SAVED and
   adds a recent-record row with the purchase, region, amount, and estimated
   time. View dashboard is the next observed route, but it is not part of the
   selected prototype journey. [ev-saved-result-desktop-shot]
   [ev-saved-result-mobile-shot]

Interaction model: country selection, category buttons, item buttons, amount
entry, save, and View dashboard are product actions. The explanatory copy and
breakdown rows are read-only. The capture walked one representative branch;
other area-of-life and item choices were visible but not traced.

## Dashboard route (observed context, not selected flow)

After save, View dashboard changes the hash to `#dashboard` and shows a headline
summary, Today / This week / This month / All time filters, four metric cards,
four breakdown cards (area, work region, industry, region), and a selected-period
record list. At the captured representative input the dashboard showed about 18
minutes, one purchase, 79% inside the purchase region, 21% outside, and the saved
coffee record. The desktop layout is a wide grid; mobile stacks the cards.
[ev-dashboard-desktop-full-shot] [ev-dashboard-mobile-full-shot]

## Abstraction boundary for the prototype

Preserve the observable decision sequence — start from the public explanation,
choose a purchase area and item, enter an amount, see the statistical estimate,
and save it — plus the context that makes the result discussable (region,
amount, estimate range, industries, and regions).

Abstract brand marks, exact colors, licensed/third-party imagery, decorative
icons, and long source copy. The prototype uses neutral sketchbook data while
keeping the observed labels and representative values specific enough to
correct. Dashboard remains documented as source context but is intentionally
outside this one-flow handoff.
