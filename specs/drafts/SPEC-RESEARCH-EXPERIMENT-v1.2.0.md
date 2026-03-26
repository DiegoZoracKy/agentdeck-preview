# SPEC-RESEARCH-EXPERIMENT: Experiment Package Contract

> Status: Draft
> Version: 1.2.0
> Last Updated: 2026-02-18
> Implementation: ⏳ Pending (Phase A only)
> Audience: Research engineers, contributors, experiment authors

## 1. Purpose
- Extend experiment artifacts with a baked-in `statistics` block in `results.json`.
- Keep artifacts useful for both small and large samples by separating:
  - computed metrics (always available when possible), and
  - evidence quality and actionability (explicitly graded).
- Provide statistically grounded recommendations for additional matches.
- Improve first-time researcher onboarding with readable, self-contained package metadata.
- Prevent experiment folder collisions for same-day reruns.

## 2. Scope & Philosophy Alignment
- Aligns with `SPEC.md` research-first and data-driven goals.
- Aligns with `CONTRIBUTING.md` principles:
  - Simplicity: one canonical place for inferential statistics (`results.json.statistics`).
  - Separation of concerns: computation in export/statistical utilities; narrative in markdown remains human-owned.
  - Reproducibility: recommendations are deterministic from recorded data + manifest analysis parameters.
- Non-goals:
  - No automatic narrative generation beyond factual blocks.
  - No changes to live gameplay execution.

## 3. Responsibilities
- Define required `results.json.statistics` schema for completed experiments.
- Define evidence-quality tiers and actionability criteria.
- Define recommendation fields and deterministic calculation contract.
- Define validation requirements for complete experiments.
- Define unique experiment folder naming contract for reruns.
- Define readability constraints for auto-generated factual summaries.
- Define discoverability fields for `research/INDEX.md` and optional viewer links.

## 4. Data Structures

### 4.0 Experiment Identity & Folder Naming
Two identifiers are used:

- `experiment_key` (stable research series slug; reusable across reruns)
- `experiment_id` (unique execution id; MUST match folder name)

Recommended folder naming:
- `research/<experiment_key>__<YYYYMMDD_HHMMSS>_<hash6>/`

Examples:
- `research/performance-methods-benchmark-matrix__20260218_144442_0ac1e0/`
- `research/openai-mini-smoke__20260218_144442_0ac1e0/`

When packaging from `session_id`, tools SHOULD reuse the session suffix
(`YYYYMMDD_HHMMSS_hash6`) to preserve traceability.

### 4.1 `manifest.yaml` (`analysis_plan`) Additions
For experiments using inferential stats, `analysis_plan` SHOULD include:
- `confidence_level` (float, default `0.95`)
- `alpha` (float, default `0.05`)
- `null_win_rate` (float, default `0.5`)
- `power_target` (float, default `0.8`)
- `min_detectable_effect` (float, default `0.15`)  # absolute win-rate delta
- `target_ci_half_width` (float, default `0.10`)
- `min_decisive_for_inference` (int, default `10`)

Recommended manifest additions:
- `experiment_key` (string, stable slug)
- `links.viewer_match` (optional URL/path to a curated replay in viewer UI)

### 4.2 `results.json` Additions
`results.json` MUST include:
- `statistics` (object) for `status in {complete, archived}`.

`statistics` contract:
```json
{
  "method": "exact_binomial",
  "confidence_level": 0.95,
  "alpha": 0.05,
  "null_win_rate": 0.5,
  "n_decisive": 48,
  "comparisons": {
    "player_a": {
      "wins": 30,
      "win_rate": 0.625,
      "ci_95": [0.483, 0.748],
      "p_value": 0.0412,
      "cohens_h": 0.252,
      "effect_label": "small"
    }
  },
  "pairwise_comparisons": {
    "player_a_vs_player_b": {
      "win_rate_a": 0.625,
      "win_rate_b": 0.375,
      "p_value": 0.0412,
      "effect_size": 0.252,
      "is_significant": true
    }
  },
  "quality": {
    "tier": "moderate",
    "is_actionable": true,
    "power_estimate": 0.81,
    "precision_half_width": 0.12,
    "quality_note": "Exploratory to moderate evidence."
  },
  "recommendation": {
    "n_for_80pct_power": 44,
    "n_for_precision": 97,
    "n_recommended_total": 97,
    "additional_matches_recommended": 49,
    "message": "Run ~49 additional decisive matches to reach ±10pp precision @95% CI."
  }
}
```

### 4.3 Small-Sample Behavior
`statistics` MUST still be present for small samples, including `n_decisive < min_decisive_for_inference`.
In that case:
- metrics MAY be computed and reported,
- `quality.tier` MUST communicate low credibility,
- `quality.is_actionable` MUST be `false`,
- recommendation MUST quantify additional matches needed.

### 4.4 Markdown Auto-Facts Readability
Auto-generated factual blocks in `README.md` and `analysis.md` SHOULD follow:
- percentages as formatted percentages (e.g., `100.0%`, not raw ratio object),
- durations rounded for human readability (e.g., `64.2s`),
- cost rounded for display (while full precision remains in `results.json`),
- no raw Python `dict` literals in narrative-facing lines.

### 4.5 `research/INDEX.md` Discoverability Additions
Generated index SHOULD include:
- research question (or concise question summary),
- evidence quality tier (`insufficient|low|moderate|high`),
- optional viewer link when available.

