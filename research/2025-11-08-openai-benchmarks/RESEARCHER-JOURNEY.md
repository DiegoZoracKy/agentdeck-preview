# Researcher Journey: Completing Analysis Without Re-Running Experiments

> **Experiment**: OpenAI Strategic Benchmarks - Phase 0
> **Date**: 2025-11-08
> **Researchers**: Diego, Claude, Codex
> **Key Learning**: How AgentDeck's design enabled post-hoc analysis without token waste

---

## The Situation

After running **Baseline A** (gpt-4o-mini, 30 matches, $0.0623 cost), we hit a dependency issue:

```
ImportError: Research utilities require scipy and statsmodels
```

The matches had completed successfully, but we couldn't calculate the Wilson confidence intervals or p-values needed for the quality gate assessment.

---

## The Traditional Approach (What We DIDN'T Do)

In a typical research workflow, you might:

1. ❌ Install scipy/statsmodels
2. ❌ Re-run the entire baseline (30 matches)
3. ❌ Wait another 8+ minutes
4. ❌ Spend another $0.06

**Total waste**: Time, tokens, money.

---

## The AgentDeck Approach (What We DID)

Thanks to AgentDeck's design, we took a different path:

### Step 1: Install Dependencies

```bash
pip install scipy statsmodels
```

**Time**: <1 minute
**Cost**: $0

### Step 2: Extract Data from Existing Results

We already had everything we needed from the first run:
- ✅ Win count: 14/30 for player A
- ✅ Session artifacts saved
- ✅ JSON recordings available
- ✅ Full event streams preserved

### Step 3: Run Statistical Analysis

```python
from agentdeck.research.statistical import (
    calculate_confidence_interval,
    statistical_significance
)

# Use data from first run - no API calls needed!
wins_a = 14
matches = 30

ci_lower, ci_upper = calculate_confidence_interval(wins_a, matches, 0.95)
p_value = statistical_significance(wins_a, matches, expected_probability=0.5)

print(f"Wilson CI: [{ci_lower:.1%}, {ci_upper:.1%}]")  # [30.2%, 63.9%]
print(f"p-value: {p_value:.4f}")                        # 0.8555
```

**Time**: <1 second
**Cost**: $0
**Result**: ✅ PASS (46.7% win rate, no significant bias)

### Step 4: Apply Same Approach to Baseline B

When **Baseline B** (gpt-4o, 30 matches) completed, scipy was already installed.

The statistical analysis ran automatically as part of the script - no extra work needed.

**Result**: ✅ PASS (same statistics: 14/30, CI [30.2%, 63.9%], p=0.8555)

---

## Why This Worked

AgentDeck's architecture made post-hoc analysis trivial:

### 1. **Separation of Concerns**

- **Execution layer**: AgentDeck runs matches, tracks outcomes
- **Analysis layer**: `agentdeck.research.statistical` computes statistics
- **They don't need to run together**

### 2. **Rich Session Artifacts**

Every session captures:
```
recordings/session_YYYYMMDD_HHMMSS_xxxxxx/
├── logs/
│   ├── info.log    # Win/loss outcomes logged
│   └── debug.log   # Full execution details
└── records/
    ├── batch_*.json       # Batch metadata
    └── match_*.json × 30  # Individual match recordings
```

### 3. **Accessible Data**

The `MatchResults` object returned by `deck.play()` contains:
- `.matches` - List of all match results
- Each match has `.winner`, `.turns`, `.metadata`
- No need to parse files - programmatic access

### 4. **Replayable Recordings**

If we needed more detail, we could:
- Load recordings via `ReplayEngine`
- Re-analyze any aspect of the matches
- Extract custom metrics
- All without re-running API calls

---

## Concrete Savings

| Scenario | Time | Cost | Result |
|----------|------|------|--------|
| **Re-run baseline** | 8m 41s | $0.0623 | Same data |
| **Use existing data** | <1s | $0 | Same data |
| **Savings** | 8m 40s | $0.0623 | ✅ |

**Multiplied across experiments**: This pattern saves significant time and money.

---

## Lessons for Researchers

### 1. **Trust the Recordings**

AgentDeck's session artifacts are your source of truth:
- You don't need to re-run to analyze
- Recordings preserve full state
- Post-hoc analysis is first-class

### 2. **Install Dependencies Early**

If you know you'll need statistical analysis:
```bash
# Before starting experiments
pip install scipy statsmodels
```

