# SPEC-RECORD-MIGRATION: Research Record Migration Utility

> Status: Final
> Version: 1.1.0
> Last Updated: 2026-06-25
> Implementation: Complete (`scripts/migrate_agentic_edge_records_v2.py`)
> Review State: Legacy-approved
> Audience: Contributors running migrations, researchers preserving study artifacts

## 1. Purpose

- Provide a non-destructive utility for migrating AgentDeck match records from Recorder v1.x to v2.0.
- Guarantee that historical study artifacts (e.g. `viewer/matches/`) are never modified in place by default.
- Produce derived v2.0 records with embedded provenance so the relationship to the source artifact is traceable.
- Enforce semantic losslessness: every migration MUST validate that player, action, state, and prompt semantics are preserved before writing any output.

## 2. Scope & Philosophy Alignment

- Aligns with `SPEC.md` §2.4 reproducibility: provenance makes derived records auditable and re-runnable.
- Upholds `CONTRIBUTING.md` "Fail Fast & Noisily": migration refuses protected paths and mismatched flags loudly before processing any records.
- Non-goals: runtime compatibility shims, viewer updates, or schema validation for records already at v2.0 (those are validated, not re-migrated).

## 3. Responsibilities

- **Safe derivation**: write migrated records to `--output-dir`; never touch sources unless `--write` is explicitly supplied.
- **Protected-path enforcement**: refuse `--write` for paths under `viewer/matches/` unless `--force` is also passed.
- **Provenance embedding**: every derived record MUST carry a `migration_provenance` block linking it to its source.
- **Semantic validation**: run `assert_lossless` and `assert_canonical_v2` before any write; abort the record on failure.
- **Dry-run default**: when neither `--output-dir` nor `--write` is supplied, validate only and report without writing.

## 4. Data Structures

### MigrationProvenance (embedded in derived record)

```python
{
    "source_schema_version": str,   # e.g. "1.3"
    "source_match_id": str | None,  # match_id from original record
    "source_artifact": str | None,  # absolute resolved path to source file, or None
    "migration_script": str,        # "scripts/migrate_agentic_edge_records_v2.py"
    "migration_target_schema": str, # "2.0"
    "migrated_at": str,             # UTC ISO 8601, e.g. "2026-06-25T14:00:00Z"
}
```

### v2.0 Gameplay Event Shape (output contract)

Derived gameplay events MUST conform to the canonical v2.0 shape:

```python
{
    "type": "gameplay",
    "data": {
        "match_id": str,
        "mechanic": str,
        "phase_index": int,       # canonical — no turn_index alias
        "player": str,
        "action": {               # always a dict in v2
            "value": str,
            "reasoning": str | None,
            "metadata": dict,     # non-interaction metadata only
        },
        "interaction": {          # prompt/response/usage separated from action
            "prompt_text": str | None,
            "prompt_blocks": list,
            "response_text": str | None,
            "usage_info": dict | None,
            "renderer_output": dict | None,
            "controller_format": str | None,
            "controller_metadata": dict | None,
        },
        "state_before": dict,
        "state_after": dict,
        "turn_context": dict,     # no turn_index
    },
    "context": {                  # no turn_index
        "phase_index": int,
    }
}
```

## 5. Public API

```
scripts/migrate_agentic_edge_records_v2.py [records ...] [options]
```

| Argument | Default | Description |
|---|---|---|
| `records` (positional) | — | Explicit record paths. If omitted, `--root` is scanned. |
| `--root PATH` | `research/2026-04-27-agentic-edge-strategy-stack` | Scan for `match_*.json` under this directory. |
| `--output-dir DIR` | — | Write derived records here. Mutually exclusive with `--write`. |
| `--write` | off | Rewrite records in place. Refused for protected paths without `--force`. |
| `--force` | off | Bypass `viewer/matches/` protection when combined with `--write`. |

