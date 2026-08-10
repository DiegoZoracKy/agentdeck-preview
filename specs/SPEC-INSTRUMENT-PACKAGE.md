# SPEC-INSTRUMENT-PACKAGE: External Instrument Contract

> Status: Final
> Version: 0.6.0
> Last Updated: 2026-08-10
> Implementation: Complete
> Review State: Consensus-approved
> Audience: Instrument authors, Builder authors, Core maintainers, research tooling

## 1. Purpose

Define a versioned, machine-readable package that lets an external author describe an
AgentDeck Game and prove its capabilities without changing or teaching the Core about
that Game.

## 2. Scope

An Instrument Package MAY contain Game, deterministic fixture, behavioral scorer,
redaction, and viewer code. This spec governs package structure, inspection, validation,
certification, and awarded capability tiers. It does not define research questions,
product promotion, provider credentials, deployment, or code-generation strategy.

Python in a package is executable code and follows `SPEC-ARTIFACT-SAFETY` trust modes.

## 3. Package Layout

The package root contains:

```text
instrument.yaml                 required declarative manifest
<python package>/               package-local implementation
behavioral-profile.yaml         required for evidence_ready
presentation/                   optional viewer assets
```

All declared files and package-local entry points MUST resolve inside the package root.
The structural inspector MUST NOT import any Python module.

The package is a portable source artifact, not a development workspace snapshot. It
MUST exclude transient runtime and tool output: Python bytecode, `__pycache__`,
`.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.coverage`, and `.DS_Store`. This rule
does not constrain authored source, locally bundled browser dependencies, media, WASM,
source maps, or another implementation technology.

## 4. Manifest

`instrument.yaml` is UTF-8 YAML with this canonical shape:

```yaml
schema_version: "1.1"
instrument:
  id: number-duel
  version: "0.1.0"
  title: Number Duel
  summary: A deterministic two-player reference instrument.
game:
  entry_point: number_duel.game:NumberDuelGame
  config:
    target: 3
  config_schema:
    target: {type: integer, minimum: 1, default: 3}
fixture:
  entry_point: number_duel.fixture:create_players
  player_count: 2
  matches: 2
  seed: 42
  max_turns: 20
  expected_winners: [Alpha, Alpha]
evidence:
  scorer_entry_point: number_duel.behavioral:NumberDuelScorer
  profile: behavioral-profile.yaml
presentation:
  redactor_entry_point: number_duel.presentation:visible_state
  viewer: presentation/index.html
  viewer_protocol: agentdeck-stage/1.1
  oracle_paths:
    Alpha: [/private/Beta]
    Beta: [/private/Alpha]
  terminal_oracle_paths:
    Alpha: [/answer]
    Beta: [/answer]
  terminal_oracle_values: ["3"]
claims:
  requested: [runnable, presentable, stage_ready]
```

### Required fields

- `schema_version`: supported manifest schema string. `1.0` remains valid for existing
  packages; `1.1` adds custom Game Stage declarations.
- `instrument.id`: portable Artifact Identifier.
- `instrument.version`: semantic `MAJOR.MINOR.PATCH` string.
- `instrument.title`, `instrument.summary`: non-empty strings.
- `game.entry_point`: package-local `module.path:Symbol` naming a `Game` subclass.
- `game.config`: strict JSON object passed to the Game constructor.
- `game.config_schema`: one declaration per config key; unknown config keys are invalid.
- `fixture.entry_point`: package-local callable returning deterministic fixture Players.
- `fixture.player_count`, `matches`, `seed`, `max_turns`: bounded positive integers.
- `fixture.expected_winners`: one expected value per match; `null` represents a draw.
- `claims.requested`: non-empty subset of the capability tiers in ascending order.

Entry-point functions receive only documented keyword arguments. A fixture callable has
the contract `create_players() -> list[Player]`; the Core supplies no provider
credential or user input. Package authors SHOULD make fixtures independent of network,
clock, and ambient process state. In-process `trusted-local` certification can prove
repeatable observed behavior, but cannot prove that arbitrary Python did not inspect or
use ambient resources. Only a caller-provided `isolated` runtime may make and enforce a
stronger environmental claim.

### Configuration schema

The initial schema supports `string`, `integer`, `number`, `boolean`, and `array`, plus
`default`, `enum`, `minimum`, `maximum`, and `items` where applicable. Every effective
constructor option that changes behavior MUST appear. Certification compares the
manifest config with `Game.describe()["config"]` exactly.

### Optional tier declarations

- `evidence.scorer_entry_point`: package-local `BehavioralScorer` subclass.
- `evidence.profile`: strict YAML profile declaring metric IDs, output pointers,
  generated-record evidence pointers, and calibration expectations.
- `presentation.redactor_entry_point`: callable implementing
  `visible_state(state, player, game_config) -> dict` without mutation or oracle leakage.
- `presentation.viewer`: contained static entry file; absence does not block a generic
  Match Surface.
- `presentation.viewer_protocol`: required with `stage_ready` and currently exactly
  `agentdeck-stage/1.1`.
- `presentation.oracle_paths`: optional mapping from fixture Player name to JSON
  Pointers that MUST be absent from that Player's visible state.
