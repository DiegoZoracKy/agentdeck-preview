# Research Log: Discovery Phase

**Date**: 2025-11-08
**Researchers**: Diego, Claude, Codex
**Objective**: Identify what AgentDeck already provides before implementing custom experiment harness

---

## Key Findings

### 1. Statistical Utilities Ready to Use

**Location**: `src/agentdeck/research/statistical.py`

AgentDeck ships with production-ready statistical functions that match our experiment needs:

| Function | Purpose | Our Use Case |
|----------|---------|--------------|
| `calculate_confidence_interval()` | Wilson score interval | Staged sampling checkpoints |
| `statistical_significance()` | Exact binomial test | Early stopping criteria |
| `calculate_effect_size()` | Cohen's h | Result reporting |
| `statistical_test()` | Auto-selects appropriate test | Comparing continuous metrics |

**Decision**: Use these directly instead of implementing from scratch.

---

### 2. Core API Pattern

**Recommendation**: Use transparent primitives, not convenience wrappers.

```python
from agentdeck import AgentDeck, AgentDeckConfig
from agentdeck.research.statistical import calculate_confidence_interval, statistical_significance
from agentdeck.spectators import ProgressDisplay

config = AgentDeckConfig(seed=42)
deck = AgentDeck(
    game=FixedDamageGame(starting_potions=2),
    session=config,
    spectators=[ProgressDisplay()]
)

# Progressive sampling - we control the loop
results = deck.play(players=[player_a, player_b], matches=20)

# Post-hoc analysis
wins_a = sum(1 for m in results.matches if m.winner == player_a.name)
ci_lower, ci_upper = calculate_confidence_interval(wins_a, 20)
p_value = statistical_significance(wins_a, 20, expected_probability=0.5)

# Continue if needed
if p_value >= 0.05:
    batch2 = deck.play(players=[player_a, player_b], matches=10)
```

**Why this approach**:
- Shows users how AgentDeck works (not magic boxes)
- Easy to customize stopping logic
- Visible progressive sampling mechanics

**Note**: `compare_models_progressive()` exists in `agentdeck.research.comparison` but hides mechanics. We'll use the transparent approach for educational value.

---

### 3. Available Spectators

| Spectator | Purpose |
|-----------|---------|
| `ProgressDisplay` | Live progress tracking |
| `StatsTracker` | Aggregate statistics |
| `TokenUsageTracker` | Token and cost tracking |
| Custom | Easy to implement for specific needs |

---

## Implementation Plan

### Phase 0: Baseline Validation
- Script: `scripts/validate_baseline.py`
- Run mirror matches (same model vs itself)
- Verify no first-player advantage
- Quality gate: 50% ± 18% win rate

### Experiments 1-3: Progressive Sampling
- Scripts: `scripts/run_experiment{1,2,3}.py`
- Initial batch: 20 matches
- Checkpoints: +10 matches until significance or budget
- Early stopping: p < 0.05 or max 80 matches

### Analysis
- Use `agentdeck.research.statistical` for effect sizes and CIs
- Log results to markdown for reproducibility

---

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Statistical tools | Use built-in | Production-ready, well-tested |
| API approach | Transparent primitives | Educational, flexible |
| Progressive sampling | Custom loop | Shows mechanics, adaptable |
| Convenience wrappers | Skip | Would hide how AgentDeck works |

---

## Questions to Answer During Execution

1. Is spectator setup clear? Any missing spectators?
2. How much analysis boilerplate is repeated across experiments?
3. What workflows should be documented?

**Rule**: If we write the same code 3+ times → propose reusable component.

---

**Status**: Discovery complete. Ready to write baseline validation script.
