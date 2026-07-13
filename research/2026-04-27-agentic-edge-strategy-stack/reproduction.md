# Reproduction

This package has completed P0, P1, P2, and P3. The official study aggregate
includes P2 and the targeted P3 FixedDamage S1 ladder-completion cell. P0
remains preflight-only and P1 remains pilot-only.

## Environment

Run commands from the repository root.

Provider-backed cells require:

- `OPENAI_API_KEY`
- `VERTEX_PROJECT_ID` or `GOOGLE_APPLICATION_CREDENTIALS_B64`
- optional `VERTEX_LOCATION`

Before live execution, record:

- AgentDeck git commit
- AgentDeck package version
- provider model IDs
- pricing snapshot
- approved pilot/main/expansion budget limits

## Code References

The execution freeze and live-run notes remain in `matrix.yaml`. The published
study package and viewer updates are represented by these GitHub commits:

- Study package: [`e9dc6a77`](https://github.com/agentdeck/agentdeck-core/commit/e9dc6a77b3495dc80b6deed71b07a2af83c1cc64)
- Portable viewer: [`f98e05c5`](https://github.com/agentdeck/agentdeck-core/commit/f98e05c5efbbb558594aaccd08fd370d92360d85)
- Curated viewer examples: [`b8771c4d`](https://github.com/agentdeck/agentdeck-core/commit/b8771c4d21ab5591b3d37aee44eaf307acaee13f)
- Implementation reference: [`d659bdf2`](https://github.com/agentdeck/agentdeck-core/commit/d659bdf244d1f0462c0d43aa2609be6c3c4a7672)

The implementation-reference commit is the code snapshot recorded in the
Hugging Face metadata for game, controller, recorder, exporter, validator, and
behavioral-scorer code. The study-package commit is the curated Git package
state containing the final matrix, generated results, analysis, and
documentation.

## Inspect the Matrix

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --list-cells
```

## Dry Runs

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P2 --dry-run
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P3 --dry-run
```

## Local Preflight

`P0` uses local policy bots only and should not make provider calls.

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P0
```

After `P0`, export and validate the preflight cells:

```bash
agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --cell p0_fd_bot_smoke \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --cell p0_vd_bot_smoke \
  --no-generated-at

agentdeck-research-validate --research-dir research
```

## Provider Pilot

Run the provider-backed pilot only after the dry runs, local preflight, and
budget envelope pass.

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py --phase P1
```

Export each cell, then refresh package-level artifacts:

```bash
agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --phase P1 \
  --no-generated-at

agentdeck-research-export \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --package \
  --no-generated-at
```

Built-in FixedDamage and VariableDamage behavioral profiles are computed during
export when the package uses automatic behavioral scoring. Use
`agentdeck-research-score` only if a package-local custom scorer is added or a
scorer change requires rescoring.

## Main-Run Lock

Before adding `P2` cells:

- fill all `TBD` budget values in `matrix.yaml`
- record measured pilot cost multipliers
- lock the selected model roster
- lock the S2 controller choice if S2 is added
- name the exact prior FixedDamage package being replicated
- keep all paired-side-swap match counts even
- update the authored analysis directory with pilot gates and expansion
  decisions

## Main Run

P2 was executed as the primary fixed-N study phase. P3 was then run as the
targeted FixedDamage S1 cross-tier ladder-completion cell. The package aggregate
is scoped to P2 and P3 by `matrix.yaml`:

```yaml
phase_model:
  study_phases: [P2, P3]
```

Export and validate:

```bash
python3 scripts/research_export.py \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --package \
  --no-generated-at

python3 scripts/research_validate.py --research-dir research --write-index
```

## P3 Ladder Completion

P3 fills the FixedDamage S1 cross-tier tuning-ladder step:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/run_experiment.py \
  --cell p3_fd_frontier_s1 \
  --concurrency 2

python3 scripts/research_export.py \
  --experiment-dir research/2026-04-27-agentic-edge-strategy-stack \
  --cell p3_fd_frontier_s1 \
  --no-generated-at
```

P3 is included in the package aggregate so the official study artifact contains
the full FixedDamage S0 -> S1 -> S3 tuning arc.

Raw recordings belong in external storage, not git. Store only artifact pointers
under `recordings/`.

## External Artifact Download

The complete raw-recording and processed-artifact payload is stored in the
Hugging Face dataset:

```text
https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study
```

Initial full artifact snapshot:

```text
13b95490cdc21dbfb1c164c683e485755f90a271
```

Latest study-arc aggregate refresh:

```text
f7ac119f69da08261269bc5cf85fb65741e8ae88
```

The curated replay viewer is hosted separately as a Hugging Face Space:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Latest curated replay Space snapshot:

```text
27ca787db947a393d21ed9847a8a4b44b2cbc317
```

To download it locally, run:

```bash
.venv/bin/hf download \
  agentdeck/agentic-edge-strategy-stack-study \
  --repo-type dataset \
  --local-dir /tmp/agentic-edge-hf-download
```

The downloaded dataset contains:

```text
metadata/
prompts/
analysis/
reports/
p0_preflight/
p1_pilot/
p2_main/
p3_supplemental/
checksums.sha256
upload_manifest.json
```

The Space contains only the five curated study replay examples. The dataset is
the canonical raw and processed artifact store.

## Development Checkout Fallbacks

If the package has not been installed and the `agentdeck-research-*` console
scripts are unavailable, use the repo-local wrappers:

```bash
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --list-cells
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --phase P1 --no-generated-at
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --cell p3_fd_frontier_s1 --no-generated-at
python3 scripts/research_export.py --experiment-dir research/2026-04-27-agentic-edge-strategy-stack --package --no-generated-at
python3 scripts/research_validate.py --research-dir research
```
