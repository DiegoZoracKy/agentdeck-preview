# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches in one cell
- Decisive matches: 48
- Draws: 0
- Win rates: `Flash-AO` finished `27-21` over `FlashLite-RC-HP`
- Statistical read: `p=0.471`, negligible effect
- Position read: first player won `39/48`; `FlashLite-RC-HP` won `3/24` as second player
- First player in first recorded match: `FlashLite-RC-HP`
- Strict contract rate: `0.9748` overall
- Artifact validation: all exported matches passed
- Average turns: `21.52`
- Average duration (s): `17.86`
- Total cost: `0.19172`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: removing turn-time `{controller_format}` reinforcement caused Flash-Lite to lose the competitive edge it had in Parity 3.
- Competitive read: `Flash-AO` beat `FlashLite-RC-HP` `27-21`, while the full-stack condition had previously won `31-17`.
- Mechanism read: the loss did **not** come from contract failure. Flash-Lite stayed `100%` strict and parseable.
- The drop came from policy quality:
  - many more all-attack matches
  - many more losses with unused potions
  - much worse second-player performance
- Practical conclusion: once HP-grounding is in place, turn-time reinforcement still matters, but mainly as a policy stabilizer rather than a formatting crutch.

## Outcome Readout
- `Flash-AO` beat `FlashLite-RC-HP` `27-21` at `N=48`.
- The cell itself is outcome-null:
  - exact binomial `p=0.471`
  - negligible effect size
- But as an ablation against Parity 3, the directional change is substantial:
  - Parity 3 `FlashLite-RC-TR-HP`: `31-17`
  - Ablation `FlashLite-RC-HP`: `21-27`
  - swing: `10` wins

## Position-Controlled Results
- Position became more dominant after removing turn reinforcement.
  - first player won `39/48`
  - Parity 3 first-player wins: `35/48`
- Flash-Lite's seat performance collapsed:
  - `FlashLite-RC-HP`: `18/24` as first player, `3/24` as second
  - Parity 3 `FlashLite-RC-TR-HP`: `21/24` as first player, `10/24` as second
- So the ablation cost Flash-Lite:
  - `3` first-player wins
  - `7` second-player wins
- The bigger loss was clearly in the harder seat.

## Behavioral Endpoints
- What stayed strong:
  - `state_action_consistency`: `0.952` vs Parity 3 `0.947`
  - `position_policy_delta`: `0.042` vs `0.043`
  - strictness: still `100%`
- What got worse:
  - `all_attack_match_rate`: `27.1%` vs `10.4%`
  - `unused_potions_on_loss_rate`: `51.9%` vs `35.3%`
  - `critical_potion_response_rate`: `0.395` vs `0.434`
  - `error_recovery_rate`: `0.496` vs `0.563`
  - `never_used_rate`: `27.1%` vs `10.4%`
- First-potion timing stayed the same:
  - median first potion `20 HP` in both packages
- That is an important result:
  - the ablation did not shift the nominal threshold later
  - it increased the number of matches where the model never reached or never acted on that threshold properly

## Threshold-State Evidence
- The healthy-state fix survived the ablation.
  - at shared `80 HP / 3 potions`, `FlashLite-RC-HP` attacked `55/55` as first player and `28/28` as second
  - so turn-time reinforcement was not needed to preserve the `80 HP` correction
- The critical-state behavior worsened, especially at `20 HP / 3 potions`.
  - `FlashLite-RC-HP` at shared `20 HP / 3 potions`:
    - first player: `POTION` `17/23`, `ATTACK` `6/23`
    - second player: `POTION` `16/30`, `ATTACK` `14/30`
  - Parity 3 `FlashLite-RC-TR-HP` at the same state:
    - first player: `POTION` `19/21`, `ATTACK` `2/21`
    - second player: `POTION` `18/26`, `ATTACK` `8/26`
- At `20 HP / 1 potion`, the ablation stayed fairly close to Parity 3:
  - first player: `15/17` `POTION`
  - second player: `15/16` `POTION`
- So the main regression is not a total collapse of low-HP healing.
  - it is weaker commitment at the first critical threshold while potions are still abundant

## Cost, Latency, and Reliability
- Cost:
  - `FlashLite-RC-HP`: about `$0.0938` total, `$0.001955` per player-match
  - `FlashLite-RC-TR-HP` in Parity 3: about `$0.1019` total, `$0.002123` per player-match
  - removing turn reinforcement did save some money
- Latency:
  - package average duration: `17.86s` per match
  - Parity 3 average duration: `19.78s`
  - so the ablation also ran faster
- Reliability:
  - `FlashLite-RC-HP`: `100%` strict, `0` parse failures
  - `Flash-AO`: `94.98%` strict, `0` parse failures
  - the policy drop is not a parsing story

## Interpretation
- This ablation gives a clean answer to your question.
- Flash-Lite with HP-grounding but **without** turn-time `{controller_format}` reinforcement is materially worse than the full-stack condition.
- The reinforcement appears to matter because it helps the model keep the better policy active across the whole match, not because it reminds the model how to format the response.
- That is an important strategy-stack result:
  - handshake-only reasoning plus a good heuristic is not enough
  - repeating the decision contract each turn still buys real decision quality in this task

## Limitations
- This is still one fresh-seed ablation package.
- The cell itself is null, so the strongest claim here is comparative to Parity 3 rather than inferential inside this package alone.
- FixedDamage remains a local sequential decision task.

## Next Steps
- Keep `FlashLite-RC-TR-HP` as the best known Flash-Lite condition for this game.
- Do not replace it with `FlashLite-RC-HP`.
- If we want to optimize further, the next good question is whether there is a cheaper turn-time reminder that preserves the Parity 3 gains without paying the full reinforcement cost.
