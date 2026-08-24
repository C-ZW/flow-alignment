# Walkthrough: record a purchase and see the work estimate

This is an alignment walk for the observed public journey, not a product tour.
Use a fresh browser profile at 1440×1000 and 390×844. The prototype uses the
representative source path United States → Food & drink → Coffee & drinks →
$12 USD. The source's live result updates while typing; this low-fidelity
artifact keeps the amount and preview together in the amount state and makes
Save this record the next click.

## Before the first click

Open the file from disk. It should begin on **About / public landing**, not on a
form or result. Ask:

“Is this the real place a person starts, or do they arrive directly on Add
record or Dashboard?”

The entry claim is open in `flow.json`: the direct URL capture observed this
page, but it did not establish audience entry behavior.

## Main path

1. **About / public landing → Add a purchase**

   Claim to pause on: the hero explains a statistical work estimate and offers
   one primary route into recording a purchase. Confirm whether the direct
   hero CTA and the header Add record tab should be equivalent entry routes.
   Follow the hero **Add a purchase** button (the header Add record tab is the
   declared navigation alternative).

2. **Add record / area of life → Food & drink**

   Claim to pause on: the form asks for purchase region and then an area of
   life; the artifact exposes Food & drink as the representative branch while
   the other visible areas stay static. Ask whether a different area belongs in
   the core journey or whether all areas share this pattern. Click **Food &
   drink**.

3. **Food & drink / item picker → Coffee & drinks**

   Claim to pause on: choosing an area replaces the grid with three item
   choices, and Coffee & drinks is the example used for the evidence capture.
   Ask whether the other two food items need distinct estimate context. Click
   **Coffee & drinks**.

4. **Coffee & drinks / amount → Save this record**

   Claim to pause on: the person enters an amount in its original currency and
   sees a statistical estimate, not a stopwatch measurement. Confirm whether
   `$12 USD` is a useful discussion value and whether the live preview should
   be visually separate from the save action. The wireframe keeps **12** visible
   as the representative value; click **Save this record**.

5. **Saved estimate / work behind the purchase**

   Check the ending postcondition: the result is marked Saved, the estimate is
   about 18 minutes with an 11–29 minute range, the industry and regional
   breakdowns are visible, and Recent records contains the purchase. Ask:

   “Is this the right ending, or should the primary journey continue directly
   into Dashboard?”

   This ending-state position is open. Dashboard was observed in the source but
   is deliberately outside this one-flow artifact.

## Back branch

Restart, then use the main path through Food & drink. At the item picker, click
**← Back to areas** and confirm that the form returns to its area-of-life grid.
This branch checks the observed recovery route without claiming that an item or
category was saved. From the returned form, restart before walking the main path
again so every terminal walk starts at the declared entry point.

Walk the main path and the Back branch at both widths. At 390×844, confirm the
header remains usable, the focused product action is not hidden under the rail,
the item/form/result cards reflow vertically, and the saved result is readable
without horizontal overflow. Scroll the saved result and resize once to confirm
the amber spotlight follows the focused region.

## Review ledger prompts

- **Entry point (open):** About page versus a deep link to Add record or
  Dashboard.
- **Navigation (open):** Hero CTA/header tab equivalence and whether a route is
  missing before the estimate.
- **Branches (open):** Whether the other visible areas/items must be complete
  branches before handoff.
- **Failure and recovery (not applicable):** No technical failure was observed;
  do not treat the transient data-loading boundary as a modeled failure without
  a separate complete journey.
- **Ending state (open):** Saved result versus continuing into Dashboard.

## Corrections for the agent

Record spoken corrections outside the browser. The browser has no review form.
For each correction, identify the affected flow/state, update `flow.json` and
its state view together, run both validators and wrapper checks, then restart and
re-walk the complete affected branch at both widths. Do not treat a route-map
jump as proof that a skipped product transition works.
