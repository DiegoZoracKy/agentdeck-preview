# SPEC-ASSEMBLY v0.1.0

## 1. Purpose

Let an AgentDeck caller author one complete execution composition, inspect its
effective configuration without Player calls, bind approval to that exact
composition, and execute it later without a downstream system reconstructing
Games, Players, Controllers, Renderers, Spectators, or session policy.

AgentDeck owns this contract because the assembly is an execution concern.
Research intent, authorization, payment, interpretation, and user-facing
language remain downstream concerns.

## 2. Terminology

- **Assembly**: one or more named AgentDeck runs composed from AgentDeck
  components.
- **PlayerFactory**: a credential-free declaration that creates one Player only
  when execution begins.
- **PreparedAssembly**: the canonical JSON description and SHA-256 identity of
  an Assembly plus its declared source artifacts.
- **AssemblyRun**: one Game, Player roster, session configuration, match count,
  seed, and optional Spectators.

## 3. Public Contract

```python
PlayerFactory(player_type, kwargs)
AssemblyRun(name, game, players, matches=1, seed=None, session=..., spectators=())
Assembly(runs)

prepare_assembly(entrypoint, artifacts=()) -> PreparedAssembly
execute_prepared_assembly(entrypoint, prepared, output_root) -> AssemblyExecution
```

The entrypoint MUST export `create_assembly()` and return `Assembly`. Source
artifacts are explicit paths inside the entrypoint directory; preparation MUST
include the entrypoint and MUST content-address every declared artifact. A
PreparedAssembly stores only paths relative to that directory. Machine-local
absolute paths MUST NOT be part of its canonical description.

## 4. Invariants

1. **AS1 — Complete ownership:** The Assembly owns every AgentDeck component and
   execution choice. Downstream callers MUST NOT recreate or override component
   semantics. The execution host MAY replace only the output root.
2. **AS2 — No Player calls during preparation:** `prepare_assembly` MUST NOT
   instantiate a `PlayerFactory` or invoke a Player provider.
3. **AS3 — Credential-free source:** `PlayerFactory` MUST reject credential
   constructor arguments. Provider credentials are resolved only by Player
   implementations when execution creates Players.
4. **AS4 — Canonical identity:** Preparation MUST produce deterministic canonical
   JSON and a SHA-256 covering the effective Assembly description, engine
   version, entrypoint identity, and all declared artifact identities.
5. **AS5 — Fail before calls:** Execution MUST reload and prepare the sealed
   source before creating any Player. A changed artifact or plan identity MUST
   fail before Player construction or provider calls.
6. **AS6 — Effective description:** The prepared description MUST include every
   run's Game identity/configuration, Player factory class and constructor
   configuration, Controller/Renderer/template configuration, Spectators,
   session policy, matches, and seed. Non-describable values MUST fail
   preparation explicitly.
7. **AS7 — Exact execution:** Execution MUST run every prepared run exactly once
   through `AgentDeck.play`, preserve canonical Records, and return their paths
   with authoritative accumulated Player usage.
8. **AS8 — Stable names:** Run names and Player names MUST be non-empty and
   unique within their scope. Run output directories MUST derive from sanitized
   run names without escaping the supplied output root.
9. **AS9 — No hidden fallback:** Import, validation, construction, execution, or
   Record-count failures MUST surface explicitly. A partial execution MUST NOT
   be represented as complete.
10. **AS10 — Portable identity:** Prepared source and artifact paths MUST be
    relative to the entrypoint directory. Artifacts outside that directory MUST
    be rejected.
11. **AS11 — Stable authored components:** Component classes defined by the
    entrypoint MUST retain the same canonical class identity across preparation
    and execution. Loader-generated randomness MUST NOT enter the plan identity.
    Source-package imports MUST be loaded fresh rather than reused from a prior
    preparation's process-wide module cache.

## 5. Errors

- Missing or invalid entrypoint: `ValueError` before preparation.
- Credential-like Player arguments: `ValueError` before preparation.
- Unsupported or non-JSON-describable configuration: `ValueError` naming the
  offending location.
- Prepared/current identity mismatch: `ValueError` before Player construction.
- Runtime or provider failure: propagate the original execution failure after
  any Records already emitted remain preserved.

## 6. Security Boundary

Assembly entrypoints are executable Python supplied by a trusted caller. This
contract provides identity, deterministic preparation, and execution fidelity;
it is not a sandbox for hostile code. External-user execution requires a
separate process/capability boundary. No downstream wrapper may claim this
contract alone provides hostile-code isolation.

## 7. Testing

- Preparation describes asymmetric Players without instantiating them.
- Identical source prepares to the same identity.
- Source or artifact mutation is rejected before Player construction.
- Credential constructor arguments are rejected.
- Two heterogeneous Controllers execute and appear in canonical Records.
- Multiple runs with distinct Games/configurations execute under one plan.
- Missing Records or incomplete match counts fail explicitly.

See `examples/prepared_assembly.py` for an asymmetric per-Player composition.

## 8. Non-Goals

- Research-question design or statistical inference.
- User approval, accounts, credits, or payment.
- A YAML registry for AgentDeck components.
- Provider credential storage.
- Isolation of hostile Python.
- A second orchestration lifecycle outside `AgentDeck.play`.

## 9. Rationale

AgentDeck already composes arbitrary components through its public Python API.
The missing capability is to preserve that composition across a prepare/approve/
execute boundary. A content-addressed Python entrypoint retains the full public
API without creating a parallel schema that must be extended whenever
AgentDeck gains a component.
