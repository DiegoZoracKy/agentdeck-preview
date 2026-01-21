# Spec Compliance Review Plan

**Created**: 2026-01-21
**Purpose**: Systematic review to ensure codebase compliance with specifications and detect spec drift.

---

## 1. Approach

The review is separated into two sequential phases:

| Phase | Question | Output |
|-------|----------|--------|
| **A: Spec → Implementation** | Does the code actually do what the spec says? | Drift report, fix list |
| **B: Spec → Tests** | Do we have automated checks for spec requirements? | Coverage matrix, test backlog |

**Phase A must complete before Phase B.** We need to know what the implementation actually does before assessing whether tests verify the right behavior.

---

## 2. Phase A: Spec → Implementation

### 2.1 Objective

For each numbered invariant in every spec, determine: **Does the code comply?**

### 2.2 Compliance Categories

| Status | Meaning |
|--------|---------|
| ✅ Yes | Implementation fully satisfies the invariant |
| ⚠️ Partial | Implementation partially satisfies; edge cases missing or behavior differs |
| ❌ No | Invariant not implemented or implementation contradicts spec |
| ➖ N/A | Invariant not applicable (deprecated, future work, or spec error) |

### 2.3 Output Format

For each spec, produce a compliance report:

```markdown
## SPEC-{NAME} Implementation Compliance

**Spec Version**: X.Y.Z
**Spec Status**: Draft | Final
**Review Date**: YYYY-MM-DD
**Reviewer**: [name]

### Summary
- Total Invariants: X
- Compliant: Y (Z%)
- Partial: A
- Non-Compliant: B
- N/A: C

### Invariant Compliance Matrix

| ID | Description (abbreviated) | Status | Evidence | Notes |
|----|---------------------------|--------|----------|-------|
| S1 | MUST emit SESSION_START exactly once | ✅ Yes | console.py:142 | |
| S2 | MUST emit SESSION_END exactly once | ⚠️ Partial | console.py:198 | Missing on exception path |
| S3 | ... | ❌ No | | Not implemented |

### Drift Issues

1. **[ID]**: [Description of drift and recommended fix]

### Action Items

- [ ] [Specific fix or spec update needed]
```

---

## 3. Spec Inventory

### 3.1 Priority Classification

| Priority | Criteria |
|----------|----------|
| **P0 - Critical** | Core orchestration, data integrity, reproducibility |
| **P1 - Core** | Primary abstractions, heavily used contracts |
| **P2 - Infrastructure** | Supporting components, tooling |
| **P3 - Extensions** | Research tools, optional features |

### 3.2 Spec Catalog

| Priority | Spec | Version | Status | Invariants | Primary Implementation |
|----------|------|---------|--------|------------|------------------------|
| P0 | SPEC-CONSOLE | 0.5.0 | Final | 43 | `core/console.py` |
| P0 | SPEC-GAME | 0.7.0 | Final | 36 | `core/base/game.py` |
| P0 | SPEC-RECORDER | 1.3.0 | Final | 32 | `core/recorder.py` |
| P0 | SPEC-REPLAY | 1.1.0 | Final | 25 | `core/replay.py` |
| P1 | SPEC-PLAYER | 1.2.0 | Final | 19 | `core/base/player.py` |
| P1 | SPEC-CONTROLLER | 1.3.0 | Draft | 30 | `core/base/controller.py` |
| P1 | SPEC-AGENTDECK | 0.3.0 | Draft | 17 | `core/agentdeck.py` |
| P1 | SPEC-SPECTATOR | 1.0.0 | Final | 21 | `core/base/spectator.py` |
| P2 | SPEC-PROMPT-BUILDER | 0.4.0 | Final | 15 | `core/prompt_builder.py` |
| P2 | SPEC-OBSERVABILITY | 1.1.0 | Final | ~20 | `core/event_bus.py` |
| P2 | SPEC-MONITOR | 1.0.0 | Final | 22 | `monitors/*.py` |
| P2 | SPEC-PRICING | 1.0.0 | Final | 16 | `utils/pricing.py` |
| P2 | SPEC-LLM | 1.0.0 | Draft | 21 | `players/llm_player.py` |
| P2 | SPEC-RENDERER | 0.3.0 | Draft | 8 | `core/base/renderer.py` |
| P3 | SPEC-RESEARCH | 1.1.0 | Final | 32 | `research/*.py` |
| P3 | SPEC-RESEARCH-EXPERIMENT | 1.0.0 | Draft | 8 | `scripts/research_*.py` |
| P3 | SPEC-RESEARCH-PACKAGER | 0.1.0 | Draft | 8 | `research/packager.py` |
| P3 | SPEC-PARALLEL | 1.0.0 | Final | 11 | `core/console.py` |
| P3 | SPEC-MATCH-RUNTIME | 1.0.0 | Draft | 7 | `core/match_runtime.py` |
| P3 | SPEC-GAME-MECHANIC-TURN-BASED | 2.0.0 | Draft | 6 | `core/mechanics/turn_based.py` |

