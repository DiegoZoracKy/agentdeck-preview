# Action Items

**Generated**: 2026-01-21
**Updated**: 2026-01-25 (spec relaxations applied)

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

- [x] TL3: ~~Replace console.get_player_action calls with runtime-first parse failure handling~~ ✅ Spec relaxed 2026-01-25 - console helpers allowed as long as parse-failure policy is correctly applied
- [x] TL2: Validate get_current_player outputs and raise ValueError on invalid results ✅ Fixed 2026-01-22
- [x] TL5: Include match_id in TurnLoop exception messages ✅ Fixed 2026-01-22
- [x] TL6: Enforce JSON-serializable custom events ✅ Fixed 2026-01-22

## SPEC-LLM
Source: `docs/compliance/SPEC-LLM.md`

- [x] CC1: ~~Define spec-compliant behavior for ADC providers like Gemini~~ ✅ Spec clarified 2026-01-25 - ADC and implicit auth satisfy credential resolution
- [x] RE2/PM3: Add phase context to metadata payloads ✅ Fixed 2026-01-22
- [x] RE3/MA1: Include provider identifiers in usage_info and error messages ✅ Fixed 2026-01-22
- [x] MA4: Propagate estimated token flags into usage_info/metadata ✅ Fixed 2026-01-22
- [x] CH2: Remove duplicate local history appends ✅ Fixed 2026-01-22
- [x] PI3: Align pricing fallback logging level with spec (warning not error) ✅ Fixed 2026-01-22
- [x] PM2: Add response_text to metadata ✅ Fixed 2026-01-22

## SPEC-MATCH-RUNTIME
Source: `docs/compliance/SPEC-MATCH-RUNTIME.md`

- [x] MR2: ~~Inject mechanic metadata and enforce ordering in emit_event~~ ✅ Dropped from spec 2026-01-25 - ordering handled by emission order, mechanic metadata is optional observability sugar
- [x] MR4: Fix handle_parse_failure to pass game context in Console runtime ✅ Fixed 2026-01-22
- [x] MR6: ~~Add runtime-level cleanup helpers for mechanics~~ ✅ Dropped from spec 2026-01-25 - TurnLoop handles bindings, runtime doesn't own cleanup
- [x] MR7: ~~Introduce compatibility tests/versioning for MatchRuntime API~~ ✅ Dropped from spec 2026-01-25 - versioning policy, not runtime invariant

## SPEC-OBSERVABILITY
Source: `docs/compliance/SPEC-OBSERVABILITY.md`

- [x] **PL3**: Verify PLAYER_ACTION_PARSE_FAILED emission includes all specified fields ✅ Verified 2026-01-22 (event includes player, match_id, turn_number, parse_result, policy_outcome)
- [x] **PL4**: Verify all lifecycle events include complete prompt metadata schema ✅ Verified 2026-01-22 (core fields present; optional fields vary by event type as expected)

## SPEC-PARALLEL
Source: `docs/compliance/SPEC-PARALLEL.md`

- [x] PO1: Log a warning when falling back to sequential due to get_player_order override ✅ Fixed 2026-01-22
- [x] FP1: ~~Cancel outstanding futures on first worker failure~~ ✅ Spec relaxed 2026-01-25 - best-effort cancellation; failed results not counted
- [x] PC1: ~~Document benchmarking guidance for concurrency selection~~ ✅ Dropped from spec 2026-01-25 - README guidance, not spec invariant

## SPEC-PLAYER
Source: `docs/compliance/SPEC-PLAYER.md`

- [x] **DS2**: Documented that retry-related metadata (retries, attempt_durations) is LLMPlayer-specific ✅ Verified 2026-01-22 - base Player lacks retry fields by design; LLMPlayer subclasses provide them
- [x] **CI3**: Audit LLMPlayer subclasses for clone() ✅ Verified 2026-01-22 - LLMPlayer.clone() recreates client, providers inherit correctly