But if you forget? No problem - just analyze existing data.

### 3. **Separate Data Collection from Analysis**

Your experiment scripts should:
- Run matches → save results
- Statistical analysis → separate step (can be post-hoc)

**Don't couple them** unless you have real-time requirements.

### 4. **Leverage Programmatic Access**

```python
# After running matches
results = deck.play(players=[...], matches=30)

# Extract what you need
wins_a = sum(1 for m in results.matches if m.winner == player_a.name)

# Analyze
ci = calculate_confidence_interval(wins_a, len(results.matches))

# Log to research notebook
with open('results.csv', 'a') as f:
    f.write(f"{wins_a},{len(results.matches)},{ci[0]},{ci[1]}\n")
```

No manual counting, no parsing logs - programmatic and reproducible.

---

## Workflow Recommendation

Based on this experience, we recommend:

### Phase 1: Data Collection

Run experiments with **minimal** statistical dependencies:
```python
# Just run matches and save results
deck = AgentDeck(game=..., session=config, spectators=[ProgressDisplay()])
results = deck.play(players=[...], matches=...)

# Extract raw counts
wins_a = sum(1 for m in results.matches if m.winner == player_a.name)
print(f"Raw result: {wins_a}/{len(results.matches)}")
```

### Phase 2: Statistical Analysis

Analyze data **after** collection (or in parallel for other experiments):
```python
# Load existing session or use results object
from agentdeck.research.statistical import calculate_confidence_interval

ci_lower, ci_upper = calculate_confidence_interval(wins_a, matches, 0.95)
p_value = statistical_significance(wins_a, matches, 0.5)

# Document in research log
```

### Phase 3: Iteration (if needed)

If you need more data:
- Run additional matches
- Combine with existing results
- Re-analyze aggregate

**No need to discard previous runs**.

---

## What This Demonstrates

**AgentDeck's Value Proposition for Researchers**:

1. ✅ **Non-destructive workflows** - Existing data is never lost
2. ✅ **Post-hoc flexibility** - Analyze anytime, anywhere
3. ✅ **Cost efficiency** - No token waste from re-runs
4. ✅ **Time savings** - Instant analysis vs. 8+ minute re-runs
5. ✅ **Reproducibility** - Session artifacts preserve everything

---

## Impact on Experiment Schedule

**Original concern**: "If we need scipy after every run, we'll waste hours and $$$"

**Actual outcome**:
- Baseline A: Run once → analyze post-hoc (0 extra cost)
- Baseline B: Scipy already installed → seamless
- Experiments 1-3: Will proceed with no dependency issues

**Time saved**: ~20 minutes (if we had re-run all baselines)
**Cost saved**: ~$0.25 (baseline re-runs + potential experiment re-runs)

---

## Conclusion

**The researcher journey taught us**: AgentDeck is designed for real-world workflows where:
- Dependencies might be missing
- Analysis needs change
- Budget matters
- Time is valuable

By **separating execution from analysis** and **preserving rich session artifacts**, AgentDeck enables:
- Fearless experimentation (run first, analyze later)
- Cost-effective research (no re-runs for trivial issues)
- Flexible workflows (analyze now or later, your choice)

**This is what "research-ready" looks like.** 🎯

---

## Lesson 2: Template Verification is Essential (2025-11-11)

**Context**: After discovering format instruction effects, we attempted to replicate MVP/POC results with "Handshake-Only" configuration. First attempt (F2a-MVP) showed random 52.5/47.5 instead of expected 90/10.

### The Problem

**What we thought we configured**:
```python
GPTPlayer(
    model="gpt-4o-mini",
    temperature=0.7,
    controller=ReasoningController(),
    # No explicit handshake_template/turn_template parameters
)
```

**What we expected**:
- Handshake with format instructions (Handshake-Only regime)
- Turn prompts without format (matching MVP/POC)

**What actually happened**:
- Handshake WITHOUT format instructions (Never regime)
- Turn prompts also without format
- Result: Random 52.5/47.5 (not 90/10 like MVP/POC)

### The Discovery Process

**Step 1: Check session logs** (not just code)
```bash
grep "Respond with:" recordings/session_20251111_004845_cb2c00/logs/debug.log
# Expected: "Respond with: ACTION: <action>"
# Actual: NO MATCHES!
```

**Actual handshake from logs**:
```
Reply with 'OK' if you understand and are ready to begin.
Reply with 'OK' if you understand and are ready to begin.
```

