# AgentDeck Roadmap

Last updated: 2026-04-27

## Active Focus

The active branch is `study/agentic-edge-strategy-stack`.

The current goal is to prepare the next flagship AgentDeck research package:

```text
research/2026-04-27-agentic-edge-strategy-stack/
```

The study asks whether strategy stacks can change LLM agent behavior enough to
overcome model-tier differences in sequential decision environments. The
execution principle is to exercise every major AgentDeck research workflow
surface that strengthens validity, not every API for its own sake.

## Current Study Package

Prepared package contents:

- `manifest.yaml` - package metadata, seed base, run envelope, model roster
- `matrix.yaml` - central cell plan, fairness policy, seed offsets, sampling,
  budget gates, and expansion criteria
- `prompts/` - frozen prompt templates for S0, S1, FixedDamage S3, and
  VariableDamage S3
- `scripts/run_experiment.py` - package-local phase/cell runner
- `analysis.md` - interpretation shell
- `reproduction.md` - dry-run, execution, export, validation, and lock commands
- `recordings/README.md` - external raw-artifact policy
- `artifacts/README.md` - derived-artifact policy

## Study Design Commitments

- Keep `matrix.yaml` as the study spine.
- Use fixed-N sampling for the first flagship version.
- Use `paired_side_swap` with even match counts for head-to-head cells.
- Use only supported first-player policies: `random`, `fixed`, and
  `alternating`.
- Report position effects before topline win-rate claims.
- Disable conclusions in pilot/main cells to keep costs and post-match
  reflection noise controlled.
- Prefer built-in FixedDamage and VariableDamage behavioral scorers before
  adding package-local custom scoring.
- Lock any S2 controller choice after pilot and before main-run expansion.
- Name the exact prior FixedDamage package being replicated before Layer A is
  described as a replication.

## Phase P0 - Local Preflight

Purpose: verify that the package runs without provider credentials.

Cells:

- `p0_fd_bot_smoke`
- `p0_vd_bot_smoke`

Required checks:

- [x] package scaffold exists
- [x] `matrix.yaml` has explicit even match counts for runnable cells
- [x] runner supports phase, cell, dry-run, and match overrides
- [x] list cells cleanly
- [x] P0 dry-run cleanly
- [x] P0 local bot execution writes recordings
- [x] P0 cell export succeeds
- [x] research validation succeeds without introducing fake live results

## Phase P1 - Provider Pilot

Purpose: exercise the main validity surfaces before scaling.

Cells:

- `p1_fd_tier_gap_s0`
- `p1_fd_controller_effect_s1`
- `p1_fd_full_stack_effect_s3`
- `p1_fd_frontier_s3`
- `p1_vd_tier_gap_s0`
- `p1_vd_controller_effect_s1`
- `p1_vd_full_stack_effect_s3`
- `p1_vd_frontier_s3`

Before running P1:

- [ ] provider credentials verified (OPENAI_API_KEY + Google creds not set in current shell — load .env before running)
- [ ] live model IDs confirmed available (gemini-2.5-flash-lite, gpt-4o-mini used in prior experiments; verify current availability before authorizing)
- [x] `matrix.yaml` budget envelope filled (pilot $2.00, main $10.00, expansion $5.00)
- [x] git commit and pricing snapshot recorded (commit 92c17fa, pricing updated_at 2026-02-13)
- [x] P1 dry-run cleanly

After running P1:

- [ ] export every P1 cell
- [ ] export package-level artifacts
- [ ] validate the package
- [ ] record measured cost multipliers for S0, S1, and S3
- [ ] check built-in behavioral scorer coverage
- [ ] update `analysis.md` with pilot gates
- [ ] decide whether S2 is needed
- [ ] prune or expand cells before main-run execution

## Phase P2 - Main Run

Purpose: run only selected cells that support preregistered claims.

P2 must not be populated until P1 is reviewed. Main-run expansion requires:

- explicit cell list in `matrix.yaml`
- fixed even match count per paired-side-swap cell
- locked model roster
- locked prompt templates
- locked controller choices
- budget projection from pilot telemetry
- named FixedDamage replication target
- updated `analysis.md` hypothesis readout plan

## Research Workflow

Use package-local execution and shared export/validation:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
agentdeck-research-export --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --package --no-generated-at
agentdeck-research-validate --research-dir research
```

Raw recordings should be stored externally, with pointers under
`research/2026-04-27-agentic-edge-strategy-stack/recordings/`.

If the console entry points are not installed in a checkout, use the repo-local
wrappers:

```bash
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --list-cells
python3 scripts/research_validate.py --research-dir research
```

## Deferred AgentDeck Product Work

These are not blockers for the study package:

- Native session recovery in the research CLI
- Segmented execution as a framework-level capability
- Duplicate-session pruning in core
- Promotion of package-specific runner logic into framework core
- Broader Autonomous Researcher workflows
- MatchCurator recording-first refactor and LLM-backed curation

## 0.2.x Engineering Hardening

- Decompose `console.py` into narrower lifecycle, scheduling,
  fairness/player-ordering, parse-failure, conclusion, metadata, and
  replay/event-dispatch modules.
- Pick one stable strict-mypy island first, then expand enforcement
  progressively instead of flipping the whole codebase at once.