- `--output-dir` and `--write` MUST NOT be combined; the script MUST exit non-zero if both are supplied.
- Without any write flag: dry-run mode — validates and reports, no files written.

## 6. Invariants & Guarantees

### 6.1 Safety (RM)
1. **RM1**: Without `--write` or `--output-dir`, the script MUST validate only and MUST NOT write any file.
2. **RM2**: `--output-dir` MUST write derived records to the specified directory and MUST NOT modify source records.
3. **RM3**: `--write` on any path under `viewer/matches/` MUST be refused with a descriptive error unless `--force` is explicitly supplied. The error MUST name the protected path and suggest `--output-dir` as the safe alternative. Protected dirs MUST be anchored to the script's repo root (`Path(__file__).resolve().parents[1]`), not to the process cwd, so the guard holds regardless of where the script is invoked from.
4. **RM4**: `--output-dir` and `--write` MUST be mutually exclusive; supplying both MUST exit non-zero before processing any records.
5. **RM5**: When `--output-dir` is used and two or more source records share the same filename (basename), the script MUST detect the collision before writing any file and exit non-zero with a message identifying the duplicate name(s).

### 6.2 Provenance (PR)
5. **PR1**: Every derived record MUST contain a top-level `migration_provenance` block with all fields from §4.
6. **PR2**: `source_artifact` MUST be the **absolute resolved** path of the source file (`Path.resolve()`) when available, and `null` otherwise. Relative CLI inputs MUST be resolved before embedding so provenance remains valid when derived records move to another repo or bundle.
7. **PR3**: `migrated_at` MUST be a UTC ISO 8601 timestamp at second resolution.

### 6.3 Semantic Integrity (SI)
8. **SI1**: Before writing any output, the script MUST run `assert_lossless` verifying player, action value, reasoning, state_before, state_after, prompt, response, and usage_info are semantically equivalent between source and derived record.
9. **SI2**: Before writing any output, the script MUST run `assert_canonical_v2` verifying that gameplay events contain `action.value`, `interaction`, `phase_index`, and no `turn_index` or legacy `prompt` field.
10. **SI3**: Records already at schema 2.0 MUST be validated via `assert_canonical_v2` and counted as `already_current`; they MUST NOT be re-migrated.

### 6.4 Retired Fields (RF)
11. **RF1**: Derived records MUST NOT contain `turn_index` in any event's `data` or `context`.
12. **RF2**: Derived gameplay events MUST NOT contain a top-level `prompt` field in `data`.
13. **RF3**: Interaction-class metadata keys (`prompt_text`, `response_text`, `usage_info`, etc.) MUST NOT appear in `action.metadata`.

## 7. Data Flow & Interaction

```
CLI invocation
→ collect paths (positional | --root scan)
→ safety checks (mutual exclusivity, protected-path guard)
→ for each record:
    read + parse JSON
    if schema == "2.0": assert_canonical_v2 → count as already_current
    else:
        migrate_match_payload (embed provenance)
        assert_lossless (source vs derived)
        assert_canonical_v2 (derived)
        write to --output-dir / --write / skip (dry-run)
→ report counts
```

**Protected directories** (`PROTECTED_DIRS`): `viewer/matches/` relative to repo root. Records there are historical study artifacts published as part of the Agentic Edge research package and MUST be treated as read-only unless explicitly overridden.

**Canonical derivation workflow** for generating public v2.0 records from study artifacts:
```bash
scripts/migrate_agentic_edge_records_v2.py \
  viewer/matches/study-*.json \
  --output-dir /path/to/product/data/agentic-edge/v2
```

## 8. Error Handling & Edge Cases

| Condition | Behavior |
|---|---|
| `--output-dir` + `--write` both supplied | Exit non-zero before processing any records |
| `--write` on `viewer/matches/` without `--force` (any cwd) | Exit non-zero, name protected path, suggest `--output-dir` |
| `--output-dir` with basename collision across inputs | Exit non-zero before writing any file; name duplicate basenames |
| `assert_lossless` fails | Print path + mismatch description; abort that record; continue others |
| `assert_canonical_v2` fails | Print path + missing/retired fields; abort that record; continue others |
| Source file not found | `FileNotFoundError` propagates |
| Source file is not valid JSON | `json.JSONDecodeError` propagates |

