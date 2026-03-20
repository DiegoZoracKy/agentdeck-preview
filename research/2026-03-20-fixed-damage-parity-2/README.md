# FixedDamage Parity 2

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-20-fixed-damage-parity-2`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: 48/48
- Game: FixedDamageGame
- Players: google:gemini-2.5-flash-lite, google:gemini-2.5-flash
- Seed Base: 7242
- Topline Winner: control cell `Flash-AO` finished `14-10` over `FlashLite-RC-HO`; reinforced cell `FlashLite-RC-TR` finished `15-9` over `Flash-AO`
- Avg Turns: 20.27
- Avg Duration (s): 18.66
- Total Cost: 0.16166
<!-- AUTO_FACTS:END -->

## Why This Exists
- FixedDamage Parity 1 showed that `ReasoningController` brought Flash-Lite much closer to plain Flash, but not to parity.
- The remaining failure mode was seat-conditioned threshold inversion: as second player, `FlashLite-RC` healed too often while healthy and failed to heal in some critical states.
- This follow-up tests whether turn instruction reinforcement can stabilize that reasoning policy enough to close the remaining gap.

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-HO` vs `Flash-AO`
  - `FlashLite-RC-TR` vs `Flash-AO`
- Turn cadence:
  - `FlashLite-RC-HO`: handshake only
  - `FlashLite-RC-TR`: repeated `{controller_format}` on every turn
  - `Flash-AO`: handshake only
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Google runtime setting:
  - `thinking_budget=0` for both Gemini 2.5 models
- Matches planned:
  - `24` per cell, `48` total
- Seed base:
  - `7242` to keep this package on a fresh schedule family

## Primary Endpoints
- `position_policy_delta`
- state-level evidence at `80 HP / 3 potions`, `30 HP / 2 potions`, and `20 HP / 1 potion`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`

## Secondary Endpoints
- win rate
- cost
- latency
- strict contract rate
- position-controlled win splits

## Hypothesis
- `ReasoningController` already gave Flash-Lite most of the behavioral lift it needed.
- Turn reinforcement may reduce the second-player threshold inversion enough to make Flash-Lite genuinely competitive with plain Flash.
- If that happens while staying cheaper than `Flash-AO`, the package becomes a stronger “strategy stack beats model-only selection” result.

## Results
- `FlashLite-RC-HO` vs `Flash-AO`: `Flash-AO` finished `14-10` over `FlashLite-RC-HO`.
- `FlashLite-RC-TR` vs `Flash-AO`: `FlashLite-RC-TR` finished `15-9` over `Flash-AO`.

### Confirmed Behavioral Findings
- The handshake-only control stayed close but did not establish parity.
  - `Flash-AO` finished `14-10` over `FlashLite-RC-HO`
  - the control cell remained outcome-null at pilot scale (`p=0.541`, negligible effect)
  - `FlashLite-RC-HO` still showed the same late-healing / seat-conditioned reasoning pattern from Parity 1:
    - median first potion `60 HP`
    - `position_policy_delta = 0.246`
    - critical-potion response `35.3%`
    - unused-potions-on-loss `42.9%`
- Turn reinforcement materially improved Flash-Lite's behavioral profile.
  - all-attack rate fell `8.3% -> 4.2%`
  - median first potion shifted `60 HP -> 20 HP`
  - unused-potions-on-loss fell `42.9% -> 22.2%`
  - state-action consistency rose `0.896 -> 0.926`
  - `position_policy_delta` fell `0.246 -> 0.206`
  - critical-potion response rose `35.3% -> 43.7%`
  - recovery after missed critical defense rose `0.486 -> 0.580`
- Reinforcement reduced the healthy-state misfire that blocked parity in the prior package.
  - at shared `80 HP / 3 potions`, `FlashLite-RC-HO` attacked `14/15` as first player but used `POTION` `9/12` as second player
  - under reinforcement, `FlashLite-RC-TR` stayed aggressive in the same state: first player attacked `15/15`, second player attacked `9/12`
- Reinforcement did not fully fix low-HP second-player hesitation.
  - at shared `20 HP / 3 potions`, `FlashLite-RC-TR` as first player used `POTION` `9/9`
  - in the same state as second player it split `4` attacks / `4` potions
  - so the second-player threshold inversion narrowed, but did not disappear
- The reinforced parity cell flipped the pilot outcome direction, but it did not cross significance.
  - `FlashLite-RC-TR` finished `15-9` over `Flash-AO`
  - exact-binomial `p=0.307`, small effect
  - this is directional evidence for reinforcement as an equalizer, not a competitive proof yet
- Position stayed load-bearing in both cells.
  - control cell: first player won `18/24`
  - reinforced cell: first player won `21/24`
  - `FlashLite-RC-TR` won `12/12` as first player but only `3/12` as second
  - `Flash-AO` won `9/12` as first player and `0/12` as second in the reinforced cell
  - so the `15-9` reinforced result is not only a Flash-Lite improvement story; position advantage explains a substantial fraction of that cell independent of model or strategy
- The reinforced cell carries a mild strictness confound on the plain-Flash side.
  - `FlashLite-RC-TR` stayed `100%` strict with `0` parse failures
  - `Flash-AO` remained fully parseable, but strictness fell to `89.5%` with `26` recoverable non-strict turns
  - future parity cells should check whether that strictness regression clusters by turn count or by specific HP / potion states

### Directional Signals
- Turn reinforcement appears to help Flash-Lite more than it helps plain Flash in this matchup.
- The reinforced cell is the first parity package where the weaker model plus strategy stack beats plain Flash on raw wins, even though the cell remains underpowered.
- The remaining bottleneck is no longer the original `80 HP` panic-heal. It is residual second-player indecision in critical states.

### What AgentDeck Made Visible
- Without the behavioral layer, this package would read as “one null pilot and one promising but null pilot.”
- The state buckets show the more useful story:
  - handshake-only reasoning still wastes second-player potions while healthy
  - reinforcement mostly removes that healthy-state error
  - but second-player critical-state decisions still split too often to be fully trusted
- That makes the next experiment precise:
  - if we expand, the question is no longer “does reinforcement help at all?”
  - it is “does reinforcement help enough, and is the remaining second-player gap real or just pilot noise?”
  - if we target mechanism directly, the next prompt should anchor to HP-survival thresholds, not to `POTION` specifically
