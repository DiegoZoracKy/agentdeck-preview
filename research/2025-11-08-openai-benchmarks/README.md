# OpenAI Strategic Benchmarks

> **Research Question**: How do OpenAI model configurations compare in strategic gameplay?
>
> **Status**: ⏳ Stage 2 Complete (Discovery) - Ready for Execution
>
> **Researcher**: Diego, Claude, Codex
>
> **Started**: 2025-11-08
>
> **Completed**: TBD

---

## At a Glance

**What We're Testing**:
- Does Chain of Thought reasoning help or hurt gameplay?
- How much advantage does gpt-4o provide over gpt-4o-mini?
- Can cheap + reasoning beat expensive + direct action?

**Approach**:
- Progressive sampling with early stopping (Wilson CI)
- Baseline validation to ensure system fairness
- Cost-effectiveness analysis across configurations

**Budget**: ~$4.10 total
**Expected Matches**: 110-230 (depends on early stopping)

---

## Terminology

This research studies reasoning approaches using AgentDeck's controller system. The documentation uses conceptual terminology to emphasize the **capabilities being tested** rather than implementation details:

| Research Concept | AgentDeck Implementation | Description |
|------------------|-------------------------|-------------|
| **Chain of Thought (CoT) reasoning** | `ReasoningController` | Multi-step prompt requiring explicit reasoning before action selection |
| **Direct action selection** | `ActionOnlyController` | Single-step prompt requesting immediate action without explicit reasoning |
| **Format instruction placement** | Template configuration | Where/when format constraints appear in prompts (handshake, turns, both, or never) |

This framing makes the research findings portable across different LLM frameworks and emphasizes that we're studying fundamental AI capabilities (reasoning, instruction-following, inference) rather than framework-specific components.

---

## Quick Navigation

### 📋 Planning (Stage 1)
**Document**: [OPENAI-STRATEGIC-BENCHMARKS.md](../../planning/OPENAI-STRATEGIC-BENCHMARKS.md)

**Key Details**:
- Research questions and hypotheses
- Experiment design (4 phases)
- Statistical framework (Wilson CI, binomial tests)
- Cost estimation and budget
- Success criteria

**Status**: ✅ Complete

---

### 🔍 Discovery (Stage 2)
**Document**: [01-discovery.md](01-discovery.md)

**Key Findings**:
- AgentDeck already has full statistical toolkit (`agentdeck.research.statistical`)
- `compare_models_progressive()` implements our exact progressive sampling approach
- Wilson CI, binomial tests, Cohen's h all ready to use
- Don't need to build custom harness

**Status**: ✅ Complete

---

### ⚙️ Execution (Stage 3)
**Document**: [02-execution.md](02-execution.md)

**Plan**:
- **Phase 0**: Quality Gates (gpt-4o-mini and gpt-4o mirror matches)
- **Experiment 1**: Reasoning Approach Impact (direct action vs CoT reasoning)
- **Experiment 2**: Model Power (mini vs 4o)
- **Experiment 3**: Mixed Strategies (all combinations of CoT reasoning vs direct action)

**Status**: ⏳ Not Started

**Progress**:
- [ ] Phase 0: Baseline A (gpt-4o-mini mirror)
- [ ] Phase 0: Baseline B (gpt-4o mirror)
- [ ] Experiment 1: Reasoning approach comparison
- [ ] Experiment 2: Model comparison
- [ ] Experiment 3A: mini+CoT reasoning vs 4o+direct action
- [ ] Experiment 3B: 4o+CoT reasoning vs mini+direct action

---

### 📊 Analysis (Stage 4)
**Document**: [03-analysis.md](03-analysis.md)

**Will Include**:
- Statistical results (win rates, CIs, p-values, effect sizes)
- Cost-effectiveness analysis
- Visualizations (win rate comparison, convergence, Pareto frontier)
- Key findings and implications
- Limitations and future work

**Status**: ⏳ Pending (awaits execution completion)

---

## Reproducibility

