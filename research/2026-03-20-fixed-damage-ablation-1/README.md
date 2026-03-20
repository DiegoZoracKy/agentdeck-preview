# FixedDamage Ablation 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-ablation-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`
- Seed Base: `10242`
- Topline Winner: `Flash-AO` finished `27-21` over `FlashLite-RC-HP`
- Statistical Read: `p=0.471`, negligible effect
- Position Read: first player won `39/48`; `FlashLite-RC-HP` won only `3/24` as second player
- Avg Turns: `21.52`
- Avg Duration (s): `17.86`
- Total Cost: `0.19172`
<!-- AUTO_FACTS:END -->

## Why This Exists
- Parity 3 showed that the full Flash-Lite stack (`RC + TR + HP-grounding`) produced the strongest competitive result in the series.
- That left one ablation question open:
  - how much of that gain came from repeating `{controller_format}` on every turn?
- This package removes only the turn-time format reinforcement while keeping:
  - `ReasoningController`
  - the HP-threshold instruction
  - the same opponent, fairness settings, and task

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-HP` vs `Flash-AO`
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Turn prompt ablation:
  - `FlashLite-RC-HP` keeps the handshake reasoning contract
  - but its turn prompt does **not** repeat `{controller_format}`
  - it sees only `{game_view}` plus the HP-threshold instruction
- Matches planned:
  - `48`
- Seed base:
  - `10242` to keep this package on a fresh schedule family

## Primary Endpoints
- second-player win split
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`
- strict contract rate

## Secondary Endpoints
- total win rate
- cost
- latency

## Hypothesis
- If the HP-threshold instruction carries most of the value, `FlashLite-RC-HP` should stay close to the Parity 3 profile even without turn-time format reinforcement.
- If turn-time format reinforcement was load-bearing, this ablation should lose behavioral stability, strictness, or second-player competitiveness.

## Results
- `Flash-AO` finished `27-21` over `FlashLite-RC-HP` at `N=48`.
- This is a clear reversal from Parity 3, where `FlashLite-RC-TR-HP` beat `Flash-AO` `31-17`.
- The ablation itself is outcome-null (`p=0.471`, negligible effect), but the directional comparison to Parity 3 is strong:
  - with turn reinforcement: Flash-Lite won `31/48`
  - without turn reinforcement: Flash-Lite won only `21/48`

### Main Finding
- Turn-time `{controller_format}` reinforcement mattered, but not for the reason we first suspected.
- It was **not** load-bearing for contract adherence:
  - `FlashLite-RC-HP` stayed `100%` strict
  - `0` parse failures
- It **was** load-bearing for competitive policy quality:
  - second-player wins collapsed from `10/24` in Parity 3 to `3/24`
  - all-attack matches rose from `10.4%` to `27.1%`
  - losses with unused potions rose from `35.3%` to `51.9%`
  - recovery after missed critical defense fell from `0.563` to `0.496`

### What Held Up Without Turn Reinforcement
- The healthy-state bug stayed fixed.
  - at shared `80 HP / 3 potions`, `FlashLite-RC-HP` attacked `55/55` as first player and `28/28` as second
- Seat symmetry stayed reasonably good on the aggregate metric.
  - `position_policy_delta` stayed low at `0.042`
  - Parity 3 was `0.043`
- First-potion timing did not drift later.
  - median first potion stayed `20 HP`

### What Broke Without Turn Reinforcement
- The model fell back into many more never-heal trajectories.
  - `never_used_rate`: `27.1%` vs `10.4%` in Parity 3
  - `all_attack_match_rate`: `27.1%` vs `10.4%`
- The critical-state threshold became less reliable, especially at `20 HP / 3 potions`.
  - first player: `POTION` `17/23`, `ATTACK` `6/23`
  - second player: `POTION` `16/30`, `ATTACK` `14/30`
  - in Parity 3, second-player `20/3` was better: `18/26` `POTION`, `8/26` `ATTACK`
- The outcome cost was mostly borne in the harder seat.
  - `FlashLite-RC-HP` won `18/24` as first player but only `3/24` as second
  - `Flash-AO` won `21/24` as first player and `6/24` as second
  - first-player dominance strengthened to `39/48`

### Cost and Reliability
- Removing turn reinforcement did lower Flash-Lite cost modestly.
  - `FlashLite-RC-HP`: about `$0.001955` per player-match
  - `FlashLite-RC-TR-HP` in Parity 3: about `$0.002123`
- But that savings came with a much worse competitive result.
- Reliability did not explain the drop.
  - `FlashLite-RC-HP`: `100%` strict, `0` parse failures
  - `Flash-AO`: unchanged from Parity 3 at `94.98%` strict and `0` parse failures

### What AgentDeck Made Visible
- A raw `27-21` loss could be misread as “the HP instruction did not work.”
- The behavioral layer shows the more accurate story:
  - HP grounding still fixed the healthy-state seat bug
  - the model stayed parseable and strict
  - but without turn reinforcement it slipped back into too many pure-attack and unused-potion losses
- So the value of turn reinforcement here is not formatting. It is helping the weaker model keep the better decision policy active throughout the match.
