# Parse Failure Findings: gpt-4o-mini Controller Adherence

**Date**: 2025-11-10  
**Context**: Experiment 1 initial runs  
**Models Tested**: gpt-4o-mini (temperature=1.0)

## Observation

Repeated parse failures when running Experiment 1 (direct action vs CoT reasoning) with gpt-4o-mini at temperature=1.0.

### Examples
- Seed 100: ReasoningController returned "-" instead of valid action (turn 1)
- Seed 200: ReasoningController returned "HP" instead of valid action (turn 2)

### Pattern
Both failures occurred with **ReasoningController**, which requires format:
```
REASONING: [Your step-by-step thought process]
ACTION: [Your chosen action]
```

The LLM appears to be:
1. Understanding the game (referring to "HP" concept)
2. Not following the exact format specification
3. Extracting invalid tokens as actions

## Hypothesis

High temperature (1.0) combined with more complex response format (REASONING + ACTION) may be causing:
- Format drift
- Creative/unexpected responses
- Token extraction failures from reasoning text

## Mitigation Strategies

1. **Lower temperature**: Try 0.7 or 0.5 for more deterministic responses
2. **Retry policy**: Instead of abort-on-failure, retry with fresh prompt
3. **Model upgrade**: Test with gpt-4o (more capable, better instruction following)
4. **Format simplification**: Test if the direct action controller has fewer failures

## Research Impact

This finding itself is valuable:
- Controller format complexity affects reliability
- Temperature settings critical for structured outputs
- gpt-4o-mini may struggle with multi-part response formats at high temperature

## Next Steps

1. Re-run Experiment 1 with temperature=0.7
2. Compare parse failure rates: direct action vs CoT reasoning
3. If issues persist, escalate to gpt-4o for Experiment 1

---

**Status**: Under investigation  
**Impact**: Blocking Experiment 1 completion