- `presentation.oracle_values`: optional exact strings that MUST be absent from every
  serialized visible state and generated Match Surface.
- `presentation.terminal_oracle_paths`: optional mapping from fixture Player name to
  JSON Pointers that MUST be absent before terminal resolution and MAY appear only in
  the last gameplay frame's `state_after` view and that Player's entry in
  `final_state_views`.
  Their presence at the terminal boundary is permitted, not required.
- `presentation.terminal_oracle_values`: optional exact strings that MUST be absent
  everywhere except inside declared `terminal_oracle_paths` in those terminal views.
  Declaring a value without at least one terminal oracle path is invalid.

Permanent and terminal oracle declarations are distinct. The same path for the same
Player or the same exact value MUST NOT appear in both scopes. Permanent oracle paths
and values remain forbidden from the entire Match Surface, including terminal views.
Terminal declarations do not authorize disclosure in a gameplay `state_before`, any
non-final gameplay `state_after`, handshakes, actions, conclusions, metadata, or another
undeclared field. The last gameplay frame is the final item in the Match Surface
`frames` sequence after replay completes.

### Behavioral profile schema

The profile is UTF-8 YAML containing only strict JSON values:

```yaml
schema_version: "1.0"
profile_id: number_duel_behavioral
profile_version: "0.1.0"
metrics:
  - id: overbid_rate
    output_pointer: /aggregate_metrics/overbid_rate/value
    record_pointers:
      - /0/events/0/data/action/value
    allow_unsupported: false
calibration:
  expected:
    /coverage/matches_total: 2
    /aggregate_metrics/overbid_rate/value: 0.5
```

`metrics` MUST be non-empty with unique IDs. `output_pointer` MUST resolve in scorer
output unless `allow_unsupported` is true and the resolved value is `null`.
`record_pointers` MUST be non-empty and every pointer MUST resolve against the ordered
list of exact generated match payloads. The pointers are evidence anchors; they do not
authorize a semantic conclusion on their own. Every `calibration.expected` pointer MUST
resolve in scorer output and equal the declared strict JSON value exactly.

## 5. Public API

```python
def inspect_instrument(package_root: PathLike) -> InstrumentReport: ...

def validate_instrument(package_root: PathLike) -> InstrumentReport: ...

def certify_instrument(
    package_root: PathLike,
    *,
    trust_mode: str,
    output_dir: PathLike | None = None,
) -> InstrumentReport: ...
```

- `inspect_instrument` performs structural discovery only and never executes code.
- `validate_instrument` performs complete declarative validation only and never executes
  code. Errors are accumulated when continued validation is safe.
- `certify_instrument` requires `trusted-local` or caller-provided `isolated` execution,
  runs only requested tiers whose prerequisites pass, and emits canonical JSON.
- Reports contain schema version, package identity, package content hash, trust mode,
  requested/awarded tiers, checks, errors, warnings, and produced artifact pointers.
- Reports MUST be deterministic for equal package bytes and equal semantic execution.
  Volatile paths, UUIDs, wall-clock values, and durations MUST NOT enter the digest.

CLI:

```text
agentdeck-instrument inspect <package>
agentdeck-instrument validate <package>
agentdeck-instrument certify <package> --trust-mode trusted-local --output <dir>
```

Commands write the report to stdout as canonical JSON. Diagnostic prose goes to stderr.
Success exits `0`; validation/certification failure exits `1`; invocation failure exits
`2`.

## 6. Capability Tiers

### `runnable`

The certifier MUST prove:

- Game and fixture resolve to public Core contracts.
- setup, every visible view, update, events, and final state are strict JSON.
- recorded effective config equals the declared config.
- handshake precedes gameplay and conclusion/match-end ordering is valid.
- the declared match count completes with the declared winner sequence.
- a second execution has the same semantic trace and result under the same seed.
- every recorded match replays with event/data parity.
- all artifacts remain inside the certification output root.
- the report distinguishes observed deterministic completion from environmental
  isolation that the selected trust mode cannot prove.

### `evidence_ready`

Requires `runnable`. The certifier MUST additionally prove:

- every generated Record identifies one exact Game implementation through a complete
  declared closure with `content_addressed` assurance;
- scorer resolves to `BehavioralScorer`, supports the generated payloads, and returns
  strict JSON deterministically;
- every declared metric is present or explicitly marked unsupported;
- every profile record pointer resolves into the exact generated records;
- profile ID/version and calibration expectations match scorer output.

### `presentable`

Requires `runnable`. The certifier MUST additionally prove:

- redactor output is strict JSON, does not mutate canonical state, and is deterministic;
- declared private/oracle fixture values do not appear in player-visible projections;
- a generic Match Surface can project the full lifecycle using only each acting
  Player's declared visible state;
- a declared viewer entry, when present, is contained; custom browser execution is a
  separate `stage_ready` claim.

### `stage_ready`

