# Reserve Courier: from a Game to Research

This example asks whether misleading dispatcher advice changes an AI's ability
to plan three deliveries while preserving an energy reserve. A second proposed
treatment asks for a brief stated rationale. The Game has a known optimum of
15 points, a conservative score of 6, and an infeasible score of 0.

The example is intentionally outside the importable library. Obtain this
directory from the same public source revision as your installed package. It uses
public AgentDeck APIs and the `agentdeck study` CLI, with no edits to the kernel.
Install AgentDeck into your Python environment before running these commands.
All output directories below must be new and outside `study/`.

## Start with one local Player

```bash
python examples/reserve_courier/journey.py basic --output-root /tmp/courier-basic
python examples/reserve_courier/journey.py extended --output-root /tmp/courier-extended
```

The basic path composes a Game, an authored Player and ActionOnlyController.
The extended path adds an explicit JSON Controller, JSON Renderer, DecisionTrail
Spectator and ProgressProbe Monitor, then runs two matches concurrently. Both
check the expected score. The oracle separately enumerates all 8 schedules in
all 18 distinct worlds; this is Game validation, not evidence about a model.

Read `study/courier_game.py` for rules and the explicit single-player ABORT_MATCH
policy. Read `study/components.py` for the optional components. The Player sees
the rendered prompt; the Controller validates a response; the Spectator records
observations; the Monitor watches runtime progress.

## Complete the local Research journey

```bash
python examples/reserve_courier/journey.py local --output-root /tmp/courier-local
```

This inspects and validates the Study, executes 12 calibration matches and four
extension matches, analyzes the explicit Cells, checks known Measure results,
authors a bounded Finding, resolves exact citations, renders a report and
replays every Record. It repeats analysis and reporting with network access
disabled and compares bytes. A deliberately invalid citation must be rejected.
The extension group varies JSON/rationale, rendering, serial execution and
conclusion handling; it is integration QA, not a causal experiment.

The main artifacts are `summary.json`, `local-execution.json`,
`local-analysis.json` and `local-report/report.md`. CLI envelopes contain an
absolute `data.output_root` and artifact paths relative to it. For example,
resolve a receipt as `Path(data['output_root']) / data['receipt_path']`.
Canonical Records and receipts live under `runs/`; source and original Records
remain unchanged during Research.

## Optional bounded provider smoke

```bash
agentdeck study inspect examples/reserve_courier/study --json
# Read the plan and copy its plan_sha256 into the next command.
# Supply OPENAI_API_KEY through the host environment.
python examples/reserve_courier/journey.py smoke \
  --approve '<plan_sha256>' --output-root /tmp/courier-smoke
```

This first repeats and verifies local calibration, then explicitly selects the
`smoke` group: gpt-4.1-nano and gpt-4o-mini × two advice conditions × action/rationale,
one match per Cell. There are at most 32 provider calls, 384 output tokens per
call, no conclusion calls and no automatic retries. These are execution bounds,
not a guaranteed invoice price. The receipt reports measured known usage.

The eight-match smoke tests integration. It cannot establish either hypothesis.
Repeated seeds can produce the same world; count distinct worlds separately
from matches. Rationale is observable response text, and the token cap is part
of that treatment. The Measure does not score a technical abort as a behavioral
loss. To investigate the hypotheses, author a new Study revision with adequate
world coverage, sample size and an explicit analysis plan.

For a partial run, keep its envelope, receipt, Records and provider journal.
The runner stops and never retries a slot or overwrites an output directory.
Use `agentdeck study analyze --help` to select explicit Cells and analyze that
receipt; missing expected Records remain unavailable. A new execution requires
a new output directory and is a separate observation.

## Where each responsibility lives

| File | Responsibility |
| --- | --- |
| `study/study.yaml` | Question, hypotheses, phases, Cells and conditions |
| `study/assembly_*.py` | Models, components, concurrency, matches and seeds |
| `study/research-profile.yaml` | Game affordances and interpretation boundaries |
| `study/measures.py` | Deterministic observations with sources and denominators |
| `journey.py` | User-authored workflow, calibration assertions and Finding template |

The normative example contract is [SPEC-EXAMPLE-RESERVE-COURIER](../../specs/SPEC-EXAMPLE-RESERVE-COURIER.md).
