# AgentDeck Scripts

Utility scripts for validation, testing, and experiments.

## Research Validation

**Script**: `research_validate.py`

Validates research manifests and checks that `research/INDEX.md` is up to date.

### Usage:

```bash
python scripts/research_validate.py --research-dir research
```

## Standalone LLM Arena

**Script**: `standalone_llm_arena.py`

Runs a minimal turn-based battle loop directly with OpenAI models, without using
AgentDeck internals. Useful for isolating behavior and comparing against the
original notebook mechanics.

### Usage:

```bash
python scripts/standalone_llm_arena.py \
  --matches 10 \
  --model-a gpt-4o-mini --mode-a action \
  --model-b gpt-4o-mini --mode-b reasoning_action
```

Enable per-turn format reinforcement for each player:

```bash
python scripts/standalone_llm_arena.py \
  --turn-reinforce-a \
  --turn-reinforce-b
```

### Output:

- `standalone_runs/session_YYYYMMDD_HHMMSS_xxxxxx/summary.json`
- `standalone_runs/session_YYYYMMDD_HHMMSS_xxxxxx/records/match_*.json`

Regenerate the index if needed:

```bash
python scripts/research_validate.py --research-dir research --write-index
```

## Research Packager

**Script**: `research_package.py`

Promotes a completed session in `agentdeck_runs/` into a standardized research
package under `research/`.

### Usage:

```bash
python scripts/research_package.py \
  --session-id session_YYYYMMDD_HHMMSS_xxxxxx \
  --question "Your research question here"
```

## Schema v1.3.0 Validation

**Script**: `validate_schema_v1_3.py`

Validates schema v1.3.0 implementation with real LLM calls and replay functionality.

### What it does:

1. **Runs 3 matches** with gpt-4o-mini using FixedDamageGame
2. **Validates recordings**:
   - Checks schema version is "1.3"
   - Verifies no dialogue array present (removed in v1.3)
   - Confirms PM1-PM6 metadata in lifecycle events
3. **Tests replay**: Loads recordings and verifies event stream is complete

### Usage:

```bash
# Set OpenAI API key
export OPENAI_API_KEY=sk-...

# Run validation
python scripts/validate_schema_v1_3.py
```

### Success Criteria:

- ✅ 3 matches complete without errors
- ✅ All recordings have schema version "1.3"
- ✅ PM1-PM6 fields present in lifecycle events
- ✅ No dialogue array duplication
- ✅ Replay reconstructs matches from events only

### Output:

Recordings saved to: `agentdeck_runs/schema_v1_3_validation/session_YYYYMMDD_HHMMSS/`

### What to check:

Open a recording and verify:
```bash
cat agentdeck_runs/schema_v1_3_validation/session_*/records/match_*.json | jq .
```

Look for:
- `"schema_version": "1.3"`
- No `"dialogue"` array at top level
- Events have `"data": {"prompt_text": "...", "prompt_blocks": [...], "response_text": "..."}`

### Example Output:

```
======================================================================
Schema v1.3.0 Validation
======================================================================

📁 Output directory: agentdeck_runs/schema_v1_3_validation/session_20251105_203000

🤖 Creating players (gpt-4o-mini)...

🎮 Running 3 validation matches...
   (This will make real API calls to OpenAI)

✅ Matches completed successfully
   Win rate: 66.7% (Alice)

🔍 Validating Recordings...

  Validating: match_001.json
    ✅ Valid - 42 events, schema v1.3

  Validating: match_002.json
    ✅ Valid - 38 events, schema v1.3

  Validating: match_003.json
    ✅ Valid - 45 events, schema v1.3

🔄 Testing Replay Functionality...
   Found 3 matches to replay

   Replaying match_001...
     - 42 events in recording
     - 4 lifecycle events with PM metadata
     - 4/4 events have prompt_text

   Replaying match_002...
     - 38 events in recording
     - 4 lifecycle events with PM metadata
     - 4/4 events have prompt_text

   Replaying match_003...
     - 45 events in recording
     - 4 lifecycle events with PM metadata
     - 4/4 events have prompt_text

   ✅ Replay validation successful

======================================================================
Validation Summary
======================================================================

✅ Matches executed: 3/3
✅ Recording validation: PASS
✅ Replay functionality: PASS

🎉 Schema v1.3.0 validation SUCCESSFUL!

   - PM1-PM6 metadata embedded in events
   - No dialogue array duplication
   - Replay works from event stream only
   - Single source of truth confirmed
```
