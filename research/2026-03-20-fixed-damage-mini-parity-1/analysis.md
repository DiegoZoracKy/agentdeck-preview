# Analysis

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Sample size (`n`): 48 total matches in one cell
- Decisive matches: 48
- Draws: 0
- Win rates: `FlashLite-RC-TR-HP` finished `41-7` over `Mini-AO`
- Statistical read: `p=6.24e-07`, medium effect, significant at `alpha=0.05`
- Position read: first player won `27/48`; `FlashLite-RC-TR-HP` won `19/24` as second player vs `Mini-AO` `2/24`
- First player in first recorded match: `Mini-AO`
- Strict contract rate: `1.0000` overall
- Artifact validation: all exported matches passed
- Average turns: `22.40`
- Average duration (s): `23.97`
- Total cost: `0.16189`
<!-- AUTO_FACTS:END -->

Interpretation note: use `first_player` for position claims. `player_order`
is the effective roster order after scheduling, while `first_player` is the actor
who actually took the first turn.

## Executive Summary
- Primary finding: the full Flash-Lite strategy stack decisively beat plain `gpt-4o-mini`, finishing `41-7` at `N=48`.
- Statistical finding: unlike the Flash parity packages, this is a clean competitive result, not a directional one.
- Mechanism finding: Flash-Lite won because it kept a survival-grounded healing threshold while Mini burned potions immediately at `80 HP` in both seats.
- Practical read: this is the strongest current evidence that strategy stack can matter more than base-model family in this task class, though not at a lower cost than Mini.

## Outcome Readout
- `FlashLite-RC-TR-HP` beat `Mini-AO` `41-7` at `N=48`.
- The outcome read is strong and statistically clean.
  - exact binomial `p=6.24e-07`
  - effect size `0.787` (`medium`)
- This is stronger than every Flash parity package in the current arc.
- The result also held up across seat:
  - `FlashLite-RC-TR-HP` won `22/24` as first player
  - `FlashLite-RC-TR-HP` won `19/24` as second player

## Position-Controlled Results
- Position was present but not dominant in the way it was against Flash.
  - first player won `27/48`
  - upset rate: `21/48`
- `FlashLite-RC-TR-HP` was strong from both seats:
  - `22/24` as first player
  - `19/24` as second player
- `Mini-AO` was weak from both seats:
  - `5/24` as first player
  - `2/24` as second player
- So this package is not another example of a position-heavy soft edge.
  - the cross-provider result is robust across seat

## Behavioral Endpoints
- Flash-Lite and Mini were both highly consistent and perfectly strict, so the difference was not format discipline.
  - `state_action_consistency`: `0.961` for `FlashLite-RC-TR-HP`, `0.975` for `Mini-AO`
  - strict contract rate: `100%` for both
- The difference was policy quality.
  - `position_policy_delta`: `0.044` for `FlashLite-RC-TR-HP`, `0.077` for `Mini-AO`
  - `unused_potions_on_loss_rate`: `71.4%` for `FlashLite-RC-TR-HP`, but on only `7` losses total
  - `unused_potions_on_loss_rate`: `0.0%` for `Mini-AO`, because Mini spent its potions early rather than preserving them for later losing states
- Flash-Lite's late healing remained coherent:
  - median first potion `20 HP`
  - `critical_potion_response_rate`: `0.513`
  - `error_recovery_rate`: `0.730`
- Mini's early healing was stable but maladaptive:
  - median first potion `80 HP`
  - `0` critical-potion support turns in the behavioral profile, because it had usually already spent potions before reaching critical HP

## Threshold-State Evidence
- The clearest mechanism is at shared `80 HP / 3 potions`.
  - `Mini-AO` used `POTION` `24/24` as first player and `24/24` as second
  - `FlashLite-RC-TR-HP` attacked `48/48` as first player and `46/47` as second
- So Mini's policy was not merely "slightly more defensive."
  - it had a fixed early-heal rule at the exact state where Flash-Lite correctly kept pressure on
- Flash-Lite then stayed coherent in the states that matter later:
  - at shared `20 HP / 3 potions`, `FlashLite-RC-TR-HP`:
    - first player: `POTION` `19/23`
    - second player: `POTION` `17/20`
  - at shared `20 HP / 1 potion`, `FlashLite-RC-TR-HP`:
    - first player: `POTION` `17/20`
    - second player: `POTION` `17/17`
- Mini never produced comparable critical-with-potion buckets in this package.
  - it had already spent those potions at `80 HP`
  - that is why its `critical_potion_response_rate` shows `0/0`, not because it navigated critical states perfectly

## Cost, Latency, and Reliability
- Cost:
  - `FlashLite-RC-TR-HP`: `$0.10861` total, `$0.002263` per player-match
  - `Mini-AO`: `$0.05328` total, `$0.001110` per player-match
  - the tuned Flash-Lite stack cost about `2.04x` as much as Mini in this package
- Latency:
  - package average duration: `23.97s` per match
  - the HP-grounded Lite stack raised latency through longer reasoning traces
- Reliability:
  - both players were `100%` strict with `0` parse failures
- So the outcome gap is not coming from formatting or recoverability issues.
  - it is coming from different decision policies

## Interpretation
- This package does justify the sentence “the full Flash-Lite stack beat plain Mini decisively in FixedDamage.”
- It also sharpens the broader research story:
  - strategy stack is not merely an intra-family equalizer
  - it can produce a cross-provider advantage when the baseline opponent policy is worse matched to the task
- The cost framing changes here.
  - this is not a cheaper-win story
  - it is a stronger-policy story at about double the per-match cost of Mini
- That makes the result useful in a different way:
  - AgentDeck is not only for showing that cheaper models can catch stronger ones
  - it is also for showing when a tuned weaker model becomes stronger than an untuned baseline from another family

## Limitations
- The package is still a single-cell study on one fresh seed family.
- FixedDamage remains a local sequential decision task, so the result transfers most directly to similar task classes.
- Position will need explicit reporting in any cross-provider interpretation.
- Mini's baseline in this game is now clearly known to be extremely early-healing, so this matchup is not a neutral “best plain policy” reference for all models.

## Next Steps
- The current Flash-Lite stack is clearly strong enough to carry beyond the Flash matchup.
- If the next goal is breadth, move to a different game or task class rather than more FixedDamage mini-matches.
- If the next goal is product framing, the current evidence now supports two separate claims:
  - tuned strategy can make Flash-Lite competitive with plain Flash
  - tuned strategy can decisively beat plain Mini
