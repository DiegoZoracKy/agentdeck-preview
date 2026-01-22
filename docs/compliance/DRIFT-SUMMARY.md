# Drift Summary

**Generated**: 2026-01-21

## SPEC-AGENTDECK
Source: `docs/compliance/SPEC-AGENTDECK.md`

- E3/L4: `elapsed_time` not exposed as property
- L4: `finished_at` exposure
- R1: TypeError for unsupported input types

## SPEC-CONTROLLER
Source: `docs/compliance/SPEC-CONTROLLER.md`

- GB6: Missing RuntimeError for unbound validation
- CP2: parse_conclusion return type mismatch

## SPEC-GAME-MECHANIC-TURN-BASED
Source: `docs/compliance/SPEC-GAME-MECHANIC-TURN-BASED.md`

- TL3: Direct console call bypasses runtime.parse_failure pipeline
- TL2: Invalid player errors do not match spec
- TL5: Exception messages missing match_id
- TL6: Custom events not validated for JSON-serializability

## SPEC-LLM
Source: `docs/compliance/SPEC-LLM.md`

- CC1: Gemini bypasses api_key enforcement
- RE2: Logger calls omit phase context
- RE3: RuntimeError missing provider identifier
- MA1: usage_info lacks provider identifier
- MA4: Estimated usage flag dropped
- CH2: Local history duplicated
- PI3: Cost fallback logs ERROR instead of warning
- PM1: usage_info not wired into handshake/turn metadata
- PM2: response_text key missing from metadata
- PM3: Phase context missing from metadata

## SPEC-MATCH-RUNTIME
Source: `docs/compliance/SPEC-MATCH-RUNTIME.md`

- MR2: emit_event does not attach mechanic metadata or enforce ordering
- MR4: handle_parse_failure delegates without game parameter in Console runtime
- MR6: Exception safety enforced in mechanic, not runtime
- MR7: No explicit backward compatibility guard

## SPEC-OBSERVABILITY
Source: `docs/compliance/SPEC-OBSERVABILITY.md`

- PL3: PLAYER_ACTION_PARSE_FAILED event schema verification
- PL4: Prompt metadata completeness in lifecycle events

## SPEC-PARALLEL
Source: `docs/compliance/SPEC-PARALLEL.md`

- PO1: Fallback warning uses debug level
- FP1: Parallel failures do not cancel remaining workers
- PC1: Benchmarking guidance not explicitly documented

## SPEC-PLAYER
Source: `docs/compliance/SPEC-PLAYER.md`

- DS2: Partial metadata in base Player
- CI3: Clone implementation varies by provider

## SPEC-PRICING
Source: `docs/compliance/SPEC-PRICING.md`

- V0: Missing root structure validation
- C1: Logger not using AgentDeckLogger

## SPEC-RENDERER
Source: `docs/compliance/SPEC-RENDERER.md`

- MO1: Missing format hint in metadata
- EH1: No validation for missing required fields

## SPEC-RESEARCH
Source: `docs/compliance/SPEC-RESEARCH.md`

- DI3: Progressive comparisons lack elapsed_time tracking
- SR3: player_order_source not surfaced in comparison metadata
- RE2: Missing model/game config in comparison metadata
- MA2: Confidence intervals not computed for all aggregated metrics in comparisons
- DH1: ImportError lacks explicit install guidance
- PH2: Match recordings not validated
- PH3: No recorder schema version handling

## SPEC-RESEARCH-EXPERIMENT
Source: `docs/compliance/SPEC-RESEARCH-EXPERIMENT.md`

- RE1: README.md presence not enforced
- RE2: No provenance check for results.json/results.csv
- RE5: Results schema_version not validated
- RE6: Recordings directory constraints not enforced
- RE8: Export outputs are not strictly deterministic

## SPEC-SPECTATOR
Source: `docs/compliance/SPEC-SPECTATOR.md`

- CA1/CA3: Context field presence varies by event timing
- Base Spectator missing player lifecycle handler stubs
