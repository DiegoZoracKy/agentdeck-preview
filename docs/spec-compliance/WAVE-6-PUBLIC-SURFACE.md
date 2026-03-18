# Wave 6 Public Surface Audit Note

Wave: 6
Status: complete
Verdict: compliant
Last updated: 2026-03-17

## Scope
- Release-facing docs and runnable examples:
  - [README.md](/home/diegozoracky/dev/agentdeck-preview/README.md)
  - [viewer/README.md](/home/diegozoracky/dev/agentdeck-preview/viewer/README.md)
  - [examples/README.md](/home/diegozoracky/dev/agentdeck-preview/examples/README.md)
  - [research/README.md](/home/diegozoracky/dev/agentdeck-preview/research/README.md)
  - [scripts/README.md](/home/diegozoracky/dev/agentdeck-preview/scripts/README.md)
  - [minimal_experiment.py](/home/diegozoracky/dev/agentdeck-preview/examples/minimal_experiment.py)
  - [spectator_example.py](/home/diegozoracky/dev/agentdeck-preview/examples/spectator_example.py)
- Goal: ensure public guidance matches the audited spec/code contract and the defaults users actually experience.

## Evidence Reviewed
- audited specs from Waves 1-5
- public docs and example scripts listed above
- runnable validation:
  - [test_minimal_setup.py](/home/diegozoracky/dev/agentdeck-preview/examples/test_minimal_setup.py)
  - [spectator_example.py](/home/diegozoracky/dev/agentdeck-preview/examples/spectator_example.py)

## Findings

### Blocker
- none

### High
- Several public examples/docs still used stale session-config arguments (`log_dir`, `record_dir`) even though the current contract uses `run_dir`.
- Public example docs still referenced an obsolete `HandshakeController` mental model that is not a public surface.

### Medium
- Replay guidance in the examples README still pointed at an outdated recording path.
- The viewer README used an invalid `AgentDeck` / `deck.play(...)` snippet shape.
- Research/scripts docs under-described checkpoint aggregation and deterministic export options that already exist in the tooling.

### Low
- One mock spectator example printed overly noisy raw action payloads, which hurt the public UX even though the example technically ran.

## Drift Classification Summary
- implementation drift: 0
- spec drift: 0
- test drift: 0
- doc/example drift: 6

## Required Remediation
- Update docs/examples to use `run_dir`, current replay paths, and current prompt/default terminology.
- Keep public examples focused on the actual default user experience rather than legacy internal vocabulary.

## Beta Relevance
- required before beta: yes, because these docs define the first-run experience
- safe to defer: deeper tutorial expansion and broader example coverage

## Final Verdict
- Wave 6 is compliant after cleanup. The public docs/examples now describe the current AgentDeck contract instead of older pre-audit usage patterns.