### Environment

**AgentDeck Version**: [git commit hash]
**Python Version**: 3.11+
**Key Dependencies**:
- `scipy` - Statistical tests
- `statsmodels` - Effect sizes
- `openai` - API integration

### Commands

All experiments can be reproduced with these commands:

```bash
# Setup
export OPENAI_API_KEY=your_key_here
export PYTHONPATH=./src

# Phase 0: Quality Gates
python3 scripts/validate_baseline.py --model gpt-4o-mini --matches 30 --seed 42
python3 scripts/validate_baseline.py --model gpt-4o --matches 30 --seed 43

# Experiment 1: Controller Impact
python3 scripts/run_experiment1.py --seed 100

# Experiment 2: Model Power
python3 scripts/run_experiment2.py --seed 200

# Experiment 3: Mixed Strategies
python3 scripts/run_experiment3.py --seed 300

# Generate Analysis
python3 scripts/analyze_results.py
```

### Seeds

All experiments use fixed seeds for reproducibility:
- Baseline A (gpt-4o-mini): `seed=42`
- Baseline B (gpt-4o): `seed=43`
- Experiment 1 (Controller): `seed=100`
- Experiment 2 (Model Power): `seed=200`
- Experiment 3 (Mixed): `seed=300`

### Data Artifacts

**Recordings**: `recordings/openai-benchmarks/`
- Raw event streams for every match
- Replayable with `ReplayEngine`

**Analysis Outputs**: `experiments/01-openai-benchmarks/results/`
- Statistical summaries (CSV/JSON)
- Cost tracking data
- Checkpoint snapshots

**Visualizations**: `experiments/01-openai-benchmarks/plots/`
- Win rate comparisons
- Progressive sampling convergence
- Cost-performance tradeoffs
- Effect size forest plots

---

## Key Results

### Phase 0: Quality Gates

| Baseline | Win Rate A | Wilson CI | p-value | Pass |
|----------|------------|-----------|---------|------|
| gpt-4o-mini | [X.X%] | [[X.X%, X.X%]] | [X.XXX] | ⏳ TBD |
| gpt-4o | [X.X%] | [[X.X%, X.X%]] | [X.XXX] | ⏳ TBD |

**Expected**: 50% ± 18% (no first-player advantage)

### Experiment 1: Reasoning Impact

**Matchup**: gpt-4o-mini direct action vs gpt-4o-mini CoT reasoning

| Metric | Result |
|--------|--------|
| Matches Played | [X] |
| Win Rate A (direct action) | [X.X%] |
| Wilson CI | [[X.X%, X.X%]] |
| p-value | [X.XXX] |
| Cohen's h | [X.XX] ([size]) |
| Total Cost | $[X.XX] |

**Key Finding**: [TBD]

### Experiment 2: Model Power

**Matchup**: gpt-4o-mini direct action vs gpt-4o direct action

| Metric | Result |
|--------|--------|
| Matches Played | [X] |
| Win Rate A (mini) | [X.X%] |
| Wilson CI | [[X.X%, X.X%]] |
| p-value | [X.XXX] |
| Cohen's h | [X.XX] ([size]) |
| Total Cost | $[X.XX] |

**Key Finding**: [TBD]

### Experiment 3: Mixed Strategies

**Matchup A**: mini+CoT reasoning vs 4o+direct action

| Win Rate | Wilson CI | p-value | Cost A | Cost B |
|----------|-----------|---------|--------|--------|
| [X.X%] | [[X.X%, X.X%]] | [X.XXX] | $[X.XX] | $[X.XX] |

**Matchup B**: 4o+CoT reasoning vs mini+direct action

| Win Rate | Wilson CI | p-value | Cost A | Cost B |
|----------|-----------|---------|--------|--------|
| [X.X%] | [[X.X%, X.X%]] | [X.XXX] | $[X.XX] | $[X.XX] |

**Key Finding**: [TBD]

---

## Cost Summary

