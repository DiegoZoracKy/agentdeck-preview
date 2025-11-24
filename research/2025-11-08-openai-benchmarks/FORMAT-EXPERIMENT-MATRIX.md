# Format Instruction Experiment Matrix

**Purpose**: Systematically test all combinations of format instruction placement to definitively map their impact on model performance.

**Date Created**: 2025-11-11
**Status**: 📋 Planned
**Researchers**: Diego, Claude, Codex

---

## Motivation

We've discovered that format instruction placement has a massive impact (~67-point swing) on model performance. However, our initial tests revealed an unexpected result:

- **Never** (no format anywhere): gpt-4o wins 90% ✅ Validated
- **Turn-Only** (every turn): gpt-4o-mini wins 77% ✅ Validated
- **Handshake-Only** (once at start): gpt-4o wins 55% ❌ **UNEXPECTED** (expected 90% like MVP/POC)

The Handshake-Only result doesn't match MVP/POC, suggesting:
1. MVP/POC may have actually been "Never" (regression bug)
2. There's another variable we haven't identified
3. Sample size variance (need larger N)

This experiment matrix will systematically test all configurations to resolve these questions.

---

## Research Questions

1. **Primary**: What is the exact relationship between format instruction placement and model win rates?
2. **Secondary**: Does sample size explain the Handshake-Only discrepancy?
3. **Tertiary**: Are there interaction effects between handshake and turn formats?
4. **Quaternary**: How do different format instruction wordings affect results?

---

## Experimental Design

### Independent Variables

**IV1: Handshake Format Instructions**
- **Levels**:
  - `NONE`: No action format in handshake (only "Reply with OK")
  - `BASIC`: "Respond with: ACTION: <action>"
  - `DETAILED`: "Respond with: ACTION: <action>\nAllowed actions: ATTACK, POTION"

**IV2: Turn Format Instructions**
- **Levels**:
  - `NONE`: No format in turns (only game state)
  - `EVERY`: Format on every turn
  - `PERIODIC`: Format every N turns (e.g., every 5 turns)

**IV3: Format Instruction Wording** (exploratory)
- **Levels**:
  - `EXPLICIT`: "Respond with: ACTION: <action>"
  - `IMPLICIT`: "Your move:"
  - `STRUCTURED`: "Reply in JSON: {\"action\": \"ATTACK\"}"

### Dependent Variables

- **Primary**: Win rate (gpt-4o vs gpt-4o-mini)
- **Secondary**: Parse failure rate
- **Tertiary**: Average response length (tokens)
- **Quaternary**: Cost per match

### Control Variables

- Game: FixedDamageGame (max_health=100, attack_damage=20, potion_heal=30, starting_potions=2)
- Controller: ActionOnlyController (both players)
- Temperature: 1.0 (both models)
- Max Turns: 30
- Concurrency: 10 (for speed)
- Sample Size: N=40 per configuration (adequate power for medium effects)

---

## Experiment Matrix

### Phase 1: Core Configurations (3x2 = 6 conditions)

Test all combinations of handshake × turn format:

| Exp ID | Handshake Format | Turn Format | Expected Result | Matches | Seed | Status |
|--------|------------------|-------------|-----------------|---------|------|--------|
| **F1a** | NONE | NONE | gpt-4o wins ~90% | 40 | 700 | 📋 Planned |
| **F1b** | NONE | EVERY | gpt-4o-mini wins ~77% | 40 | 701 | 📋 Planned |
| **F1c** | NONE | PERIODIC (every 5) | TBD | 40 | 702 | 📋 Planned |
| **F2a** | BASIC | NONE | gpt-4o wins ~90%? (MVP/POC) | 40 | 703 | 📋 Planned |
| **F2b** | BASIC | EVERY | TBD (both have format) | 40 | 704 | 📋 Planned |
| **F2c** | BASIC | PERIODIC (every 5) | TBD | 40 | 705 | 📋 Planned |
| **F3a** | DETAILED | NONE | TBD | 40 | 706 | 📋 Planned |
| **F3b** | DETAILED | EVERY | TBD | 40 | 707 | 📋 Planned |
| **F3c** | DETAILED | PERIODIC (every 5) | TBD | 40 | 708 | 📋 Planned |

**Total Phase 1**: 9 configurations × 40 matches = **360 matches** (~$5-7 estimated cost)

### Phase 2: Wording Variations (Optional, based on Phase 1 results)

Test different format instruction wordings on most impactful configurations:

| Exp ID | Handshake Format | Turn Format | Wording Style | Matches | Seed | Status |
|--------|------------------|-------------|---------------|---------|------|--------|
| **F4a** | EXPLICIT | EVERY | Standard | 40 | 710 | 📋 Optional |
| **F4b** | IMPLICIT | EVERY | Natural language | 40 | 711 | 📋 Optional |
| **F4c** | STRUCTURED | EVERY | JSON format | 40 | 712 | 📋 Optional |

**Total Phase 2**: 3 configurations × 40 matches = **120 matches** (~$2-3 estimated cost)

---

