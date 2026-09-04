# SPEC-GAME-RESEARCH-PROFILE v0.1.0

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-28
> Implementation: ✅ Implemented
> Review State: approved by maintainer for the Research-axis wave
> Audience: Game authors, Study authors, AgentDeck users, Research implementers

## 1. Purpose

Help a person understand what a Game can plausibly make observable, which
questions remain opportunities, which bounded operationalizations AgentDeck can
currently prepare, and what the Game does not establish.

A Game Research Profile (GRP) translates mechanics into Research possibilities
without claiming that a Game inherently measures a behavioral construct. It is
the discovery bridge between a Game and an explicitly authorized Study.

## 2. Scope & Philosophy Alignment

- **Research-layer artifact:** a GRP references a Game identity; it is never a
  field or responsibility of the execution `Game` contract.
- **Discovery, not authority:** a GRP MAY recommend a Measure or Study template;
  it MUST NOT select analysis or alter executable composition.
- **No overclaiming:** opportunities, resolvable operationalizations, Evidence,
  and Findings have distinct assurance.
- **Independent evolution:** profile knowledge can evolve without rewriting the
  Game, historical Studies, Records, Evidence, or Findings.
- **Human legibility:** the profile answers “what can I investigate here?” before
  requiring the user to understand measurement or experimental-design APIs.

## 3. Terminology

- **Game Research Profile:** versioned authored description of one Game's
  Research affordances and boundaries.
- **Research Opportunity:** plausible question made observable by Game mechanics;
  it is not a validated metric or supported claim.
- **Operationalization:** bounded connection from an Opportunity to an explicit
  Measure declaration and required observables.
- **Prepared Profile:** immutable profile whose Game reference, authored source,
  and Measure references have been content-addressed and resolved.
- **Behavioral Profile:** downstream description of behavior observed in a
  corpus. It is Evidence/Finding output and MUST NOT be confused with a GRP.

## 4. Architecture

```text
Game identity
  -> Game Research Profile
       -> Research Opportunities
       -> explicit Operationalizations -> PreparedMeasure references
       -> boundaries / limitations
  -> person or AI explicitly chooses a question and method
  -> Study -> PreparedAssembly -> Records -> Measure -> Evidence -> Finding
```

The dependency direction is:

```text
Research Profile -> public Game-version and Measure contracts
Game / execution kernel -X-> Research Profile
```

## 5. Authored Contract

`research-profile.yaml` schema version `1`:

```yaml
schema_version: 1
profile:
  id: fixed-damage
  version: 1
  game:
    name: FixedDamageGame
  summary: >-
    Repeated resource decisions under explicit health state and consequential
    recovery trade-offs.
opportunities:
  - id: resource-timing
    question: When does an agent choose to recover?
    mechanism: A scarce POTION competes with ATTACK as health changes.
    observables: [gameplay.action, gameplay.state_before]
    boundaries:
      - Does not establish general risk preference.
operationalizations:
  - id: low-health-recovery-rate
    opportunity: resource-timing
    measure:
      source: measures.yaml
      id: low-health-recovery-rate
    required_observables: [gameplay.action, gameplay.state_before]
    limitations:
      - The health threshold is an authored Measure parameter.
```

Required fields:

- `profile.id`: portable lowercase identifier.
- `profile.version`: positive integer authored revision.
- `profile.game.name`: non-empty logical Game name.
- `profile.summary`: concise human explanation of the instrument.
- `opportunities`: non-empty unique authored Opportunities.

Optional fields:

- `profile.game.implementation_sha256`: exact Game implementation identity when
  the profile is intentionally pinned to one implementation.
- `operationalizations`: zero or more explicit Measure references.
- `boundaries`: profile-wide limitations in addition to per-Opportunity and
  per-Operationalization boundaries.

Every Opportunity contains `id`, `question`, `mechanism`, `observables`, and at
least one `boundary`. Every Operationalization contains `id`, `opportunity`, an
explicit location-neutral Measure reference, `required_observables`, and zero or
more `limitations`.

The profile MUST NOT contain Player, Controller, provider, model, prompt, seed,
match count, Cell selection, Evidence values, Finding text, or executable
overrides.

## 6. Data Structures

- `ResearchOpportunity`: immutable authored question, mechanism, observable ids,
  and boundaries.
- `MeasureReference`: package-relative declaration path plus Measure id.
- `ResearchOperationalization`: Opportunity reference, Measure reference,
  required observables, and limitations.
- `GameResearchProfile`: structurally valid authored content plus source root.
- `PreparedGameResearchProfile`: immutable normalized profile, authored-source
  hash, resolved PreparedMeasure identities, and final `profile_sha256`.

`profile_sha256` covers normalized authored content, the profile source, any
pinned Game implementation identity, and every resolved Measure identity. It
MUST NOT cover Study, Assembly, corpus, Evidence, Finding, timestamps, or host
paths.

## 7. Public API

```python
load_game_research_profile(path: str | Path) -> GameResearchProfile
prepare_game_research_profile(path: str | Path) -> PreparedGameResearchProfile
```