**Total: ~307 invariants across 20 component specs**

---

## 4. Review Execution

### 4.1 Review Order

Execute in priority order. Within each priority, order by invariant count (highest first) to surface systemic issues early.

**Phase A Sequence:**

1. SPEC-CONSOLE (43 invariants)
2. SPEC-GAME (36 invariants)
3. SPEC-RECORDER (32 invariants)
4. SPEC-REPLAY (25 invariants)
5. SPEC-CONTROLLER (30 invariants)
6. SPEC-SPECTATOR (21 invariants)
7. SPEC-PLAYER (19 invariants)
8. SPEC-AGENTDECK (17 invariants)
9. ... (remaining specs by priority)

### 4.2 Review Process Per Spec

1. **Read the spec** - Understand the contract, note all numbered invariants
2. **Locate implementation** - Find primary source files
3. **Trace each invariant** - For each invariant:
   - Search for implementation in code
   - Verify behavior matches spec exactly
   - Note file:line as evidence
   - Flag any deviation
4. **Document findings** - Complete the compliance matrix
5. **Identify drift** - List all non-compliant or partial items with recommended fixes

### 4.3 Drift Resolution

When drift is detected:

| Drift Type | Resolution |
|------------|------------|
| Implementation missing feature | Add implementation to match spec |
| Implementation differs from spec | Determine which is correct; fix code OR update spec |
| Spec outdated (code is correct) | Update spec to match implementation |
| Spec unclear | Clarify spec, then verify implementation |

**Rule**: Every drift item must result in either a code change OR a spec change. No unresolved drift.

---

## 5. Phase B: Spec → Tests (Future)

After Phase A completes, Phase B will:

1. Map each invariant to existing test(s)
2. Identify untested invariants
3. Prioritize test gaps by risk
4. Add tests to existing test files (not a parallel structure)
5. Use clear naming: `test_<component>_<invariant_id>_<description>`

Phase B planning will be detailed after Phase A findings are known.

---

## 6. Deliverables

### Phase A Deliverables

| Deliverable | Location | Description |
|-------------|----------|-------------|
| Per-spec compliance reports | `docs/compliance/SPEC-{NAME}.md` | Detailed invariant matrix |
| Drift summary | `docs/compliance/DRIFT-SUMMARY.md` | Aggregated drift issues |
| Action items | GitHub Issues or `docs/compliance/ACTION-ITEMS.md` | Tracked fixes |

### Success Criteria

Phase A is complete when:

- [ ] All P0 specs reviewed (136 invariants)
- [ ] All P1 specs reviewed (87 invariants)
- [ ] All drift issues documented with resolution path
- [ ] No ❌ (non-compliant) items without action plan

---

## 7. Progress Tracking

