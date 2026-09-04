# AgentDeck Research

See [historical artifact provenance](PROVENANCE.md) for the treatment of original
host metadata, frozen Records and explicitly derived acceptance artifacts.

AgentDeck uses Games as behavioral instruments: define an explicit situation,
place AI Players inside it, preserve what happened, and determine what the
resulting Records support.

This directory contains AgentDeck's public Research history and flagship Study
artifacts. Research is a first-class project axis. The active `0.4` source
candidate now closes the redesigned public path from Study preparation and
selected execution through exact Record corpora, deterministic Measures,
immutable Evidence, and authored Findings.

## Start Here

- [The Agentic Edge](2026-04-27-agentic-edge-strategy-stack/README.md) — flagship
  completed Study, results, limitations, reproduction metadata, and public
  artifacts.
- [Research Arc](../docs/research-arc.md) — architecture and end-to-end guidance
  for Study, Measure, Evidence, and Finding.
- [Hugging Face dataset](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study)
  — canonical raw and processed The Agentic Edge artifacts.
- [Curated replay viewer](https://huggingface.co/spaces/agentdeck/agentic-edge-viewer)
  — five selected Match replays.
- [Research index](INDEX.md) — historical Study/package registry.

## Current Source Status

The former `agentdeck.research` modules and these commands are not part of the
active `0.4` source candidate:

```text
agentdeck-research-export
agentdeck-research-score
agentdeck-research-package
agentdeck-research-index
agentdeck-research-validate
```

Documentation or packages that mention them describe the historical `0.2`
workflow. The exact implementation remains available at the
[`agentic-edge-research`](https://github.com/agentdeck/agentdeck/tree/agentic-edge-research)
tag. Do not treat those commands as current `main` APIs.

The active Study surface supports inspection, explicit execution, derivation,
and authored reporting:

```bash
agentdeck study inspect research/2026-04-27-agentic-edge-strategy-stack
agentdeck study validate research/2026-04-27-agentic-edge-strategy-stack
agentdeck study run ...
agentdeck study analyze ...
agentdeck study report ...
```

The package-local `scripts/reproduce_current.py` reads the frozen Hugging Face
revision without mutating it, adapts copied Recorder v1.3 Records locally, and
reproduces the 432-Match historical Evidence/Findings through the current
contracts. `P0` also remains a zero-provider live acceptance path.

## Epistemic Boundary

```text
Game / Question
  -> Study
  -> Prepared Assembly
  -> Runs
  -> canonical Records
  -> deterministic Measures
  -> Evidence
  -> authored Findings
```

- **Record:** what happened during execution.
- **Measure:** what was deterministically extracted from identified Records.
- **Evidence:** what those measurements support under an explicit method and
  Study scope.
- **Finding:** what an author interprets that Evidence to mean.

Research never mutates canonical Records. Every stochastic or intelligent
operation that can affect Evidence must itself terminate in Records before
deterministic measurement begins.

## Historical Archive

Packages under `research/` record the sequence of Studies, pilots, negative
results, interventions, and synthesis that led to The Agentic Edge. Their
manifests, matrices, reports, notes, and scripts are historical artifacts; they
are not all current package templates.

The historical layout commonly used:

```text
research/<study-id>/
|-- README.md
|-- manifest.yaml
|-- matrix.yaml
|-- results.json
|-- results.csv
|-- analysis.md or analysis/
|-- artifacts/
|-- notes/
|-- recordings/
`-- scripts/
```

Do not copy historical `_templates/` as current Study contracts. Raw Match
recordings remain external artifacts; repository
packages store durable pointers, checksums, and human-readable context.