## 5. Invariants
- **RE11**: For `manifest.status in {complete, archived}`, `results.json` MUST include `statistics`.
- **RE12**: `statistics` MUST include method metadata (`alpha`, `confidence_level`, `null_win_rate`, `n_decisive`).
- **RE13**: `statistics.quality` MUST always include `tier`, `is_actionable`, `power_estimate`, and `quality_note`.
- **RE14**: `statistics.recommendation` MUST always include `n_recommended_total` and `additional_matches_recommended`.
- **RE15**: Recommendation math MUST be deterministic from recorded outcomes + `analysis_plan` (or defaults).
- **RE16**: `additional_matches_recommended` MUST be `max(0, n_recommended_total - n_decisive)`.
- **RE17**: Quality tier values are fixed enum: `insufficient | low | moderate | high`.
- **RE18**: `results.json` MUST remain machine-readable and stable; markdown files are narrative overlays, not statistical source-of-truth.
- **RE19**: `experiment_id` MUST be unique and folder-safe; reruns MUST NOT overwrite prior experiment folders.
- **RE20**: For complete experiments, README factual headers MUST be concrete values (no "see manifest.yaml" placeholders).
- **RE21**: Auto-facts lines MUST be human-readable and MUST NOT expose raw Python literal formatting.
- **RE22**: If `links.viewer_match` is provided, it MUST be surfaced in generated README/INDEX entries.

## 6. Quality & Recommendation Contract

### 6.1 Quality Tier Semantics
- `insufficient`: below minimum useful evidence threshold.
- `low`: weak inferential support; not decision-grade.
- `moderate`: usable for directional decisions with caveats.
- `high`: strong inferential support and precision.

### 6.2 Actionability
`quality.is_actionable` SHOULD be `true` only when evidence is at least `moderate`.

### 6.3 Recommendation Model
The recommendation MUST combine two targets:
- **Power target** (`n_for_80pct_power`): based on `min_detectable_effect`, not on fragile observed effect from tiny N.
- **Precision target** (`n_for_precision`): based on desired CI half-width.

`n_recommended_total` MUST be:
`max(min_decisive_for_inference, n_for_80pct_power, n_for_precision)`.

## 7. Validation Rules
`research_validate.py` MUST enforce for complete/archived experiments:
- `results.json.statistics` exists and matches required fields.
- `quality.tier` is a valid enum value.
- `additional_matches_recommended` is non-negative integer.
- if `n_decisive` is very small, `quality.is_actionable` MUST NOT be `true`.
- `experiment_id` matches folder name and follows unique execution naming policy.
- factual markdown headers do not contain known placeholder strings.

## 8. Error Handling
- Missing optional scientific dependencies (e.g., scipy/statsmodels):
  - tool MUST fail noisily or emit explicit conservative fallback mode in `statistics.quality_note`.
- Missing decisive matches (`n_decisive = 0`):
  - `statistics` MUST still be emitted with `quality.tier=insufficient`.
  - recommendation MUST still be computed.
- Duplicate experiment folder on package creation:
  - tool MUST fail fast with collision error and MUST NOT overwrite existing experiment output.

## 9. Testing Strategy
- Unit tests for statistical helpers:
  - power estimate,
  - required sample size for target power,
  - required sample size for target CI half-width.
- Unit tests for export:
  - `results.json.statistics` exists for complete experiments.
  - deterministic output with fixed recordings and fixed analysis_plan.
  - rerun packaging with same id fails deterministically (no overwrite).
- Validator tests:
  - fail when `statistics` missing on complete.
  - fail when invalid `tier`.
  - fail when `additional_matches_recommended < 0`.
  - fail when placeholder factual headers persist in complete package.
- Integration tests:
  - small sample (`n=1`) yields `insufficient`, `is_actionable=false`, positive recommendation.
  - larger sample fixture yields `moderate/high` when thresholds are met.

## 10. Examples

### 10.1 Small Sample (`n=1`)
```json
{
  "statistics": {
    "n_decisive": 1,
    "quality": {
      "tier": "insufficient",
      "is_actionable": false,
      "power_estimate": 0.06,
      "quality_note": "Sample too small for reliable inference."
    },
    "recommendation": {
      "n_recommended_total": 24,
      "additional_matches_recommended": 23,
      "message": "Run ~23 additional decisive matches for minimum decision-grade evidence."
    }
  }
}
```

### 10.2 Decision-Ready Sample
```json
{
  "statistics": {
    "n_decisive": 120,
    "quality": {
      "tier": "high",
      "is_actionable": true,
      "power_estimate": 0.95,
      "precision_half_width": 0.08,
      "quality_note": "High-confidence estimate."
    },
    "recommendation": {
      "n_recommended_total": 120,
      "additional_matches_recommended": 0,
      "message": "Current sample satisfies configured evidence targets."
    }
  }
}
```

## 11. Design Rationale
- Keeps inferential stats close to objective results (`results.json`) instead of scattered outputs.
- Avoids false authority by always exposing quality/actionability explicitly.
- Recommendation based on configurable MDE + precision avoids unstable sample-size advice from tiny N.
- Unique execution ids avoid same-day rerun collisions and keep provenance stable.
- Readable auto-facts improve newcomer comprehension without replacing human interpretation.

## 12. Open Questions
- Should `quality.tier` thresholds be global defaults only, or overridable via `analysis_plan`?
- Should recommendation messaging support localization, or remain English-only in artifacts?
- Should pairwise comparisons be mandatory only for 2-player experiments or for all experiments with `players >= 2`?
- Should `research/INDEX.md` show full question text or a normalized short question field?

## 13. References
- `SPEC-RESEARCH-EXPERIMENT.md` v1.1.0
- `SPEC-RESEARCH.md` v1.1.0
- `CONTRIBUTING.md` (spec-first workflow, clarity/simplicity principles)
- `research/SCHEMA.md`
