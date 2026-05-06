# Recordings

Raw AgentDeck match recordings should not be committed to git.

The finalized P0/P1/P2/P3 recordings and processed artifacts are stored in the
Hugging Face dataset:

```text
https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study
hf://datasets/agentdeck/agentic-edge-strategy-stack-study/
```

Initial full artifact snapshot:

```text
13b95490cdc21dbfb1c164c683e485755f90a271
```

Latest study-arc aggregate refresh:

```text
f7ac119f69da08261269bc5cf85fb65741e8ae88
```

The curated replay viewer is hosted as a separate Hugging Face Space:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Latest curated replay Space snapshot:

```text
27ca787db947a393d21ed9847a8a4b44b2cbc317
```

Dataset status:

- owner: `agentdeck`
- dataset: `agentic-edge-strategy-stack-study`
- local staging source: `/tmp/agentic-edge-hf-upload`
- file inventory: `upload_manifest.json`
- checksum manifest: `checksums.sha256`

Uploaded layout:

```text
metadata/
prompts/
analysis/
reports/
p0_preflight/
p1_pilot/
p2_main/
p3_supplemental/
```

The package-local runner writes raw recordings under `agentdeck_runs/` during
execution. Those local directories are runtime artifacts; the Hugging Face
dataset is the durable storage pointer for publication and review.

The Space is a presentation and review surface for the curated examples only.
It is not the durable source for the complete raw recording corpus.
