# Prior Research Context

Status: draft  
Purpose: technical-report background only

This note explains how earlier committed research packages should be used when
writing the public technical report for `2026-04-27-agentic-edge-strategy-stack`.

## Recommendation

Use the older arc packages as **contextual background**, not as primary
empirical evidence for the flagship study's public claims.

Reason:

- The flagship package has current schema-v3 outputs, per-cell artifacts,
  deterministic `results.md`, behavioral profiles, and curated replay examples.
- The older arc-level aggregate `results.json` files for the March synthesis
  packages are historical package shells with `0` aggregate matches, while their
  authored `analysis.md` files summarize many underlying packages.
- Therefore, the March arc writeups are useful for explaining how the strategy
  idea evolved, but final quantitative claims should come from the flagship
  package unless a later paper pass revalidates the older underlying package
  artifacts directly.

## Contextual Arc

### FixedDamage Arc

Path:

```text
research/2026-03-23-fixed-damage-arc-1/
```

Use for:

- Explaining why FixedDamage became the deterministic "wind tunnel".
- Explaining that earlier work found strategy stacks could repair survival
  logic.
- Explaining that RC, turn reinforcement, HP grounding, and no-potion exit logic
  were explored before the flagship design was simplified.

Do not use for:

- A flagship topline number unless the referenced underlying package artifact is
  directly checked.

### VariableDamage Arc

Path:

```text
research/2026-03-26-variable-damage-arc-1/
```

Use for:

- Explaining why VariableDamage required risk-band grounding instead of exact
  FixedDamage HP thresholds.
- Explaining that RC transferred for FlashLite but TR and fixed HP guidance did
  not transfer cleanly.
- Motivating the flagship VariableDamage S3-RISK design.

Do not use for:

- A flagship cross-tier dominance claim. The flagship VariableDamage frontier
  result is itself caveated by seat effects and non-significance.

### Cross-Game Comparison

Path:

```text
research/2026-03-26-cross-game-comparison-1/
```

Use for:

- Explaining the pre-flagship synthesis:
  - FixedDamage rewards deterministic threshold reasoning.
  - VariableDamage rewards risk management and inventory timing.
  - AgentDeck's behavioral metrics had to evolve with the game.

Do not use for:

- Replacing the flagship package's current artifact trail.

## How To Phrase In The Report

Good:

> Earlier AgentDeck research motivated the flagship ladder by showing that
> deterministic survival failures and stochastic risk failures require different
> grounding. The flagship study then reran a cleaner, current-version design
> with frozen prompts, fixed-N cells, generated artifacts, and replay examples.

Avoid:

> The old arc proves the flagship result.

Avoid:

> The older aggregate `results.json` files are the numeric source for the
> flagship claims.

## Primary Evidence Boundary

For the public report, treat these as primary evidence:

- `../results.md`
- `../results.json`
- `../artifacts/p2_*/results.json`
- `../artifacts/p3_fd_frontier_s1/results.json`
- `../analysis/analysis_20260428_152909_codex_official_study_analysis/`
- curated replay examples in the Hugging Face Space

Treat older research packages as background unless a specific older cell is
opened and rechecked from its own committed artifact.