| Spec | Status | Compliant | Partial | Non-Compliant | Reviewer | Date |
|------|--------|-----------|---------|---------------|----------|------|
| SPEC-CONSOLE | ✅ Complete | 39 (86.7%) | 3 | 3 | Claude | 2026-01-21 |
| SPEC-GAME | ✅ Complete | 41 (93.2%) | 2 | 1 | Claude | 2026-01-21 |
| SPEC-RECORDER | ✅ Complete | - | - | - | Claude | 2026-01-21 |
| SPEC-REPLAY | ✅ Complete | - | - | - | Claude | 2026-01-21 |
| SPEC-CONTROLLER | ✅ Complete | 26 (89.7%) | 2 | 1 | Claude | 2026-01-21 |
| SPEC-SPECTATOR | ✅ Complete | 19 (90.5%) | 2 | 0 | Claude | 2026-01-21 |
| SPEC-PLAYER | ✅ Complete | 18 (90.0%) | 2 | 0 | Claude | 2026-01-21 |
| SPEC-AGENTDECK | ✅ Complete | 14 (82.4%) | 3 | 0 | Claude | 2026-01-21 |
| SPEC-PROMPT-BUILDER | Not Started | | | | | |
| SPEC-OBSERVABILITY | Not Started | | | | | |
| ... | | | | | | |

---

## Appendix A: Invariant Categories by Spec

### SPEC-CONSOLE (43 invariants)

- Session Lifecycle: S1-S5
- Execution Lifecycle: X1-X4
- Player Order: PO1-PO4
- Deterministic Randomness: R1-R4
- Seed Traceability: T1-T4
- Handshake Lifecycle: H1-H5
- Event Ordering: E1-E5
- Match Metadata: M1-M4
- Spectator Integration: P1-P4
- Logging: L1
- Parse Failure: PF1-PF7
- Error Handling: H1-H4
- Parallel Execution: PE1-PE4

### SPEC-GAME (36 invariants)

- Game State Data: GS1-GS4
- Determinism: DT1-DT3
- Narrative & Views: G15-G16
- Observability: OB1-OB3
- Validation: V1-V2
- Parse Failure Policy: PF1-PF4
- Handshake Template: HT1-HT3
- Information Visibility: IV1-IV5
- Player Ordering: PO1-PO4
- Mechanic Execution: ME1-ME5
- Hook Stability: HS1-HS5
- Lifecycle Hooks: LH1-LH5
- Typed Contracts: TC1-TC3

### SPEC-PLAYER (19 invariants)

- Handshake: HS1-HS4
- Prompt Pipeline: PP1-PP3
- Decision Semantics: DS1-DS4
- Conversation & State: CS1-CS3
- Component Integrity: CI1-CI3
- LLM Provider: LP1-LP2

### SPEC-CONTROLLER (30 invariants)

- Handshake Validation: HV1-HV5
- Format Instructions: FI1-FI3
- Action Parsing: AP1-AP3
- Validation & Errors: VF1-VF4
- Metadata Integrity: MI1-MI2
- Determinism & Safety: DS1-DS2
- Game Binding: GB1-GB6
- Prompt Metadata: PM1-PM4

### SPEC-RECORDER (32 invariants)

- Progressive Persistence: PP1-PP3
- Atomic Writes: AW1-AW3
- Schema Versioning: SV1-SV3
- Metadata Completeness: MC1-MC5
- Seed & Reproducibility: SR1-SR4
- API Usage: UC1-UC6
- Prompt Metadata: PM1-PM6
- Parse Failure: PF1-PF2

### SPEC-REPLAY (25 invariants)

- Input Normalization: IN1-IN3
- Event Parity: EP1-EP3
- Timing & Ordering: TO1-TO3
- Context Reconstruction: CR1-CR2
- Lifecycle Events: LC1-LC5
- Prompt Metadata: PM1-PM3
- State Tracking: ST1-ST2
- Spectator Isolation: SI1-SI4

*(Additional specs to be added as reviews progress)*
