# SPEC-OBSERVABILITY Audit Note

Spec: [SPEC-OBSERVABILITY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-OBSERVABILITY.md)
Wave: 4
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Event model for lifecycle, gameplay, and domain events plus shared `Event` / `EventContext` payload rules.
- Does not own spectator APIs, recorder persistence rules, or replay/viewer interfaces beyond shared event-shape expectations.

## Evidence Reviewed
- spec sections: full document, especially §§3-9 and references
- implementation files: [event_bus.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/event_bus.py), [console.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/console.py), [event_factory.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/event_factory.py), [game_event_emitter.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/game_event_emitter.py), [replay.py](/home/diegozoracky/dev/agentdeck-preview/src/agentdeck/core/replay.py)
- tests: [test_replay_lifecycle.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_replay_lifecycle.py), [test_monitors.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_monitors.py), [test_recorder_lifecycle.py](/home/diegozoracky/dev/agentdeck-preview/tests/unit/test_recorder_lifecycle.py)
- docs/examples: in-spec examples and adjacent spectator/recorder/replay specs

## Findings

### Blocker
- none

### High
- The spec still carried stale cross-references (`AGENTS.md`, old version-pinned adjacent specs) that made the contract look older than the actual baseline.
- A few historical labels such as “new in v1.2.0” added noise without changing the current contract.

### Medium
- The MATCH_END metadata discussion used older wording around `MatchResult` payloads and needed tightening to the current event vocabulary.

### Low
- none

## Drift Classification Summary
- implementation drift: 0
- spec drift: 3
- test drift: 0
- doc/example drift: 0

## Required Remediation
- Remove stale cross-references and version-pinned wording.
- Keep the spec focused on the current event contract, not historical rollout notes.

## Beta Relevance
- required before beta: yes, because observability is the shared contract that recorder, replay, spectators, and research all depend on
- safe to defer: further editorial trimming that does not change payload guarantees

## Final Verdict
- [SPEC-OBSERVABILITY.md](/home/diegozoracky/dev/agentdeck-preview/specs/SPEC-OBSERVABILITY.md) is compliant after Wave 4 cleanup. The implementation already matched the event model; the work here was to remove stale governance drift so the spec reads as the current contract.
