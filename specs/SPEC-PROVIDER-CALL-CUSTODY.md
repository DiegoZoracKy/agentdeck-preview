# SPEC-PROVIDER-CALL-CUSTODY: Provider Call Custody

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-09-03
> Implementation: Complete
> Review State: consensus-approved
> Audience: AgentDeck callers, execution-host implementers, and provider-adapter contributors

## 1. Purpose

Allow an AgentDeck caller to declare how provider-call observations are held
before a Controller or Game can depend on them. A returned provider response may
already represent behavior and billable usage even when a process stops before
the response reaches a canonical Record.

## 2. Scope & Philosophy Alignment

- Preserves execution truth at the provider boundary (`SPEC.md` §1.4).
- Keeps policy separate from mechanism: the execution declares a custody
  requirement while the host supplies a compatible journal.
- Keeps the component narrow: custody and recovery inspection, not Match resume,
  storage orchestration, Research interpretation, or provider-side retention.
- Follows fail-fast semantics: a required durable commit failure stops execution
  before downstream interpretation.

## 3. Terminology

- **Provider call:** one logical Player interaction identified by `call_id`.
- **Provider attempt:** one possible SDK dispatch within a provider call,
  identified by `call_id` plus a positive `attempt_index`.
- **Custody boundary:** the declared point a provider-call fact must cross before
  downstream execution may consume it.
- **Volatile custody:** committed to process memory; process-restart recovery is
  unavailable.
- **Durable custody:** committed to an injected persistent backend before
  downstream use; recovery is supported after process restart on the same
  available storage.
- **ProviderCallJournal:** the narrow mechanism that holds attempt lifecycle and
  returned provider-call facts.
- **Outcome unknown:** dispatch may have reached the provider but no returned
  response or authoritative terminal provider outcome entered custody.

## 4. Data Contract

Each journal entry MUST identify:

```text
schema_version
call_id
attempt_index
state
intent
dispatch                         optional until dispatch begins
result                           only after a response is committed
error                            optional diagnostic
```

`intent` MUST preserve Player, provider/model, lifecycle phase, Match/turn
correlation when available, and the canonical composed-input identity.
`dispatch` MUST preserve the exact bounded SDK-request audit already required by
`SPEC-LLM` PCA1-PCA5. `result` MUST preserve the canonical JSON-safe
provider-call payload and per-call usage known to AgentDeck. It does not claim
to preserve the raw SDK object.

States are facts about local custody:

```text
intent_committed
dispatch_started
response_committed
attempt_failed
```

After recovery, `dispatch_started` without a committed response or authoritative
pre-dispatch failure projects as provider outcome `unknown`.

## 5. Public API

```python
ProviderCallJournal
MemoryProviderCallJournal()
FilesystemProviderCallJournal(directory)
ProviderCallCustodyError
```

The journal contract MUST allow callers to:

- commit an attempt intent before dispatch;
- commit dispatch start before invoking the official SDK;
- commit one canonical returned result before Controller use;
- commit an observed attempt error without upgrading provider outcome certainty;
- inspect entries after execution or restart;
- describe its effective custody mode and backend without exposing local paths in
  prepared identity.

## 6. Invariants & Guarantees

1. **PC1 — Before downstream use:** a provider response MUST cross the declared
   custody boundary before it reaches a Controller, conversation history, Game,
   spectator, or Record.
2. **PC2 — Attempt identity:** every SDK attempt MUST have a stable positive
   `attempt_index` under its logical `call_id`. A retry MUST NOT overwrite an
   earlier attempt.
3. **PC3 — Intent before dispatch:** attempt intent MUST enter custody before the
   official SDK may be invoked.
4. **PC4 — Dispatch truth:** dispatch start MUST enter custody immediately before
   the official SDK invocation. Absence of a later result MUST remain unknown,
   not failed, free, or safe to recreate.
5. **PC5 — Returned response:** a returned response MUST be committed with exact
   canonical Controller response text, bounded provider metadata, and known
   per-call usage before downstream interpretation.
6. **PC6 — Fail closed:** durable custody failure MUST stop the interaction. It
   MUST NOT fall back to memory or trigger another provider attempt.
7. **PC7 — No recovery re-inference:** recovery MUST NOT create an additional
   provider attempt. Configured in-process retry policy remains explicit
   execution policy; every such attempt remains separately identified.
