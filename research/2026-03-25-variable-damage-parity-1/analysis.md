# VariableDamage Parity 1 Analysis

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `FlashLite-RC-RISK` held near parity with `Flash-AO` at `N=48`, finishing `26-22` with exact-binomial `p=0.665` and negligible effect size.
- Secondary finding: the risk-grounded treatment preserved its main mechanism gains from Threshold 1: `0.0%` safe-zone healing, `100%` lethal-zone healing, `0.0%` unused-potion losses, and low seat-conditioned drift (`position_policy_delta = 0.0667`).
- Practical recommendation: treat this as a successful parity hold and use it as the Flash-Lite carry-forward condition for the premium `GPT5Mini-AO` pilot.
<!-- AUTO_FACTS:END -->

## Status
- Completed single-cell VariableDamage parity expansion with `48` matches.

## Question
- Does `FlashLite-RC-RISK` stay competitive with plain Flash at `N=48`, or was the `12-12` Threshold 1 tie only a pilot signal?

## What This Package Is Designed To Answer
1. Whether the Threshold 1 carry-forward treatment remains near parity or opens a real edge at a larger sample.
2. Whether the cleaned-up inventory-timing policy remains stable at `N=48`.
3. Whether `FlashLite-RC-RISK` is strong enough to justify a follow-up premium comparison against `GPT5Mini-AO`.

## Primary Readout
- Outcome:
  - `FlashLite-RC-RISK` beat `Flash-AO` `26-22`
  - exact-binomial `p=0.665`
  - effect size `h=0.083`, negligible
  - first-player wins remained common overall (`34/48`), but the treatment still converted `8/24` from second seat versus `6/24` for Flash
- Behavior:
  - `FlashLite-RC-RISK` preserved the Threshold 1 cleanup:
    - `safe_zone_potion_rate = 0.0%`
    - `lethal_zone_potion_rate = 100%`
    - `unused_potions_on_loss_rate = 0.0%`
    - `position_policy_delta = 0.0667`
  - `Flash-AO` stayed close on broad danger handling, but remained messier:
    - `safe_zone_potion_rate = 8.9%`
    - `lethal_zone_potion_rate = 82.4%`
    - `unused_potions_on_loss_rate = 15.4%`
    - `first lethal entry inventory median = 0`

## Behavioral Interpretation
- The treatment survived expansion without collapsing back into the RC-only failure mode.
- The strongest evidence is that the pilot’s core mechanism stayed intact:
  - Threshold 1 risk pilot:
    - `safe_zone_potion_rate = 0.0%`
    - `lethal_zone_potion_rate = 100%`
    - `first lethal zero-potions rate = 26.1%`
    - `position_policy_delta = 0.0505`
  - Parity 1 expansion:
    - `safe_zone_potion_rate = 0.0%`
    - `lethal_zone_potion_rate = 100%`
    - `first lethal zero-potions rate = 39.6%`
    - `position_policy_delta = 0.0667`
- So the expansion did introduce some regression in first-lethal inventory timing, but not in the core safety rules.
- The remaining weakness is more specific now:
  - with multiple potions, the treatment heals correctly in danger (`57.9%`)
  - with one potion left, danger-zone healing drops sharply (`21.7%`)
- That explains why the treatment can hold parity without yet opening a decisive gap. It is now robust in safe and lethal zones, but still leaves value on the table in one-potion danger states.

## Interpretation Guardrails
- This is a single-condition parity expansion, not a new intervention branch.
- The relevant comparison point is Threshold 1's treatment cell, not the older RC-only or TR packages.
- If the cell stays close, the behavioral profile matters as much as the win count.

## Follow-On Rule
- Run the premium follow-up next:
  - `FlashLite-RC-RISK` vs `GPT5Mini-AO`
  - `N=24`
- Keep `Flash-AO` as the practical cheap reference baseline.
- Do not reopen the Flash-Lite TR branch; the open issue is now narrow one-potion danger timing, not controller cadence.
