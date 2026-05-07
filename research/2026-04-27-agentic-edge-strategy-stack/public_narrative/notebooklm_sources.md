# NotebookLM Source List

Status: draft source list  
Purpose: use these files to generate slides, summaries, podcasts, or briefings
without mixing unsupported claims into the narrative.

NotebookLM can ingest many raw files directly. This list is therefore a source
checklist, not a copied bundle. Upload the files below as-is.

Avoid `.json` and `.yaml` files for NotebookLM. Use the markdown reports and
support docs that already summarize those artifacts in human-readable form.

Hugging Face links point to the public dataset for canonical study sources.

This directory itself is downstream public-narrative work. It is intentionally
not part of the study dataset. Upload local `public_narrative/*.md` files to
NotebookLM directly when you want narrative scaffolding.

Dataset base:

```text
https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study
```

## Core Upload List

Use these first:

| Source | Local file | Hugging Face file | Use |
| --- | --- | --- | --- |
| Study overview | [`../study_overview.md`](../study_overview.md) | [`metadata/study_overview.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/metadata/study_overview.md) | Final study definition, design, thesis, main findings, limitations. |
| Deterministic results | [`../results.md`](../results.md) | [`reports/results.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/reports/results.md) | Official P2+P3 results, cell rows, seat splits, costs, strictness, warnings. |
| Official analysis | [`../analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md) | [`analysis/.../analysis.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/analysis/analysis_20260428_152909_codex_official_study_analysis/analysis.md) | Official authored interpretation and hypothesis readout. |
| Behavioral metrics | [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md) | [`analysis/.../support/behavioral_metrics_digest.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/analysis/analysis_20260428_152909_codex_official_study_analysis/support/behavioral_metrics_digest.md) | Behavioral story beyond win rate. |
| Prompt audit | [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md) | [`analysis/.../support/protocol_and_prompt_audit.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/analysis/analysis_20260428_152909_codex_official_study_analysis/support/protocol_and_prompt_audit.md) | Exact prompt protocol and what was actually shown to agents. |
| Business explainer | [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md) | [`analysis/.../support/layman_business_explainer.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/analysis/analysis_20260428_152909_codex_official_study_analysis/support/layman_business_explainer.md) | Business-facing explanation. |
| S1 follow-up | [`../analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md`](../analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md) | [`analysis/.../support/s1_frontier_followup.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/analysis/analysis_20260428_152909_codex_official_study_analysis/support/s1_frontier_followup.md) | Why S1 is part of the official FixedDamage ladder. |
| Public findings | [`findings_report.md`](findings_report.md) | Not in study dataset | Condensed public findings narrative. Upload local file directly. |
| Presentation outline | [`presentation_outline.md`](presentation_outline.md) | Not in study dataset | Slide-level structure and claim guardrails. Upload local file directly. |

## Prompt Transparency Sources

Add these when you want NotebookLM to see the actual prompt templates directly:

| Source | Local file | Hugging Face file |
| --- | --- | --- |
| Handshake template | [`../prompts/handshake_default.txt`](../prompts/handshake_default.txt) | [`prompts/handshake_default.txt`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/prompts/handshake_default.txt) |
| S0 action-only turn template | [`../prompts/turn_action_only.txt`](../prompts/turn_action_only.txt) | [`prompts/turn_action_only.txt`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/prompts/turn_action_only.txt) |
| S1 reasoning turn template | [`../prompts/turn_reasoning.txt`](../prompts/turn_reasoning.txt) | [`prompts/turn_reasoning.txt`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/prompts/turn_reasoning.txt) |
| S3 FixedDamage turn template | [`../prompts/turn_fixed_full_stack.txt`](../prompts/turn_fixed_full_stack.txt) | [`prompts/turn_fixed_full_stack.txt`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/prompts/turn_fixed_full_stack.txt) |
| S3 VariableDamage turn template | [`../prompts/turn_variable_full_stack.txt`](../prompts/turn_variable_full_stack.txt) | [`prompts/turn_variable_full_stack.txt`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/prompts/turn_variable_full_stack.txt) |

These are safe to upload as `.txt` files. They are also quoted and explained in
the prompt audit, but adding the raw templates helps prevent paraphrase drift.

## Replay Story Sources

Add these when the generated material should reference the five curated viewer
examples:

| Source | Local file | Hugging Face file |
| --- | --- | --- |
| Viewer curation index | [`../viewer/index.md`](../viewer/index.md) | [`viewer/index.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/viewer/index.md) |
| Study 1 sidecar | [`../viewer/match_0316b96b.md`](../viewer/match_0316b96b.md) | [`viewer/match_0316b96b.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/viewer/match_0316b96b.md) |
| Study 2 sidecar | [`../viewer/match_0430d46c.md`](../viewer/match_0430d46c.md) | [`viewer/match_0430d46c.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/viewer/match_0430d46c.md) |
| Study 3 sidecar | [`../viewer/match_2d1955c8.md`](../viewer/match_2d1955c8.md) | [`viewer/match_2d1955c8.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/viewer/match_2d1955c8.md) |
| Study 4 sidecar | [`../viewer/match_63fd5bc4.md`](../viewer/match_63fd5bc4.md) | [`viewer/match_63fd5bc4.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/viewer/match_63fd5bc4.md) |
| Study 5 sidecar | [`../viewer/match_c2fe0872.md`](../viewer/match_c2fe0872.md) | [`viewer/match_c2fe0872.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/viewer/match_c2fe0872.md) |

Use the hosted Space for visual inspection, but use these markdown sidecars for
the narrative text.

## Optional Methodology Sources

Add these when the generated material needs methodology details:

| Source | Local file | Hugging Face file |
| --- | --- | --- |
| Package README | [`../README.md`](../README.md) | [`metadata/README.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/metadata/README.md) |
| Reproduction notes | [`../reproduction.md`](../reproduction.md) | [`metadata/reproduction.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/metadata/reproduction.md) |
| Recording storage notes | [`../recordings/README.md`](../recordings/README.md) | [`metadata/recordings/README.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/metadata/recordings/README.md) |
| Artifact notes | [`../artifacts/README.md`](../artifacts/README.md) | [`metadata/artifacts/README.md`](https://huggingface.co/datasets/agentdeck/agentic-edge-strategy-stack-study/blob/main/metadata/artifacts/README.md) |

Do not upload `manifest.yaml` or `matrix.yaml` to NotebookLM unless you have a
specific reason. Their important content is already represented in
`study_overview.md`, `README.md`, `reproduction.md`, and `results.md`.

## Files To Avoid As NotebookLM Sources

Avoid these by default:

- `*.json`
- `*.yaml`
- raw recording files
- generated upload manifests and checksums
- full artifact directories

Reason: they are useful for audit and reproduction, but noisy for narrative
generation. Use markdown summaries for NotebookLM and keep JSON/YAML for
verification outside the tool.

## Replay Viewer Source

Use the public Hugging Face Space as visual evidence:

```text
https://huggingface.co/spaces/agentdeck/agentic-edge-viewer
```

Do not ask NotebookLM to infer numbers from screenshots. Use `results.md` and
cell artifacts for numbers, and use the Space for intuition and demonstration.

## Number Guardrails

Use these as the public headline numbers:

- FixedDamage S0 cross-tier: FlashLite-S0-AO 0/48, 0.0% vs GPT4oMini-S0-AO.
- FixedDamage S1 cross-tier: FlashLite-S1-RC 34/48, 70.8% vs GPT4oMini-S0-AO.
- FixedDamage S3 cross-tier: FlashLite-S3-HP 38/48, 79.2% vs GPT4oMini-S0-AO.
- VariableDamage S3 within-model: FlashLite-S3-RISK 41/48, 85.4% vs FlashLite-S0-AO.
- VariableDamage S3 cross-tier: FlashLite-S3-RISK 28/48, 58.3% vs GPT4oMini-S0-AO, caveated.

Always include the VariableDamage caveat:

- p=0.312,
- negligible effect,
- first-player win rate 87.5%,
- FlashLite-S3-RISK won 23/24 as first player but 5/24 as second player.

## Prompt Guardrails

Do not say the model discovered the strategy by itself.

Correct framing:

> The stack made the model execute a better procedure.

Incorrect framing:

> The smaller model invented a superior strategy.

S1 did not include the 20 HP survival rule. S3 did.

## Suggested NotebookLM Prompt

```text
Using the provided AgentDeck study sources, create a presentation narrative for
non-technical business and technical audiences. Explain what was tested, how the
agent behavior changed from S0 to S1 to S3, what the FixedDamage result proves,
why VariableDamage must be caveated, and what this suggests for business AI
workflows. Use only the numbers in results.md and the official analysis. Do not
claim that smaller models are generally better or cheaper.
```