### `load_game_research_profile`

- MUST parse and structurally validate the profile without loading a Game,
  Study, Record, provider, or Measure implementation.
- MUST validate unique ids and Opportunity references.

### `prepare_game_research_profile`

- MUST resolve every Measure reference through `SPEC-MEASURE`.
- MUST content-address profile source and resolved PreparedMeasures.
- AgentDeck orchestration MUST construct no Players and invoke no providers.
- MUST NOT create a Study, select a Measure for a user, or claim calibration.

Custom Measure preparation remains trusted authored Python under
`SPEC-MEASURE`; profile preparation is not a hostile-code sandbox.

## 8. Assurance Vocabulary

- **Opportunity declared:** the author states that mechanics plausibly expose a
  question. AgentDeck has not validated metric or scientific meaning.
- **Operationalization prepared:** its Opportunity exists and its exact Measure
  reference resolves to a PreparedMeasure. This proves executability and
  identity only.
- **Operationalization calibrated:** reserved for a future contract with explicit
  fixtures and acceptance criteria. V0.1 MUST NOT emit this assurance.
- **Finding supported:** belongs only to Evidence/Finding contracts; never to a
  Game or GRP.

## 9. Invariants & Guarantees

1. **GR1 — Research boundary:** execution-kernel modules MUST NOT import GRP
   types or profile data.
2. **GR2 — Discovery only:** loading/preparing a GRP MUST NOT create a Study,
   select a Measure for analysis, or execute a Game.
3. **GR3 — No duplicate authority:** a GRP MUST NOT define or override Assembly,
   Study, corpus, or Measure parameters.
4. **GR4 — Explicit limitation:** every Opportunity MUST name at least one thing
   its mechanics do not establish.
5. **GR5 — Exact references:** every Operationalization references exactly one
   declared Opportunity and one explicit Measure declaration/id.
6. **GR6 — Honest support:** successful preparation means references and
   identities resolved; it does not mean scientific validity or calibration.
7. **GR7 — Independent identity:** changing a GRP MUST NOT change Game,
   PreparedStudy, RecordCorpus, Measure, Evidence, or Finding identity.
8. **GR8 — Historical stability:** changing a Measure reference or profile text
   creates a new profile identity and never rewrites historical artifacts.
9. **GR9 — No outcome ownership:** Evidence and Findings MAY cite the profile
   revision that informed a Study, but MUST NOT be stored in or attributed to
   the Game itself.
10. **GR10 — Location-neutral Measures:** Operationalizations use the same
    Measure declaration contract as a Study package, built-in catalog, or
    explicit caller path; no Study-exclusive Measure namespace exists.

## 10. Error Handling

| Condition | Required outcome |
|---|---|
| Missing/invalid profile YAML | fail with source and field location |
| Duplicate Opportunity/Operationalization id | fail before Measure preparation |
| Unknown Opportunity reference | fail before Measure preparation |
| Missing or changed Measure source | fail preparation with Operationalization id |
| Executable/Study/Evidence field present | reject as duplicate authority |
| Profile/Measure changes after preparation | new identity; stale prepared object is not reused |

No error path may convert an unresolved Operationalization into an Opportunity
silently or label authored possibility as mechanically supported.

## 11. Testing Strategy

| Invariants | Behavioral proof |
|---|---|
| GR1–GR3 | Core import remains independent; forbidden executable fields fail |
| GR4–GR5 | missing boundary and unknown Measure/Opportunity references fail |
| GR6 | prepared output says `prepared`, never calibrated/validated behavior |
| GR7–GR8 | profile changes alter only profile identity; historical inputs unchanged |
| GR10 | same Measure declaration resolves from GRP and direct Measure API |

Acceptance requires:

- a FixedDamage profile with resource-timing and information-sensitivity
  Opportunities;
- one prepared Operationalization referencing a deterministic Measure;
- a second single-Player/no-winner profile using the same public types;
- no Game subclass or execution-kernel type gaining a Research field.

## 12. Design Rationale

- **Profile outside Game:** mechanics remain reusable execution truth while
  Research knowledge evolves independently.
- **Opportunity before Measure:** people can discover worthwhile questions
  without pretending every affordance has a validated operationalization.
- **Prepared, not calibrated:** content-addressed resolution is mechanically
  testable; scientific validity is not.
- **Measure references, not copies:** the GRP aids discovery without becoming a
  second analysis authority.

## 13. Non-Goals / Future Work

- automatic Study generation or Measure selection;
- natural-language claim generation;
- calibration/certification protocol;
- Evidence or prior-result registry inside the profile;
- UI layout, search ranking, marketplace, or publication;
- generalized behavioral ontology.

## 14. References

- [`SPEC-RESEARCH`](SPEC-RESEARCH.md)
- [`SPEC-GAME`](SPEC-GAME.md)
- [`SPEC-GAME-VERSION-PROVENANCE`](SPEC-GAME-VERSION-PROVENANCE.md)
- [`SPEC-MEASURE`](SPEC-MEASURE.md)
- [`SPEC-STUDY`](SPEC-STUDY.md)