**NO "Respond with: ACTION..."**
**NO "Allowed actions: ATTACK, POTION"**

**Root cause**: Script relied on GPTPlayer defaults, which don't include format instructions in handshake.

### The Fix

**Explicit template configuration** (F2a-MVP-v2):
```python
# EXPLICITLY define templates
handshake_template = (
    "You are playing {game_name}.\\n\\n"
    "{game_instructions}\\n\\n"
    "{player_instructions}\\n\\n"
    "Respond with: ACTION: <action>\\n"
    "Allowed actions: ATTACK, POTION\\n\\n"
    "Reply with 'OK' if you understand and are ready to begin."
)
turn_template = "{game_view}"  # NO format (Handshake-Only)

GPTPlayer(
    model="gpt-4o-mini",
    handshake_template=handshake_template,  # ← EXPLICIT
    turn_template=turn_template,             # ← EXPLICIT
    ...
)
```

**Result**: gpt-4o wins 95% (38/40) ✅ Successfully replicated MVP/POC!

### Key Lessons

**Methodological**:

1. **Trust the logs, not the code**
   - Code shows what you *intended*
   - Logs show what *actually happened*
   - Always verify actual prompts used in experiments

2. **Default behavior is unreliable**
   - Framework defaults may change between versions
   - Defaults may not match your expectations
   - Explicit is better than implicit for reproducibility

3. **Post-execution verification**
   - Check session logs BEFORE drawing conclusions
   - Grep for critical prompt components (format instructions, constraints)
   - One configuration error can invalidate entire experiment

4. **Version control prompt templates**
   - Prompts are code - they should be versioned
   - Track prompt changes alongside code changes
   - Prompt modifications can reverse research conclusions

**Technical**:

1. **Always pass template parameters explicitly**
   ```python
   # BAD - relies on defaults
   GPTPlayer(model="gpt-4o-mini", controller=ReasoningController())

   # GOOD - explicit configuration
   GPTPlayer(
       model="gpt-4o-mini",
       controller=ReasoningController(),
       handshake_template=my_handshake,  # Explicit
       turn_template=my_turn,            # Explicit
   )
   ```

2. **Verification checklist** (post-execution):
   - [ ] Check actual handshake prompts in logs
   - [ ] Check actual turn prompts in logs
   - [ ] Verify format instructions present/absent as intended
   - [ ] Compare with expected configuration
   - [ ] Document any discrepancies

3. **Session logs are ground truth**
   - Logs contain actual prompts sent to LLMs
   - Code only shows construction logic
   - When in doubt, trust the logs

### Impact on Results

**Before verification**:
- Concluded format hypothesis was wrong
- 52.5/47.5 result suggested "no effect at larger N"
- Nearly abandoned format instruction research

**After verification**:
- Discovered misconfiguration (Never vs Handshake-Only)
- Created corrected version (F2a-MVP-v2)
- Result: 95/5 confirms format hypothesis is REAL and ROBUST
- Saved entire research direction from incorrect invalidation

**Cost of error**: Nearly discarded major finding (~90-point performance swing)
**Cost of fix**: 5 minutes of log verification + 1m 30s re-run

### Implications for Reproducibility

**For AgentDeck users**:
- Always verify prompts in session logs before publishing results
- Include actual prompt samples in research documentation
- Provide session IDs for full reproducibility

**For future experiments**:
- Add automated prompt verification to scripts
- Compare intended vs actual configuration
- Flag discrepancies before execution completes

**For research workflow**:
- Post-execution verification is not optional
- Logs are first-class research artifacts
- Trust, then verify (especially templates)

### Updated Workflow

**Recommended experiment workflow**:

1. **Design** experiment configuration
2. **Code** explicit template parameters
3. **Execute** experiment
4. **Verify** actual prompts in logs
5. **Compare** logs vs intended configuration
6. **Analyze** only if verification passes
7. **Document** verification steps in execution log

**Verification script template**:
```bash
# After experiment completes
SESSION_ID="session_20251111_010236_6795b7"

# Check handshake prompts
echo "=== Handshake verification ==="
grep -A 3 "Respond with:" recordings/$SESSION_ID/logs/debug.log | head -10

# Expected output should contain format instructions
# If missing, investigate before analyzing results
```

---

**Next**: With both dependency resilience (Lesson 1) and template verification (Lesson 2) established, we have a robust workflow for reliable, reproducible research with AgentDeck.
