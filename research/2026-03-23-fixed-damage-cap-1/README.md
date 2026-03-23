# FixedDamage FlashLite Cap 1

**Status**: see `manifest.yaml`  
**Research Question**: see `manifest.yaml`  
**Experiment ID**: `2026-03-23-fixed-damage-cap-1`

## Factual Snapshot (Auto-generated)
<!-- AUTO_FACTS:BEGIN -->
- Status: complete
- Matches: `48/48`
- Game: `FixedDamageGame`
- Players: `google:gemini-2.5-flash-lite`, `google:gemini-2.5-flash`
- Seed Base: `19242`
- Topline Read:
  - `Flash-AO` beat `FlashLite-RC-TR-HP-cap128` `32-16` at `N=48` (`p=0.029`, small effect)
  - the cap made Flash-Lite cheaper than plain Flash, but it clearly damaged the full-stack policy
- Avg Turns: `20.46`
- Avg Duration (s): `74.06`
- Total Cost: `$0.185511`
<!-- AUTO_FACTS:END -->

## Why This Exists
- The best Flash-Lite stack in Parity 3 became competitively strong, but it
  lost the original cost advantage against plain Flash.
- A lower-bound token audit showed that visible reasoning text is a real part
  of the premium, even though it does not explain all of it.
- This package tests the cheapest low-risk lever first:
  - keep the full Flash-Lite stack intact
  - apply a mild `max_tokens=128` cap only to Flash-Lite
  - compare directly against plain `Flash-AO`

## Design Snapshot
- Game + information level: `FixedDamageGame(information_level="partial")`
- Models / providers:
  - `gemini-2.5-flash-lite`
  - `gemini-2.5-flash`
- Strategy conditions:
  - `FlashLite-RC-TR-HP-cap128` vs `Flash-AO`
- Turn-time prompt:
  - same as Parity 3 full stack
  - the only new change is `max_tokens=128` on Flash-Lite
- Fairness:
  - `pairing_policy="paired_side_swap"`
  - `first_player_policy="random"`
- Matches planned:
  - `48`
- Seed base:
  - `19242`

## Primary Endpoints
- second-player win split
- total win rate
- cost per player-match
- `position_policy_delta`
- `critical_potion_response_rate`
- `unused_potions_on_loss_rate`
- `error_recovery_rate`
- state-level evidence at `80 HP / 3 potions`, `20 HP / 3 potions`, and `20 HP / 1 potion`

## Secondary Endpoints
- latency
- strict contract rate
- parse failure rate

## Hypothesis
- If the full-stack Flash-Lite gain depends mostly on ordinary-length reasoning
  rather than very long tail responses, then `max_tokens=128` should preserve
  most of the competitive and behavioral improvement while reducing cost.

## Execution Status
- Two regional attempts failed before the first completed match because
  `Flash-AO` repeatedly exhausted Vertex retry budget in `us-central1`.
- The canonical run switched Vertex to the `global` endpoint, kept the same
  seed base and cell design, and completed all `48` matches.
- The package-local Flash retry/backoff increase remained in place for the
  successful run:
  - `max_retries=12`
  - `retry_delay=4.0`
- This changed latency, not the game rules or response contract, so it is an
  infrastructure note rather than a strategy confound.
