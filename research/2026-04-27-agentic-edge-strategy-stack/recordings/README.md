# Recordings

Raw AgentDeck match recordings should not be committed to git.

Use this directory only for lightweight pointers after execution:

- Hugging Face dataset URI
- dataset revision or snapshot hash
- shard list
- checksum manifest
- curated viewer match IDs, if any are copied into `viewer/matches/`

Planned dataset:

```text
hf://datasets/agentdeck/agentic-edge-strategy-stack-study/
```

The package-local runner writes raw recordings under `agentdeck_runs/` during
execution. Move finalized raw artifacts to external storage before publication.
