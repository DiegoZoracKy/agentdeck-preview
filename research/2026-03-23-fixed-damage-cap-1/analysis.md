# Analysis — FixedDamage FlashLite Cap 1

## Executive Read
<!-- AUTO_FACTS:BEGIN -->
- Primary finding: `Flash-AO` beat `FlashLite-RC-TR-HP-cap128` `32-16` at `N=48` (`p=0.029`, small effect).
- Secondary finding: the cap did restore a real cost edge for Flash-Lite, but only by breaking the behavior that made the full stack competitive.
- Practical recommendation: do not proceed to a tighter cap like `112`; `128` already regresses the strategy too much.
<!-- AUTO_FACTS:END -->

## Outcome Layer
- The package answered the question cleanly once the run moved from
  `us-central1` to `VERTEX_LOCATION=global`.
- `FlashLite-RC-TR-HP-cap128` lost `16-32` to plain `Flash-AO`.
- That is a decisive regression from Parity 3, where the uncapped full stack
  went `31-17` against the same plain Flash baseline on a fresh seed family.
- Position remained load-bearing:
  - `FlashLite-RC-TR-HP-cap128` won `14/24` as first player and only `2/24` as second
  - `Flash-AO` won `22/24` as first player and `10/24` as second
- So the cap did not merely erase a tiny edge. It pushed Flash-Lite back into
  a clearly losing regime.

## Behavioral Layer
- The cap preserved one part of the previous fix:
  - at `80 HP / 3 potions`, second-player Flash-Lite still attacked `22/24`
    times, only slightly worse than the uncapped full stack's `23/24`
- But it badly regressed the critical states that mattered most:
  - `all_attack_match_rate`: `10.4%` -> `29.2%`
  - `unused_potions_on_loss_rate`: `35.3%` -> `65.6%`
  - `critical_potion_response_rate`: `0.434` -> `0.336`
  - `error_recovery_rate`: `0.563` -> `0.415`
  - `state_action_consistency`: `0.947` -> `0.907`
  - `position_policy_delta`: `0.043` -> `0.071`
- The clearest state regression is `20 HP / 3 potions`:
  - uncapped full stack, first player: `ATTACK` `2/21`, `POTION` `19/21`
  - uncapped full stack, second player: `ATTACK` `8/26`, `POTION` `18/26`
  - capped stack, first player: `ATTACK` `13/29`, `POTION` `16/29`
  - capped stack, second player: `ATTACK` `21/34`, `POTION` `13/34`
- So the mild cap did not reintroduce the old healthy-state bug very much.
  It reintroduced the low-HP hesitation bug, especially as second player.

## Cost Layer
- This is the one part of the hypothesis that worked.
- Flash-Lite cost per player-match:
  - uncapped full stack: `$0.002123`
  - capped full stack: `$0.001841`
- Plain Flash cost per player-match in the capped package:
  - `Flash-AO`: `$0.002024`
- So the cap saved about `13.3%` on Flash-Lite itself and made it about `9.1%`
  cheaper than plain Flash in this cell.
- But the competitive cost/performance trade got worse, not better:
  - the old slight cost disadvantage became a real cost edge
  - and the old near-parity outcome became a significant `16-32` loss

## Contract and Confounds
- The successful run required the global Vertex endpoint. That is an execution
  note, not a gameplay confound.
- The cap also caused a real contract-quality regression on Flash-Lite:
  - uncapped full stack strictness: `100%`
  - capped full stack strictness: `85.4%`
  - recoverable non-strict turns: `71`
- There were still `0` parse failures, so the scorer could recover actions.
  But the raw outputs show many clipped responses that lost the final
  `ACTION:` line.
- A direct raw-recording scan found `68` Flash-Lite turns with no `ACTION:` in
  the raw response text, and those clipped turns clustered heavily in the most
  important states:
  - `27` at `20 HP / 3 potions`
  - `7` at `80 HP / 3 potions`
  - `7` at `10 HP / 2 potions`
- So the cap did not just shorten verbose turns. It disproportionately clipped
  the same low-HP decisions where reasoning quality mattered.

## What This Proves
- `VERTEX_LOCATION=global` is the right operational fix for the Flash-side
  throttling that blocked the original regional attempts.
- `max_tokens=128` is not a safe cost optimization for this Flash-Lite stack.
- The cap buys a modest real cost reduction, but it is too destructive to the
  low-HP reasoning policy and to strict contract adherence.

## Next Research Move
- Stop the cap ladder here.
- Do not run `max_tokens=112`; `128` already fails the behavioral regression
  check.
- If FixedDamage gets one more business-oriented cost probe, it should target
  the larger input-side lever instead:
  - a shorter turn reminder / controller scaffold
  - not a tighter output cap
