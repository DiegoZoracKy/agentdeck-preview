# SPEC-BEHAVIORAL-ARCHIVIST-CHOICE v0.1.0

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-07-21
> Implementation: Complete (`src/agentdeck/games/examples/archivist_choice_behavioral.py`)
> Review State: Legacy-approved
> Audience: Research engineers, game authors, product execution engineers

## 1. Purpose

Define the deterministic Archivist Choice behavioral profile so a Core research
package can explain archival triage behavior from recorded matches without a
product-owned score calculation.

The profile turns the game's final state and recorded processed cases into
reproducible score, completion, and action-fit metrics.

## 2. Terminology

| Term | Meaning |
| --- | --- |
| **Archivist profile** | The game-specific behavioral profile for ArchivistChoiceGame. |
| **Final score** | The score in a player's final recorded game state. |
| **Processed case** | One final-state entry recording manuscript id, chosen action, best action, and score delta. |
| **Action fit** | The recorded fraction of processed cases whose chosen action equals the game's post-hoc best action. |
| **Post-hoc oracle** | Best-action or score-table data used only after execution for scoring; it MUST NOT be treated as player-visible input. |

## 3. Architecture

    recorder match payloads
      -> ArchivistChoiceBehavioralScorer
      -> BehavioralProfileResult
      -> Core results.json / results.md
      -> external consumers such as product Artifact Sets

- The scorer belongs to AgentDeck Core, alongside the Archivist Choice game.
- It MUST consume recordings only. It MUST NOT call providers, mutate records,
  reconstruct a player prompt, or use browser/product state.
- The scorer MAY use final-state best_action and score_delta values as post-hoc
  scoring evidence. Their presence in a result MUST NOT imply that the player
  saw those fields.
- Product code MAY project profile values for presentation, but MUST NOT
  recompute their semantic values.

## 4. Data Structure

The scorer MUST return a BehavioralProfileResult with:

    schema_version: 2
    game_id: archivist_choice
    profile_id: archivist_choice_behavioral
    profile_version: 0.1.0
    coverage:
      matches_total
      matches_evaluable
      turns_total
      turns_evaluable
    aggregate_metrics: {}
    per_player:
      <player>:
        mean_final_score
        mean_processed_cases
        best_action_rate
        mean_score_delta_per_processed_case
    state_metrics:
      by_manuscript:
        <manuscript id>:
          processed_cases
          best_action_rate
          mean_score_delta
    evidence:
      aggregate_metrics: {}
      per_player: metric numerators, denominators, and observed match counts
      state_metrics: metric numerators and denominators
    quality_flags:
      complete
      unsupported_metrics

All numeric outputs MUST be JSON serializable finite values.

## 5. Scoring Rules

1. A match is evaluable when final_state contains mappings for scores and
   processed entries for every declared player.
2. mean_final_score is the arithmetic mean of a player's final scores across
   evaluable matches.
3. mean_processed_cases is the arithmetic mean count of a player's final
   processed entries across evaluable matches.
4. best_action_rate is matching processed actions divided by processed cases
   with a recorded best_action.
5. mean_score_delta_per_processed_case is summed score_delta divided by
   processed cases with a numeric score_delta.
6. Per-manuscript state metrics aggregate the same action-fit and score-delta
   observations by manuscript_id.
7. turns_total is the number of recorded gameplay events. turns_evaluable is
   the number of processed-case observations with enough fields for scoring.

## 6. Invariants

1. **ACB1 Determinism:** Equal recorder payloads and configuration MUST produce
   canonically equal profile data.
2. **ACB2 Recording-only:** The scorer MUST derive values from records; it MUST
   NOT access live game objects, providers, or product state.
3. **ACB3 No prompt claim:** Post-hoc best_action data MUST appear only as
   scoring evidence; the profile MUST NOT claim it was visible to a player.
4. **ACB4 Explicit coverage:** Missing final state or malformed processed
   entries MUST reduce coverage or appear as unsupported, never as a fabricated
   score of zero.
5. **ACB5 Safe arithmetic:** Zero denominators MUST use a documented neutral
   value with an unsupported flag, rather than NaN or Infinity.
6. **ACB6 Export integration:** Auto behavioral-profile resolution for
   ArchivistChoiceGame MUST include this profile in Core results.json.

## 7. Error Handling

| Condition | Required behavior |
| --- | --- |
| Non-Archivist payloads | supports returns false; auto resolution selects another scorer or none. |
| Missing scores/processed map | Match is not evaluable; coverage and quality flags expose the absence. |
| Unknown player in final state | Ignore only the unknown entry; do not invent a declared-player score. |
| Missing best_action | Exclude from action-fit denominator and mark the metric unsupported when no observations exist. |
| Missing score_delta | Exclude from score-delta denominator and mark the metric unsupported when no observations exist. |

## 8. Testing Strategy

- Unit tests use recorder payloads with complete, incomplete, and mixed
  outcomes.
- Tests verify deterministic canonical JSON, per-player score means, action-fit
  rates, per-manuscript metrics, and zero-denominator flags.
- Export integration verifies results.json includes the profile automatically
  for ArchivistChoiceGame.
- Regression tests verify player-visible renderer fields are not used as a
  substitute for post-hoc score evidence.

## 9. Canonical Example

For a player who processes four cases per match with final score 11 and chooses
the recorded best action on every case:

    mean_final_score: 11.0
    mean_processed_cases: 4.0
    best_action_rate: 1.0
    mean_score_delta_per_processed_case: 2.75

The profile reports these values as deterministic post-hoc behavioral evidence,
not as a claim about the player's private prompt.

## 10. Non-Goals

- Re-ranking models across worlds.
- Defining archival expertise outside ArchivistChoiceGame.
- Exposing best_action or score-table fields to players.
- LLM-generated commentary or causal interpretation.
- Product-specific UI or experiment lineage behavior.

## 11. Design Rationale

Archivist Choice was promoted as a product holdout only after a product-owned
renderer removed answer-key fields from the player view. The same discipline
requires its behavioral read to live in Core: the console owns deterministic
game semantics; the product owns how those results become inspectable evidence.