## Prompt Templates

### Handshake Templates

**NONE** (current default):
```python
handshake_template = (
    "You are playing {game_name}.\\n\\n"
    "{game_instructions}\\n\\n"
    "{player_instructions}\\n\\n"
    "Reply with 'OK' if you understand and are ready to begin."
)
```

**BASIC**:
```python
handshake_template = (
    "You are playing {game_name}.\\n\\n"
    "{game_instructions}\\n\\n"
    "{player_instructions}\\n\\n"
    "Respond with: ACTION: <action>\\n\\n"
    "Reply with 'OK' if you understand and are ready to begin."
)
```

**DETAILED** (MVP/POC style):
```python
handshake_template = (
    "You are playing {game_name}.\\n\\n"
    "{game_instructions}\\n\\n"
    "{player_instructions}\\n\\n"
    "Respond with: ACTION: <action>\\n"
    "Allowed actions: ATTACK, POTION\\n\\n"
    "Reply with 'OK' if you understand and are ready to begin."
)
```

### Turn Templates

**NONE**:
```python
turn_template = "{game_view}"
```

**EVERY**:
```python
turn_template = "{game_view}\\n\\nRespond with: ACTION: <your_action>"
```

**PERIODIC** (every 5 turns):
```python
# Requires custom logic in prompt_builder to conditionally include format
turn_template_base = "{game_view}"
turn_template_with_format = "{game_view}\\n\\nRespond with: ACTION: <your_action>"
# Use turn_template_with_format when turn_number % 5 == 1
```

---

## Hypotheses

### H1: Format Repetition Effect (Primary)

**Hypothesis**: Repeated format instructions (EVERY turn) favor smaller models by reducing inference load.

**Predictions**:
- NONE/NONE: gpt-4o wins ~90%
- NONE/EVERY: gpt-4o-mini wins ~77%
- Effect size: ~1.3 SD (67-point swing)

**Status**: ✅ Partially validated (Turn-Only confirmed, but Handshake-Only unexpected)

### H2: Handshake Format Persistence (Secondary)

**Hypothesis**: Format instructions given once at handshake provide sufficient guidance for larger models but not smaller models.

**Predictions**:
- BASIC/NONE: gpt-4o wins ~90% (maintains format from handshake)
- BASIC/NONE: gpt-4o-mini struggles (forgets format, parse failures)
- DETAILED/NONE: Similar to BASIC/NONE

**Status**: ❌ Initial test showed 55/45 (random) - UNEXPECTED!

### H3: Interaction Effect

**Hypothesis**: Having format in BOTH handshake and turns may show interaction effects.

**Predictions**:
- BASIC/EVERY: Both models have maximum guidance → smaller differences
- DETAILED/EVERY: Same as BASIC/EVERY (diminishing returns)

**Status**: 🔬 To be tested

### H4: Periodic Reminders

**Hypothesis**: Periodic format reminders (every 5 turns) may find optimal balance between guidance and token cost.

**Predictions**:
- NONE/PERIODIC: Performance between NONE/NONE and NONE/EVERY
- BASIC/PERIODIC: Reinforces handshake format without constant repetition

**Status**: 🔬 To be tested

---

## Execution Plan

### Stage 1: Validate Core Findings (High Priority)

**Goal**: Confirm the established baselines with larger N

1. **F1a** (NONE/NONE): Validate "Never" regime
   - Expected: gpt-4o 90%, mini 10%
   - N=40 (increase from N=20 to reduce variance)
   - Seed: 700

2. **F1b** (NONE/EVERY): Validate "Turn-Only" regime
   - Expected: gpt-4o 23%, mini 77%
   - N=40 (already have N=30, add 10 more)
   - Seed: 701

3. **F2a** (BASIC/NONE): Resolve "Handshake-Only" discrepancy
   - Previous result: 55/45 (N=20, seed=600) - UNEXPECTED
   - New test: N=40, seed=703
   - If still ~55/45 → MVP/POC was truly "Never", not "Handshake-Only"
   - If ~90/10 → Previous result was variance

**Priority**: CRITICAL - These resolve the core question

### Stage 2: Map Interaction Space (Medium Priority)

**Goal**: Understand how handshake × turn formats interact

4. **F2b** (BASIC/EVERY): Both have format
5. **F3a** (DETAILED/NONE): More verbose handshake
6. **F3b** (DETAILED/EVERY): Maximum guidance

**Priority**: HIGH - Completes the core 2×2 matrix

### Stage 3: Explore Periodic Reminders (Lower Priority)

**Goal**: Find cost-optimal format strategy

7. **F1c** (NONE/PERIODIC): Baseline with periodic
8. **F2c** (BASIC/PERIODIC): Handshake + periodic reinforcement
9. **F3c** (DETAILED/PERIODIC): Verbose + periodic

**Priority**: MEDIUM - Practical optimization question

### Stage 4: Wording Variations (Optional)

**Goal**: Test if wording style matters

10. **F4a-c**: Different wording styles

**Priority**: LOW - Only if Phase 1-3 show interesting patterns

