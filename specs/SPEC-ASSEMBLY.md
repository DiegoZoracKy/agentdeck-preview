# SPEC-ASSEMBLY v0.6.0

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
- **AssemblyRecordReceipt**: authoritative binding from one emitted Record to
  its AssemblyRun, match slot, effective seed, Match id, content hash, and path.
- **AssemblyRunExecution**: complete or failed receipt for one AssemblyRun,
  including expected match count and every emitted Record receipt.

## 3. Public Contract

```python
PlayerFactory(player_type, kwargs)
AssemblyRun(name, game, players, matches=1, seed=None, session=..., spectators=())
Assembly(runs)

prepare_assembly(entrypoint, artifacts=()) -> PreparedAssembly
execute_prepared_assembly(
    entrypoint,
    prepared,
    output_root,
    runtime_monitor_factory=None,
) -> AssemblyExecution
```

The entrypoint MUST export `create_assembly()` and return `Assembly`. Source
artifacts are explicit paths inside the entrypoint directory; preparation MUST
include the entrypoint and MUST content-address every declared artifact. A
PreparedAssembly stores only paths relative to that directory. Machine-local
absolute paths MUST NOT be part of its canonical description.

## 4. Invariants

1. **AS1 — Complete ownership:** The Assembly owns every AgentDeck component and
   execution choice. Downstream callers MUST NOT recreate or override component
   semantics. The execution host MAY replace the output root and attach
   runtime-only Monitors that cannot alter the prepared description, gameplay,
   Records, or execution receipt.
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
12. **AS12 — Deep identity immutability:** every value reachable from a
    `PreparedAssembly` MUST either be immutable or be returned as a detached
    copy. A caller MUST NOT be able to change the representation associated with
    an existing `plan_sha256` by mutating nested mappings or sequences.
13. **AS13 — Exact Record receipts:** every emitted Record returned by execution
    MUST bind to one AssemblyRun, zero-based match slot, effective seed,
    `match_id`, SHA-256, and portable path. Record count alone is insufficient.
14. **AS14 — Partial receipt:** host Monitor construction, Player construction, runtime, provider, or Record-count failure MUST
    raise `AssemblyExecutionError` with the best available immutable execution
    receipt. Already emitted Records remain bound to their run/slots and the
    receipt MUST NOT claim completion.
15. **AS15 — Runtime observation:** an optional `runtime_monitor_factory`
    receives the declared run name and returns Monitors for that run. These
    Monitors MUST be additive to authored monitor policy, MUST NOT enter the
    prepared identity, and MUST retain SPEC-MONITOR failure isolation.
16. **AS16 — Custody identity:** each run's declared provider-call custody mode
   is execution policy and MUST enter prepared identity. The concrete backend
   type and path are execution-host capabilities and MUST NOT enter portable
   prepared identity.
17. **AS17 — Custody receipt:** execution receipts MUST disclose required and
   effective provider-call custody. Known usage from committed provider
   responses MUST survive a downstream failure and MUST be deduplicated by
   `call_id` against usage already incorporated into canonical Records.
18. **AS18 — Prepared Game provenance:** every Record emitted by a prepared
    Assembly MUST preserve the same Game implementation descriptor that entered
    that run's prepared identity. Unloading authored source modules between
    preparation and execution MUST NOT degrade known provenance to unresolved.
19. **AS19 — Durable terminal receipt:** before a successful
    `execute_prepared_assembly()` call returns, or an `AssemblyExecutionError`
    escapes, AgentDeck MUST atomically create `assembly-execution.json` in the
    supplied output root with the exact complete or best-available partial
    receipt. A pre-existing receipt MUST fail before Player construction rather
    than be overwritten. Downstream validation failure MUST NOT erase the
    Assembly-to-Record binding that execution already established.

## 5. Errors

- Missing or invalid entrypoint: `ValueError` before preparation.
- Credential-like Player arguments: `ValueError` before preparation.
- Unsupported or non-JSON-describable configuration: `ValueError` naming the
  offending location.
- Prepared/current identity mismatch: `ValueError` before Player construction.
- Runtime, provider, or Record-count failure: raise `AssemblyExecutionError`
  chained from the original failure after preserving emitted Records and an
  incomplete `AssemblyExecution` receipt.

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
- Record receipts preserve exact run, zero-based slot, effective seed, Match id,
  hash, and portable path; duplicate/missing slots fail.
- Injected partial failure returns an incomplete immutable receipt without
  losing already emitted Records.
- Runtime monitor injection observes exact run names, concurrent progress, and
  bounded live turns without changing `plan_sha256`, results, or Records.
- A Game class defined in the entrypoint retains its prepared class-source
  identity in emitted Records after the loader releases authored modules.
- Complete and partial Assembly executions durably preserve their exact receipt
  before returning control to downstream validation; an existing receipt is
  never overwritten.
- Nested mutation attempts cannot change a PreparedAssembly representation or
  leave changed content associated with its existing plan identity.

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

Usage fields named `cost_usd` report known-cost subtotals. A Record with unavailable total cost MUST contribute its `known_cost_usd` without changing that Record's unavailable total into zero. Record-level availability remains authoritative; reconciliation MUST NOT double-count a call present in both Record and journal.