Requires `presentable`, manifest schema `1.1`, a contained `presentation.viewer`, and
`presentation.viewer_protocol: agentdeck-stage/1.1`. The certifier MUST additionally
prove the portable browser contract in `SPEC-GAME-STAGE`: temporally bounded context and
frame delivery, exact acknowledgement and nonblank output for every frame, contained
offline requests, boundary progression, and error-free desktop/mobile probes.

## 7. Invariants

1. **IP1 Manifest Authority**: Certification MUST use the exact manifest bytes included in the package hash; code MUST NOT silently add or rewrite declarations.
2. **IP2 Structural Non-Execution**: Inspect and validate MUST NOT import modules, run fixtures, invoke constructors, or evaluate package Python.
3. **IP3 Package Containment**: Every package-local path and entry point MUST resolve inside the package root before execution.
4. **IP4 No Game Registry**: Inspection and certification MUST NOT branch on instrument ID, title, Game class name, or module name.
5. **IP5 Public Contracts**: A certified Game, Player, Controller, Renderer, Spectator, and BehavioralScorer MUST satisfy their public AgentDeck types; deep private integration is not a capability.
6. **IP6 Declared Effective Config**: Constructor config, schema defaults, `Game.describe()`, and recorded game config MUST agree exactly.
7. **IP7 Honest Fixture Boundary**: Core MUST supply no provider credential or user input to a certification fixture, MUST test repeated semantic execution, and MUST report when the selected trust mode cannot prove absence of network, clock, or ambient process state.
8. **IP8 Reproducible Execution**: Equal package bytes, config, fixture, and seed MUST yield equal semantic traces and outcomes.
9. **IP9 Replay Parity**: Every runnable certification match MUST replay the same ordered lifecycle and domain event data.
10. **IP10 Strict Evidence**: Manifest, report, state, views, events, records, scorer output, and Match Surface artifacts MUST satisfy strict JSON/YAML scalar rules without coercion.
11. **IP11 Honest Tiers**: A report MUST award only requested tiers whose own checks and prerequisites pass. Partial success MUST remain explicit.
12. **IP12 Evidence Resolution**: Evidence-ready metrics MUST identify pointers that resolve into generated immutable records; prose alone is not evidence.
13. **IP13 Visibility Boundary**: Presentable certification MUST derive views from the declared visibility function, reject permanent oracle fixture leakage, and confine any declared terminal oracle disclosure to its exact terminal paths after the final gameplay action.
14. **IP14 Failure Atomicity**: A failed check MUST NOT overwrite a prior successful report or write outside the certification root.
15. **IP15 Canonical Report**: Equal package content and semantic result MUST produce byte-identical canonical reports after excluding declared volatile artifact locations.
16. **IP16 Stage Declaration**: A stage_ready claim MUST declare schema 1.1, presentable as a prerequisite, a contained presentation entry, and the supported Game Stage protocol.
17. **IP17 Stage Isolation**: Stage certification MUST expose only minimal certified match context and the currently authorized certified frame inside a scripts-only sandbox and MUST reject escaping or external network requests.
18. **IP18 Stage Runtime Conformance**: Stage certification MUST receive an exact protocol acknowledgement and nonblank output for every fixture gameplay frame at desktop and mobile viewports, remain error- and overflow-free, detect visible progression between distinct first and last frames, and preserve a valid Stage error as the immediate certification failure rather than replacing it with a timeout.
19. **IP19 Source-Clean Package**: Inspection, validation, and certification MUST reject transient runtime or tool artifacts before executing package code or hashing them as authored source.
20. **IP20 Evidence-Grade Game Identity**: `evidence_ready` certification MUST require every generated Record to identify one exact Game implementation with `fingerprint_scope: declared_closure`, non-empty sources, and `assurance: content_addressed`; weaker provenance MUST remain valid for `runnable`.

## 8. Failure Handling

- Structural errors include a stable check ID, field path, and actionable message.
- Unknown fields are errors, preventing misspelled declarations from becoming defaults.
- Unsupported schema versions fail before any package code executes.
- `structural` trust mode passed to certification fails before import.
- Runtime exceptions are recorded by check without being converted into certification.
- Failure of one tier blocks dependent tiers but does not erase independent check results.

## 9. Testing Strategy

- One direct test names every `IP` invariant.
- A tiny external fixture outside `src/agentdeck` proves no built-in registry is needed.
- FixedDamage passes the same public path as the external fixture.
- Adversarial variants cover traversal, import side effects during structural validation,
  unknown fields, config drift, non-JSON values, nondeterminism, replay mismatch, scorer
  fabrication, unresolved pointers, oracle leakage, and overstated requested tiers.
- A direct source-clean test covers Python bytecode and known tool/cache paths while a
  locally bundled browser asset remains valid.
- A direct evidence-provenance test removes the declared Game closure, observes
  `runnable`, rejects `evidence_ready`, and then proves runnable-only certification still
  succeeds.

## 10. Rationale

- A manifest is declarative authority; generated code is only an implementation claim.
- Tiering prevents “it runs” from being confused with valid evidence or presentation.
- Fixture execution tests the instrument without the Core supplying provider credentials
  or user input. Under `trusted-local`, repeatability is observed rather than confused
  with OS-level isolation.
- The Core certifies. Builders, products, and humans may author but cannot self-award.
