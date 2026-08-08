# SPEC-AUTHORING-READINESS: External Authoring Gate

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-07
> Implementation: Complete (Wave C4)
> Review State: Consensus-approved
> Audience: Instrument authors, Builder authors, Core maintainers, CI maintainers

## 1. Purpose

Define the minimum machine-enforced boundary that lets an external author produce an
Instrument Package from public AgentDeck contracts without depending on private Core
implementation details or receiving false confidence from advisory-only CI.

## 2. Scope

This contract governs the public authoring example, strict type-check gate, public API
imports, and security/dependency audit jobs. It does not require eliminating all legacy
typing debt inside the Core, provide an untrusted-code sandbox, or define a Builder's
model, prompt, repair policy, or product experience.

## 3. Public Authoring Surface

An external Instrument author may rely on symbols exported from `agentdeck`, the
declarative Instrument Package contract, and the mechanically selected
`instrument-builder` spec profile. A canonical external authoring fixture MUST:

- import extension classes and value types from `agentdeck`, not deep private modules;
- define a Game, deterministic Players, Controller/Renderer composition, scorer, and
  visibility redactor;
- pass strict static checking as consumer code;
- pass the same structural and runtime certifier used for official packages.

`MatchRuntime` and `TurnResult` are public only for authors implementing a genuinely
new mechanic. Ordinary sequential Games SHOULD extend `TurnBasedGame`.

## 4. CI Gates

The local and hosted CI contracts include:

1. deterministic spec-registry validation;
2. unit/integration tests and coverage;
3. strict type checking of the canonical external authoring fixture;
4. a dependency vulnerability audit of runtime dependencies;
5. a static security scan of shipped Python source.

Security tools and their severity policy MUST be named in version-controlled
configuration. A gate may use a reviewed severity threshold, but MUST NOT suppress all
exit codes with `|| true` or equivalent. Any exception MUST identify the rule and carry
an adjacent rationale in version control.

## 5. Invariants

1. **AR1 Public Imports**: The canonical external authoring fixture MUST import its extension API from `agentdeck`; private `agentdeck.core.*` imports are forbidden.
2. **AR2 Strict Consumer Typing**: CI MUST run `mypy --strict` against the canonical external fixture and fail on any error.
3. **AR3 Honest Scope**: Passing AR2 proves the declared external fixture, not the absence of all internal Core typing debt. CI and docs MUST state that boundary.
4. **AR4 Public Runtime Boundary**: Stock mechanics MUST satisfy `SPEC-MATCH-RUNTIME` MR8, and a test MUST fail on private `runtime._console` access under `src/agentdeck/core/mechanics`.
5. **AR5 Runtime Dependency Audit**: CI MUST execute a vulnerability audit against the installed runtime dependency set and fail according to the declared policy.
6. **AR6 Static Security Audit**: CI MUST execute a static security scan over shipped Python source and fail according to the declared severity/confidence policy.
7. **AR7 No Blanket Bypass**: Authoring, dependency, and security gates MUST NOT be made non-blocking through an unconditional success fallback.
8. **AR8 Same Certifier**: A fixture used to prove authoring readiness MUST pass the public Instrument Package certifier; a separate test-only acceptance path is forbidden.

## 6. Testing Strategy

- **AR1**: Parse the fixture imports and reject `agentdeck.core` or relative Core imports.
- **AR2-AR3**: Run strict mypy against the fixture as an external consumer and name the
  limited assurance in CI output.
- **AR4**: scan stock mechanics and exercise every new public runtime helper.
- **AR5-AR7**: run the exact commands locally and in GitHub Actions; tests inspect the
  workflow and local CI script for required blocking commands.
- **AR8**: certify the external fixture through `certify_instrument`.

## 7. Design Rationale

The first Builder needs a narrow contract that is genuinely green more than a broad
claim that hides debt. Strict-checking one complete external instrument catches the
author-facing type failures that matter now, while the existing whole-package mypy
report remains advisory until its legacy errors are retired deliberately. Security
gates likewise prefer explicit, reviewed thresholds over jobs that only install and
import dependencies.

## 8. References

- [SPEC-INSTRUMENT-PACKAGE](SPEC-INSTRUMENT-PACKAGE.md)
- [SPEC-MATCH-RUNTIME](SPEC-MATCH-RUNTIME.md)
- [SPEC-ARTIFACT-SAFETY](SPEC-ARTIFACT-SAFETY.md)
- [CONTRIBUTING](../CONTRIBUTING.md)
