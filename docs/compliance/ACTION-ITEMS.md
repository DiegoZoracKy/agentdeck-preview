# Action Items

**Generated**: 2026-01-21

## SPEC-AGENTDECK
Source: `docs/compliance/SPEC-AGENTDECK.md`

- [x] **E3**: Add `elapsed_time` as `@property` on AgentDeck class ✅ Fixed 2026-01-22
- [x] **L4**: Consider exposing `session.finished_at` if needed for duration analysis ✅ Addressed via `elapsed_time` property (duration available)
- [x] **R1**: Add explicit type validation in `replay()` method for match parameter ✅ Fixed 2026-01-22

## SPEC-CONTROLLER
Source: `docs/compliance/SPEC-CONTROLLER.md`

- [x] **GB6**: Clarified in spec that built-in controllers (ActionOnlyController, ReasoningController) are validation-optional - they accept any parsed action when unbound. Custom controllers requiring strict validation should implement GB6 check. ✅ Documented 2026-01-22
- [x] **CP2**: Align parse_conclusion() return type between spec (dict) and implementation (str) ✅ Fixed 2026-01-22 - now returns `{"reflection": response.strip()}`

## SPEC-GAME-MECHANIC-TURN-BASED
Source: `docs/compliance/SPEC-GAME-MECHANIC-TURN-BASED.md`

- [ ] TL3: Replace console.get_player_action calls with runtime-first parse failure handling (deferred - requires larger refactor, documented with NOTE comment)
- [x] TL2: Validate get_current_player outputs and raise ValueError on invalid results ✅ Fixed 2026-01-22
- [x] TL5: Include match_id in TurnLoop exception messages ✅ Fixed 2026-01-22
- [x] TL6: Enforce JSON-serializable custom events ✅ Fixed 2026-01-22

## SPEC-LLM
Source: `docs/compliance/SPEC-LLM.md`

- [ ] CC1: Define spec-compliant behavior for ADC providers like Gemini (deferred - spec clarification needed)
- [x] RE2/PM3: Add phase context to metadata payloads ✅ Fixed 2026-01-22
- [x] RE3/MA1: Include provider identifiers in usage_info and error messages ✅ Fixed 2026-01-22
- [x] MA4: Propagate estimated token flags into usage_info/metadata ✅ Fixed 2026-01-22
- [x] CH2: Remove duplicate local history appends ✅ Fixed 2026-01-22
- [x] PI3: Align pricing fallback logging level with spec (warning not error) ✅ Fixed 2026-01-22
- [x] PM2: Add response_text to metadata ✅ Fixed 2026-01-22

## SPEC-MATCH-RUNTIME
Source: `docs/compliance/SPEC-MATCH-RUNTIME.md`

- [ ] MR2: Inject mechanic metadata and enforce ordering in emit_event (deferred - architectural enhancement)
- [x] MR4: Fix handle_parse_failure to pass game context in Console runtime ✅ Fixed 2026-01-22
- [ ] MR6: Add runtime-level cleanup helpers for mechanics (deferred - architectural enhancement)
- [ ] MR7: Introduce compatibility tests/versioning for MatchRuntime API (deferred - testing scope)

## SPEC-OBSERVABILITY
Source: `docs/compliance/SPEC-OBSERVABILITY.md`

- [x] **PL3**: Verify PLAYER_ACTION_PARSE_FAILED emission includes all specified fields ✅ Verified 2026-01-22 (event includes player, match_id, turn_number, parse_result, policy_outcome)
- [x] **PL4**: Verify all lifecycle events include complete prompt metadata schema ✅ Verified 2026-01-22 (core fields present; optional fields vary by event type as expected)

## SPEC-PARALLEL
Source: `docs/compliance/SPEC-PARALLEL.md`

- [x] PO1: Log a warning when falling back to sequential due to get_player_order override ✅ Fixed 2026-01-22
- [ ] FP1: Cancel outstanding futures on first worker failure (deferred - requires concurrent.futures refactor)
- [ ] PC1: Document benchmarking guidance for concurrency selection (deferred - documentation scope)

## SPEC-PLAYER
Source: `docs/compliance/SPEC-PLAYER.md`

- [ ] **DS2**: Consider documenting that retry-related metadata (retries, attempt_durations) is LLMPlayer-specific, not required in base Player
- [ ] **CI3**: Audit LLMPlayer subclasses to ensure they override `clone()` when needed for parallel execution

## SPEC-PRICING
Source: `docs/compliance/SPEC-PRICING.md`

- [ ] **V0**: Add explicit `isinstance(data, dict)` check at start of `_validate_pricing_structure()` (critical)
- [ ] **C1**: Consider using AgentDeckLogger for consistent logging integration (optional)

## SPEC-RENDERER
Source: `docs/compliance/SPEC-RENDERER.md`

- [ ] Add a metadata format hint (e.g., "format": "text")
- [ ] Implement explicit validation and descriptive ValueError for required fields

## SPEC-RESEARCH
Source: `docs/compliance/SPEC-RESEARCH.md`

- [ ] Add elapsed_time tracking for progressive comparisons
- [ ] Include player_order_source and ordering metadata in comparison outputs
- [ ] Attach model and game config snapshots to comparison metadata
- [ ] Compute CIs for aggregated metrics beyond win rates
- [ ] Add explicit install guidance in dependency ImportErrors
- [ ] Validate match recording files before analysis
- [ ] Handle recorder schema version compatibility in post-hoc tools

## SPEC-RESEARCH-EXPERIMENT
Source: `docs/compliance/SPEC-RESEARCH-EXPERIMENT.md`

- [ ] Enforce README.md presence per experiment in validator
- [ ] Validate results.json/results.csv format and schema_version
- [ ] Add recordings/ pointer-only validation
- [ ] Provide deterministic export option or exclude generated_at from diff-sensitive checks

## SPEC-SPECTATOR
Source: `docs/compliance/SPEC-SPECTATOR.md`

- [ ] Consider adding player lifecycle handler stubs to base Spectator class for discoverability (optional, per duck-typing contract)
- [ ] Document explicitly in spectator.py which handlers exist for player lifecycle events