| Phase | Matches | Total Cost | Cost/Match |
|-------|---------|------------|------------|
| Phase 0: Baselines | 60 | $[X.XX] | $[X.XXX] |
| Experiment 1: Controller | [X] | $[X.XX] | $[X.XXX] |
| Experiment 2: Model | [X] | $[X.XX] | $[X.XXX] |
| Experiment 3: Mixed | [X] | $[X.XX] | $[X.XXX] |
| **Total** | [X] | $[X.XX] | $[X.XXX] |

**Budget**: $4.10
**Actual**: $[X.XX]
**Variance**: [Over/Under] by $[X.XX] ([±X%])

---

## Key Learnings

### About OpenAI Models

**Chain of Thought Reasoning Impact**:
- [Does explicit reasoning help or hurt strategic gameplay?]
- [When is the additional cost justified?]

**Model Power**:
- [How much better is gpt-4o?]
- [Is the cost increase worth it?]

**Cost-Effectiveness**:
- [Optimal configuration for budget users]
- [Pareto frontier insights]

### About AgentDeck

**Research Module**:
- `agentdeck.research.statistical` provides Wilson CI, binomial tests, Cohen's h
- `agentdeck.research.comparison.compare_models_progressive()` implements progressive sampling
- Research utilities are production-ready

**Workflow Insights**:
- [What worked well?]
- [What was friction?]
- [Feature requests]

### Methodological

**Progressive Sampling**:
- [Early stopping effectiveness]
- [Sample size efficiency]
- [Precision vs budget tradeoffs]

**Baseline Validation**:
- [Did it catch any system bias?]
- [Should this be standard practice?]

---

## Next Steps

### Immediate Follow-Ups

1. **[Priority 1]**: [Action item based on results]
2. **[Priority 2]**: [Action item based on results]
3. **[Priority 3]**: [Action item based on results]

### Future Experiments

**Enabled by These Results**:
- Multi-vendor comparison (OpenAI vs Anthropic vs Google)
- More complex games (larger action spaces, longer horizons)
- Adaptive strategies (learning over multiple matches)
- Controller architecture experiments

**Questions Raised**:
1. [New research question from findings]
2. [Edge case to explore]
3. [Hypothesis to test]

### AgentDeck Improvements

**Feature Requests**:
- [Tools that would have helped]
- [API enhancements]
- [Documentation gaps]

**Contributed Back**:
- This experiment narrative (as user documentation)
- [Any scripts or utilities we built]
- [Best practices discovered]

---

## Team Notes

**Collaboration**:
- Planning: Diego, Claude, Codex
- Discovery: Claude (with Codex review)
- Execution: [TBD]
- Analysis: [TBD]

**Decision Log**:
- Chose progressive sampling over fixed n=50 (statistical rigor)
- Added Phase 0 baselines to detect system bias
- Used OpenAI-only to limit scope before multi-vendor
- Followed research logs workflow (first experiment using this structure)

**Retrospective**:
- [What went well?]
- [What could improve?]
- [Lessons for next experiment]

---

## References

**Internal**:
- Planning: [OPENAI-STRATEGIC-BENCHMARKS.md](../../planning/OPENAI-STRATEGIC-BENCHMARKS.md)
- Discovery: [01-discovery.md](01-discovery.md)
- Execution: [02-execution.md](02-execution.md)
- Analysis: [03-analysis.md](03-analysis.md)

**External**:
- Wilson Score Intervals: [Brown et al., 2001](https://doi.org/10.1214/ss/1009213286)
- Sequential Analysis: [Wald, 1945](https://en.wikipedia.org/wiki/Sequential_analysis)
- Cohen's h: [Cohen, 1988](https://en.wikipedia.org/wiki/Cohen%27s_h)

**AgentDeck**:
- Statistical utilities: `agentdeck.research.statistical`
- Progressive comparison: `agentdeck.research.comparison`
- Research workflow: [docs/research/README.md](../README.md)

---

**Last Updated**: 2025-11-08 (Stage 2 Complete - Discovery)