## 9. Examples

```bash
# Dry run: validate records in the Agentic Edge study directory
scripts/migrate_agentic_edge_records_v2.py

# Safe derivation: produce v2.0 copies with provenance
scripts/migrate_agentic_edge_records_v2.py \
  viewer/matches/study-fd-01-s0-failure-flashlite-ao-vs-gpt4omini.json \
  --output-dir derived/v2

# Explicit file list to output-dir
scripts/migrate_agentic_edge_records_v2.py \
  viewer/matches/study-*.json \
  --output-dir /tmp/agentic-edge-v2

# In-place migration for non-protected research records (requires explicit flag)
scripts/migrate_agentic_edge_records_v2.py \
  --root research/2026-04-27-agentic-edge-strategy-stack \
  --write
```

## 10. Testing Strategy

| Focus | Invariants | Verification |
|---|---|---|
| Provenance fields | PR1, PR2, PR3 | Unit: `migrate_match_payload`, assert all provenance keys present and typed |
| `source_artifact` is absolute for relative CLI input | PR2 | CLI: pass relative path; assert `source_artifact` in provenance is absolute |
| Output-dir writes derived, original unchanged | RM1, RM2 | CLI: write to `tmp_path/out`; assert source unchanged, derived has schema 2.0 + provenance |
| Protected path refused from repo cwd | RM3 | CLI: pass absolute `viewer/matches/` path with `--write`; assert non-zero exit |
| Protected path refused from foreign cwd | RM3 | CLI: invoke from `/tmp` with absolute `viewer/matches/` path and `--write`; assert non-zero exit |
| Mutual exclusivity | RM4 | CLI: pass both `--output-dir` and `--write`; assert non-zero exit before processing |
| Basename collision in `--output-dir` | RM5 | CLI: two records with same filename; assert non-zero exit before any file written |
| Dry run does not write | RM1 | CLI: no flags; assert source unchanged and stdout contains "dry run" |
| Canonical v2 shape | SI2, RF1–RF3 | Unit: `assert_canonical_v2` passes on derived; no `turn_index`, no legacy `prompt`, `action.value` present |
| Semantic losslessness | SI1 | Unit: action, state, prompt semantics match between source and derived |

## 11. Design Rationale

- **Safe mode as default**: The most common mistake is accidentally rewriting source artifacts. Making `--output-dir` the standard write path, with `--write` as an explicit opt-in and `--force` as a second gate for protected paths, makes destructive runs require deliberate choices.
- **Provenance in record body**: Derived records are standalone artifacts. Embedding provenance in the record itself (not a sidecar) means any consumer can trace back to the source without the filesystem context of the original derivation.
- **Semantic validation before write**: Schema migration can appear to succeed while silently dropping data. `assert_lossless` compares a key semantic tuple (player, action, state, prompt) rather than doing a structural diff, which would be brittle against field reordering.

## 12. Open Questions / Future Work

- Should `--force` be replaced with a more explicit flag (e.g. `--allow-overwrite-protected`) to make the risk more legible at the call site?
- When new schema versions are introduced (v3.0+), this script should be extended or a new migration script created following the same safety invariants.

## 13. References

- `scripts/migrate_agentic_edge_records_v2.py` — implementation
- `tests/unit/test_migration_script.py` — test coverage
- `SPEC-VIEWER.md` §6.1 RC6 — legacy viewer schema ceiling that motivates derived v2 records
- `SPEC-RECORDER.md` — v1.3 and v2.0 record schemas
- `SPEC-MATCH-SURFACE-PROJECTION.md` — target surface for new viewer consuming v2 records