---

## Resource Estimates

### Cost Estimates

**Phase 1 (9 configurations × 40 matches)**:
- gpt-4o cost: ~$0.010/match × 180 matches (50% of total) = $1.80
- gpt-4o-mini cost: ~$0.002/match × 180 matches (50% of total) = $0.36
- Mixed cost (average): ~$0.006/match × 360 matches = $2.16
- **Total Phase 1**: ~$2.16-$5.00 (depending on match length)

**Phase 2 (3 configurations × 40 matches)**:
- **Total Phase 2**: ~$0.72-$1.67

**Grand Total**: ~$3-$7 for complete matrix

### Time Estimates (with concurrency=10)

- 40 matches @ 15s/match with concurrency=10 = ~60 seconds per configuration
- Phase 1 (9 configs): ~9 minutes
- Phase 2 (3 configs): ~3 minutes
- **Total time**: ~12-15 minutes for complete execution

---

## Analysis Plan

### Statistical Analysis

**Per Configuration**:
- Win rate with Wilson 95% CI
- p-value (binomial test against 50%)
- Effect size (Cohen's h)
- Parse failure rate

**Cross-Configuration**:
- ANOVA: Handshake × Turn format interaction
- Post-hoc pairwise comparisons (Bonferroni correction)
- Effect size heatmap
- Cost-effectiveness analysis

### Visualizations

1. **Heatmap**: Win rate by Handshake × Turn format
2. **Line plot**: Win rate vs format frequency (None → Periodic → Every)
3. **Scatter**: Cost per match vs win rate (Pareto frontier)
4. **Bar chart**: Parse failure rates by configuration
5. **Forest plot**: Effect sizes with confidence intervals

---

## Success Criteria

### Phase 1 Success Criteria

**Must achieve** (or experiment is inconclusive):
1. ✅ F1a reproduces "Never" baseline (gpt-4o ~90%, p<0.05)
2. ✅ F1b reproduces "Turn-Only" baseline (gpt-4o-mini ~77%, p<0.05)
3. ✅ F2a resolves Handshake-Only discrepancy (either confirms 55% or finds 90%)

**Nice to have**:
4. Significant interaction effect (p<0.05 in ANOVA)
5. Periodic shows intermediate performance (proof of gradient)

### Phase 2 Success Criteria

**Must achieve**:
1. At least one wording variation differs significantly from EXPLICIT (p<0.05)
2. JSON format either works perfectly or fails catastrophically (clear result)

---

## Risk Mitigation

### Risk 1: Budget Overrun

**Mitigation**:
- Phase 1 required, Phase 2 optional
- Can reduce N to 30 if budget tight (loses ~10% power)
- Progressive sampling: stop early if effects are very large

### Risk 2: Inconclusive Results

**Mitigation**:
- N=40 provides 80% power for medium effects (d=0.5)
- Can extend to N=60 if results are borderline
- Document null results clearly (absence of evidence ≠ evidence of absence)

### Risk 3: MVP/POC Discrepancy Unresolved

**Mitigation**:
- If F2a still shows 55%, conclude MVP/POC was "Never" regime
- Check MVP/POC git commit for exact code state
- Accept that we've discovered the true configurations

---

## Next Steps

1. **Create experiment scripts** for each configuration (F1a-F3c)
2. **Run Stage 1** (F1a, F1b, F2a) to resolve core questions
3. **Analyze Stage 1 results** and decide on Stage 2/3 execution
4. **Document findings** in FORMAT-INSTRUCTION-ANALYSIS.md
5. **Update AgentDeck docs** with prompt engineering best practices

---

## Related Documents

- [FORMAT-INSTRUCTION-ANALYSIS.md](FORMAT-INSTRUCTION-ANALYSIS.md) - Current findings and evidence
- [02-execution.md](02-execution.md) - Execution log for all experiments
- [03-analysis.md](03-analysis.md) - Statistical analysis and conclusions
- [OPENAI-STRATEGIC-BENCHMARKS.md](../../planning/OPENAI-STRATEGIC-BENCHMARKS.md) - Original experiment plan

---

## Script Template

```python
#!/usr/bin/env python3
"""
Format Instruction Matrix Experiment: {EXP_ID}

Configuration: Handshake={HANDSHAKE}, Turn={TURN}

Usage:
    python scripts/run_format_matrix_{exp_id}.py [--matches 40] [--seed {SEED}] [--concurrency 10]
"""

# Configuration
EXP_ID = "{exp_id}"
HANDSHAKE_FORMAT = "{handshake}"  # NONE, BASIC, DETAILED
TURN_FORMAT = "{turn}"  # NONE, EVERY, PERIODIC
DEFAULT_SEED = {seed}
DEFAULT_MATCHES = 40
DEFAULT_CONCURRENCY = 10

# Handshake template (varies by config)
handshake_template = # ... based on HANDSHAKE_FORMAT

# Turn template (varies by config)
turn_template = # ... based on TURN_FORMAT

# [Rest of standard experiment script structure]
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-11
**Next Review**: After Stage 1 completion