8. **PC8 — No substitution:** a committed result belongs only to its identified
   execution, Player, phase, Match/turn correlation, request identity, and
   attempt. It MUST NOT be reused across another call or Run.
9. **PC9 — Authority boundary:** the journal owns provider-call custody facts
   before Record incorporation. The canonical Record owns Match truth. The
   journal MUST NOT invent Controller results, Game actions, state transitions,
   or Research meaning.
10. **PC10 — Honest volatile mode:** memory custody remains valid and MUST be
    described as volatile with process-restart recovery unavailable.
11. **PC11 — Honest durable mode:** durable mode guarantees process-restart
    recovery only while its configured storage remains available. It MUST NOT
    claim container, host, regional, or provider-retention guarantees it cannot
    verify.
12. **PC12 — JSON safety:** custody payloads MUST satisfy `SPEC-LLM` PCA5 and MUST
    contain no credential, live SDK object, or non-JSON value.
13. **PC13 — Final-state separation:** execution-time provider-call custody and
    final Record persistence are separate guarantees. Neither may stand in for
    the other.

## 7. Data Flow & Interaction

```text
composed input
→ attempt intent
→ dispatch started
→ official provider SDK
→ canonical bounded response
→ custody commit
→ Controller
→ Game / lifecycle consequence
→ Event
→ canonical Record
```

The execution plan declares the required custody mode. The host selects a
backend satisfying that exact mode. Backend type and local path remain host
capabilities; the execution receipt reports the effective mode and backend.

## 8. Error Handling & Recovery

- Failure before `dispatch_started`: no provider dispatch is claimed.
- `dispatch_started` without a terminal committed result: provider outcome and
  cost remain unknown unless independent provider authority establishes them.
- `response_committed` before downstream failure: provider response and known
  usage remain inspectable; the Match may remain incomplete.
- Durable commit failure: raise `ProviderCallCustodyError` without retrying or
  invoking downstream interpretation.
- Recovery may inspect and reconcile committed calls. Resuming a Match from a
  committed response is not part of this version.

## 9. Examples

```python
config = AgentDeckConfig(provider_call_custody="volatile")
deck = AgentDeck(session=config)
```

```python
config = AgentDeckConfig(provider_call_custody="durable")
deck = AgentDeck(session=config)
```

The high-level facade may select the built-in journal matching the declared
mode. Execution hosts may inject another conforming backend without changing
the prepared plan's machine-independent identity.

## 10. Testing Strategy

- Verify volatile and durable commits precede Controller parsing.
- Verify durable write failure prevents Controller use and provider retry.
- Verify each configured retry receives a distinct attempt identity.
- Crash after intent but before dispatch: no provider call claimed.
- Crash after dispatch but before response commit: unknown outcome, no recovery
  inference, incomplete execution.
- Crash after response commit but before Controller: exact response and usage
  recoverable, incomplete execution, no second inference.
- Fail after Controller but before Record: provider call recoverable without a
  fabricated action or state transition.
- Verify sequential and concurrent executions isolate attempt files and retain
  correlation.
- Verify journal/Record usage reconciliation deduplicates by `call_id`.

The implemented acceptance suite covers memory and filesystem custody,
process-restart inspection, unknown post-dispatch outcomes, invalid transitions,
response-commit ordering, fail-closed retry behavior, prepared identity, usage
recovery, Record deduplication, and existing sequential/parallel execution.

## 11. Design Rationale

`ProviderCallJournal` is narrower than a generic observation store and matches
the existing `provider_call` execution vocabulary. Memory and filesystem are
the only built-in backends initially. A response journal does not make Match
resume safe; deterministic resume would require a separately earned contract
covering Game, Player history, Controller, RNG, and precondition identity.

## 12. Non-Goals / Future Work

- Deterministic Match resume after process restart.
- Provider-side storage or retrieval as the primary custody mechanism.
- Database, object-storage, cache, or plugin frameworks.
- Automatic journal compaction or retention policy.
- A claim that the complete high-level AgentDeck facade is filesystem-free.

## 13. References

- `SPEC-LLM`
- `SPEC-ASSEMBLY`
- `SPEC-RECORDER`
- `SPEC-CONSOLE`
