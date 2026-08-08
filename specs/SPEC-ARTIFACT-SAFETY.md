# SPEC-ARTIFACT-SAFETY: Artifact Identity, Containment, And Trust

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-07
> Implementation: Complete (Wave C0)
> Review State: Consensus-approved
> Audience: Core contributors, package authors, artifact pipeline maintainers

## 1. Purpose

Define the cross-cutting safety contract for identifiers that become filesystem paths,
artifact writes, strict JSON evidence, and executable extension code.

## 2. Scope & Philosophy Alignment

This contract governs Core-owned writes for recordings, Match Surfaces, Research
Packages, and Instrument Packages. It complements component schemas; it does not define
their domain fields. It follows the fail-fast and reproducibility principles in
`SPEC.md` and the untrusted-artifact threat model in `SECURITY.md`.

## 3. Responsibilities

- Validate any external identifier before using it as a filename or path segment.
- Prove that every resolved output remains inside its declared root.
- Preserve canonical evidence as strict JSON without fallback string conversion.
- Distinguish structural package inspection from execution of Python extensions.

## 4. Data Structures

### Artifact Identifier

A portable artifact identifier is a non-empty string of at most 128 characters that:

- begins with an ASCII letter or digit;
- contains only ASCII letters, digits, `.`, `_`, and `-`;
- is not `.` or `..`;
- contains no path separator, drive prefix, control character, or NUL byte.

Existing artifact payloads MAY contain historical display identifiers. Any identifier
used for a new Core-owned filesystem write MUST satisfy this contract.

### Trust Mode

Executable extension operations declare one of:

- `structural`: parse and validate data files only; import and execution are forbidden.
- `trusted-local`: Python imports and fixtures MAY execute in the current process. The
  caller asserts that the package is trusted local code.
- `isolated`: Python imports and fixtures execute in a caller-provided isolated process.
  The Core may define the protocol but does not claim to provide an OS sandbox.

## 5. Public API

```python
def validate_artifact_id(value: str, *, field: str = "artifact_id") -> str: ...

def contained_path(root: PathLike, *segments: str) -> Path: ...

def require_json_value(value: object, *, field: str) -> None: ...
```

- `validate_artifact_id` returns the unchanged identifier or raises `ValueError`.
- `contained_path` validates every dynamic segment, resolves the candidate, and returns
  it only when it remains a descendant of the resolved root.
- `require_json_value` accepts only values serializable by the standard JSON encoder
  without `default`, custom coercion, or lossy normalization.

## 6. Invariants & Guarantees

1. **AS1 Portable Identity**: Every external identifier used in a new Core-owned path MUST satisfy the Artifact Identifier grammar before any write occurs.
2. **AS2 Resolved Containment**: A Core-owned write MUST resolve under its declared root. Lexical prefixes alone are insufficient.
3. **AS3 No Silent Rewriting**: Safety helpers MUST NOT silently slugify, truncate, or replace an invalid identifier. The caller must choose a new identifier explicitly.
4. **AS4 Strict JSON Evidence**: Canonical records, Match Surfaces, manifests, certification reports, and Research Package facts MUST serialize with the standard JSON encoder and no fallback coercion.
5. **AS5 Failure Atomicity**: Validation MUST complete before creating, replacing, or partially writing an output artifact.
6. **AS6 Structural Means Non-Executable**: Structural inspection MUST NOT import package modules, load scorers, evaluate code, or execute fixtures.
7. **AS7 Python Is Trusted Code**: Importing a Game, Player, scorer, renderer, controller, or fixture from a package MUST be treated as arbitrary Python execution and requires `trusted-local` or `isolated` trust mode.
8. **AS8 No Sandbox Claim**: Core MUST NOT label in-process execution as sandboxed or safe for untrusted code. Isolation policy belongs to the caller/runtime boundary.

## 7. Data Flow & Interaction

```text
Write: external ID -> validate_artifact_id -> contained_path -> strict JSON encode -> atomic replace
Inspect: package path -> parse manifest/data -> structural report
Certify: inspected package -> explicit trust mode -> import/execute -> conformance report
```

## 8. Error Handling & Edge Cases

- Invalid type, empty IDs, separators, traversal tokens, absolute paths, drive-prefixed
  paths, control characters, and overlong IDs raise `ValueError` before I/O.
- Symlink-aware containment uses resolved paths and rejects a resolved destination that
  leaves the root.
- Unsupported JSON values identify the failing field and preserve the original encoder
  error as the cause.
- A request to execute code in `structural` mode raises a trust-mode error.

## 9. Examples

```python
validate_artifact_id("match_0123abcd")
contained_path(records_root, "match_0123abcd.json")
require_json_value({"turn": 1, "actions": ["ATTACK"]}, field="game_state")
```

```python
validate_artifact_id("../outside")  # raises ValueError
```

```python
# Reading instrument.yaml is structural. Importing package.game:MyGame is not.
report = inspect_instrument(path, trust_mode="structural")
```

## 10. Testing Strategy

- **AS1-AS3**: Table-test valid IDs and traversal, separator, control, drive, Unicode,
  empty, and overlong adversarial IDs; assert no output exists on rejection.
- **AS4-AS5**: Attempt to write sets, bytes, datetimes, callables, and custom objects;
  assert explicit failure and unchanged destination.
- **AS6-AS8**: Use a module with an import side effect; structural inspection must not
  trigger it, trusted execution must declare it, and no report may call it sandboxed.

## 11. Design Rationale

Rejecting unsafe identity is preferable to normalization because provenance must retain
the exact identifier chosen by its author. Python extension points remain valuable and
intentional; naming their trust boundary is more honest than pretending dynamic imports
are data parsing.

## 12. Open Questions / Future Work

- OS-level isolation profiles belong to `agentdeck-builder` or another execution host.
- Remote artifact fetching and archive extraction are outside this version.

## 13. References

- `SPEC-GAME.md`
- `SPEC-RECORDER.md`
- `SPEC-MATCH-SURFACE-PROJECTION.md`
- `SPEC-RESEARCH-PACKAGER.md`
- `SECURITY.md`
