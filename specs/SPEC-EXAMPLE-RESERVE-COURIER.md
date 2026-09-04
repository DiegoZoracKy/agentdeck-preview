# SPEC-EXAMPLE-RESERVE-COURIER v1.0.0

## 1. Purpose

Give a new AgentDeck caller a small, example-only path from a single-player Game to an explicit Study, deterministic Evidence and an authored Finding. The example exercises installed public APIs and does not become a core built-in Game.

## 2. Scope and terminology

A courier makes three deliveries with a public energy budget. SAFE costs 1 and earns 2; EXPRESS costs 3 and earns the public reward for the current delivery. A reserve must remain after all deliveries. Optional dispatcher advice is explicitly non-authoritative.

The behavioral question is whether misleading advice changes reserve-feasible planning. A local known-answer policy calibrates the Game and Measure. A small optional provider pilot tests integration, not general AI capability.

## 3. Architecture and data

Game → Player/Controller/Renderer → Console/Record → Study corpus → Measure/Evidence → authored Finding. Spectators observe exact gameplay facts; host Monitors observe progress. Neither authors Research meaning. Source lives under `examples/reserve_courier/`; outputs are outside the authored Study package.

## 4. Invariants

- **RC1**: A match has exactly one Player and at most three deliveries. The Game uses only its supplied seed and state.
- **RC2**: Initial energy is reserve + 5; one EXPRESS is feasible. Rewards are a seeded permutation of 5, 8, 11. The maximum achievable score is 15.
- **RC3**: Losing feasibility ends the Game with score zero. A technical abort remains an incomplete behavioral observation, not an inferred zero-score loss.
- **RC4**: Views contain complete rules and public future rewards; advice changes presentation only, never costs, rewards or transitions.
- **RC5**: Invalid response policy is explicit ABORT_MATCH. No implicit retry, repaired model decision, or single-player FORFEIT is used.
- **RC6**: The optional JSON Controller requires one explicit action; narrative, duplicate keys and unknown actions fail closed. The Renderer does not mutate or enrich hidden state.
- **RC7**: Measures derive only from canonical Records, with exact sources, status and denominators. Calibration must produce the known policy outcome before provider execution.
- **RC8**: Provider execution is explicit, bounded and separately selected. Credentials are host environment inputs and never authored artifacts. A repeated invocation cannot overwrite earlier canonical outputs.
- **RC9**: Finding citations resolve to exact Evidence results; interpretation, phase and limitations remain authored and visible. Offline reproduction invokes no provider.

## 5. Error handling

Bad composition fails before provider calls. Runtime errors preserve partial Records/receipts and known usage. The example surfaces failures without rerunning slots. An incomplete corpus remains unavailable according to SPEC-EVIDENCE.

## 6. User workflow

Run a local calibration, inspect and validate the Study, select the explicit approved scope, execute, inspect/replay Records, analyze the chosen corpus, author a bounded Finding and render its report. The example documentation provides exact commands and explains the difference between a valid artifact and a scientifically established claim.

## 7. Acceptance

Enumerate action sequences to verify the oracle; compare deterministic views and copied states; test invalid JSON and abort handling; run with optional Spectator/Monitor; execute an installed-wheel Study through Finding; compare repeated analysis/report bytes over unchanged Records. Provider smoke uses cheap models, capped interactions and no automatic re-inference.

## 8. Boundaries and rationale

This small example supports SPEC.md §3 composition and execution truth. A universal experiment UI, automatic continuation, statistical significance claims, hidden-reasoning inference, marketplace and public dataset publication are outside its scope. Historical evaluation Records remain unchanged.
