# AgentDeck Spec Registry Specification

> Status: Final
> Version: 0.2.0
> Last Updated: 2026-08-08
> Implementation: Complete (Wave C5 exact evidence and debt visibility)
> Review State: Consensus-approved
> Audience: Core maintainers, extension authors, automated authoring systems

## 1. Purpose

AgentDeck specifications are the source of truth. This specification makes that
statement mechanically useful by defining a deterministic registry, explicit
authoring profiles, and evidence-based compliance declarations.

The registry does not decide whether prose is correct. It prevents stale indexes,
ambiguous lifecycle state, accidental use of superseded contracts, and unsupported
claims that implementation conforms to a specification.

## 2. Scope

This contract governs every `specs/SPEC-*.md` document. `specs/SPEC.md` is the
navigation hub and is registered separately as a non-contract source.

The following checked-in artifacts are canonical projections:

- `specs/registry.json`: metadata, hashes, links, and invariant IDs;
- `specs/authoring-profiles.json`: closed ordered inputs for bounded authoring tasks;
- `specs/compliance.json`: per-contract assurance declarations and direct evidence;
- generated profile bundles: deterministic derivatives, never independent authority.

## 3. Contract Metadata

Every governed specification MUST declare these blockquote fields before its first
section:

- `Status`: exactly `Final`, `Superseded`, or `Deprecated`;
- `Version`: semantic version `MAJOR.MINOR.PATCH`;
- `Last Updated`: ISO date `YYYY-MM-DD`;
- `Implementation`: a human-readable state beginning with `Complete`, `Partial`,
  `Planned`, or `Not implemented`;
- `Review State`: `Consensus-approved`, `Legacy-approved`, or `Needs review`.

Lifecycle and implementation are independent. A Final contract MAY be planned; an
implemented contract MAY be superseded. Superseded specs MUST name the replacement
with `Superseded By: <filename>` and that target MUST exist and be Final.

## 4. Invariant Identity

An invariant is machine-addressable only when the normative spec declares a unique
identifier and title in one bold span, using the pattern `prefix + number + title`.
Identifiers MUST be unique across active contracts. Prose containing MUST without an
identifier remains normative but cannot support automated assurance until it receives
a stable ID.

Legacy contracts often bold only the identifier and place the title or requirement
outside that span, for example `**RS1**: ...`. The registry MUST expose these as
`unregistered_invariants`. They remain normative, but they are not addressable evidence
keys and prevent the contract from claiming `verified` until normalized. This migration
signal MUST NOT silently invent titles or rewrite source specifications.

## 5. Compliance Evidence

Each Final contract MUST have one entry in `specs/compliance.json`.

Valid status values are:

- `unverified`: no conformity evidence is claimed;
- `partial`: some mapping or direct evidence exists, but the contract is not fully
  verified;
- `verified`: every registered invariant has direct evidence at the declared level;
- `violated`: at least one known implementation conflict is open.

Valid assurance values are ordered but not interchangeable:

- `mapped`: relevant implementation or tests are named;
- `automated`: direct executable tests name the exact invariant ID;
- `semantic`: a recorded spec-to-code review establishes meaning beyond execution.

Executable evidence uses the locator `<repository-relative test path>::<test function>`.
The path and function MUST exist, and the exact invariant ID MUST appear in the test
function name or its docstring. A function MAY cover multiple invariants only when it
names every one explicitly. File-level comments, filenames, neighboring tests, and
grouped contract ranges are not direct evidence.

An entry MUST NOT claim `verified` unless the active contract declares at least one
registered invariant, has no `unregistered_invariants`, and every registered invariant
has direct evidence at the declared level. `automated` and `semantic` are the only
assurance levels eligible for `verified`; `mapped` is never sufficient. Semantic
assurance MUST include a dated review artifact.

## 6. Authoring Profiles

An authoring profile is an ordered allowlist of repository-relative sources plus a
purpose and version. A generator MUST reject missing, duplicate, escaping, or
undeclared sources. It MUST NOT discover additional specs by glob.

Generated bundles MUST contain:

- profile identity and version;
- the registry SHA-256;
- each source path and SHA-256;
- exact source bytes in declared order;
- no wall-clock timestamp, absolute path, environment value, or generated opinion.

Equal repository bytes and profile declarations MUST produce byte-identical output.

## 7. CI Behavior

CI MUST fail when:

- governed metadata is absent or invalid;
- an active invariant ID is duplicated;
- a relative Markdown link does not resolve;
- a profile source is invalid or its generated bundle changes nondeterministically;
- `registry.json` is stale;
- compliance names an unknown contract, invariant, test path, or test function;
- `verified` or `automated` is claimed without direct evidence.

CI validates declarations; it MUST NOT upgrade assurance automatically.

## 8. Invariants

1. **SR1 Complete Metadata**: Every governed spec declares valid lifecycle, semantic version, update date, implementation state, and review state.
2. **SR2 Lifecycle Integrity**: Final is the only active lifecycle; superseded targets resolve to a Final contract and deprecated contracts remain discoverable but inactive.
3. **SR3 Deterministic Registry**: Equal source bytes produce byte-identical `registry.json` with no clock or machine-specific data.
4. **SR4 Unique Invariants**: Every registered invariant ID is unique across active contracts and resolves to its declaring spec.
5. **SR5 Resolved Links**: Every repository-relative Markdown link in a governed spec resolves inside the repository.
6. **SR6 Closed Profiles**: An authoring bundle contains only the ordered sources declared by its profile.
7. **SR7 Deterministic Bundles**: Equal registry, profile, and source bytes produce byte-identical bundles.
8. **SR8 Honest Assurance**: Verified automated assurance requires direct existing tests for every registered invariant.
9. **SR9 No Grouped Shortcut**: A test mapped to one invariant MUST NOT imply coverage of adjacent IDs or a contract range.
10. **SR10 Checked-In Agreement**: CI rejects stale registry and compliance projections instead of silently rewriting them.
11. **SR11 Exact Evidence Locator**: Executable evidence MUST resolve to an existing test function that names the mapped invariant explicitly.
12. **SR12 Non-Vacuous Verification**: A contract with zero registered invariants, any unregistered invariant, or mapped-only assurance MUST NOT claim verified.
13. **SR13 Legacy Gap Visibility**: Invariant-shaped legacy identifiers that are not machine-addressable MUST remain visible in the registry and compliance summary until normalized.

## 9. Compatibility

The initial migration MAY classify legacy contracts as `Legacy-approved` and their
compliance as `partial` or `unverified`. That is an honest baseline, not a waiver.
Future waves improve assurance one invariant at a time.