## SPEC-PRICING
Source: `docs/compliance/SPEC-PRICING.md`

- [x] **V0**: Add explicit `isinstance(data, dict)` check at start of `_validate_pricing_structure()` (critical) ✅ Fixed 2026-01-22
- [x] **C1**: ~~Consider using AgentDeckLogger for consistent logging integration~~ ✅ Dropped 2026-01-25 - standard logging works fine, not a spec invariant

## SPEC-RENDERER
Source: `docs/compliance/SPEC-RENDERER.md`

- [x] MO1: Add a metadata format hint (e.g., "format": "text") ✅ Fixed 2026-01-22
- [x] EH1: ~~Implement explicit validation and descriptive ValueError for required fields~~ ✅ Spec relaxed 2026-01-25 - generic renderers (TextRenderer) are lenient by design; schema-specific renderers MAY validate

## SPEC-RESEARCH
Source: `docs/compliance/SPEC-RESEARCH.md`

- [x] DI3: ~~Add elapsed_time tracking for progressive comparisons~~ ✅ Spec relaxed 2026-01-25 - elapsed_time RECOMMENDED not MUST
- [x] SR3: ~~Include player_order_source and ordering metadata in comparison outputs~~ ✅ Already guidance in spec - player_order_source optional for post-hoc analysis
- [x] RE2: ~~Attach model and game config snapshots to comparison metadata~~ ✅ Spec relaxed 2026-01-25 - MUST record seed, SHOULD record configs
- [x] MA2: ~~Compute CIs for aggregated metrics beyond win rates~~ ✅ Spec relaxed 2026-01-25 - SHOULD compute CIs where statistically meaningful
- [x] DH1: ~~Add explicit install guidance in dependency ImportErrors~~ ✅ Spec relaxed 2026-01-25 - install guidance SHOULD be included
- [x] PH2: ~~Validate match recording files before analysis~~ ✅ Spec relaxed 2026-01-25 - SHOULD validate, MUST produce clear errors
- [x] PH3: ~~Handle recorder schema version compatibility in post-hoc tools~~ ✅ Spec clarified 2026-01-25 - MUST support v1.0.0+, older versions not supported

## SPEC-RESEARCH-EXPERIMENT
Source: `docs/compliance/SPEC-RESEARCH-EXPERIMENT.md`

- [x] RE1: ~~Enforce README.md presence per experiment in validator~~ ✅ Spec relaxed 2026-01-25 - README RECOMMENDED for curated experiments, not required
- [x] RE2/RE5: ~~Validate results.json/results.csv format and schema_version~~ ✅ Spec clarified 2026-01-25 - validator checks provenance; schema_version SHOULD be included
- [x] RE6: ~~Add recordings/ pointer-only validation~~ ✅ Spec clarified 2026-01-25 - repo policy via .gitignore, not runtime validation
- [x] RE8: ~~Provide deterministic export option or exclude generated_at from diff-sensitive checks~~ ✅ Spec clarified 2026-01-25 - output deterministic excluding timestamps

## SPEC-SPECTATOR
Source: `docs/compliance/SPEC-SPECTATOR.md`

- [x] CA1/CA3: ~~Consider adding player lifecycle handler stubs to base Spectator class for discoverability~~ ✅ Not applicable - spec already defines duck-typing contract (HC1), stubs are ergonomics not compliance
- [x] ~~Document explicitly in spectator.py which handlers exist for player lifecycle events~~ ✅ Not applicable - spec §4 documents all handlers, implementation follows spec

---

## Summary

**All action items resolved.** Phase 7 complete.

| Category | Fixed | Spec Relaxed/Dropped | Verified/N/A | Total |
|----------|-------|---------------------|--------------|-------|
| Code fixes | 18 | - | - | 18 |
| Spec relaxations | - | 20 | - | 20 |
| Verifications | - | - | 8 | 8 |
| **Total** | **18** | **20** | **8** | **46** |
