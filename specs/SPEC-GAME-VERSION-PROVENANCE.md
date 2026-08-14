# SPEC-GAME-VERSION-PROVENANCE: Game Implementation Identity

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-14
> Implementation: Complete
> Review State: Consensus-approved
> Audience: Game authors, execution operators, Record consumers

## 1. Purpose

Identify the Game implementation that produced a match Record without confusing
implementation identity with effective configuration or research meaning.

## 2. Scope

- Recorder persists implementation provenance; it does not decide whether Records are comparable.
- Missing source closure is reported honestly and does not block an otherwise valid Game.
- Historical Records remain immutable.
- Research questions, pooling, metrics, findings, and claims are outside this contract.

## 3. Contract

Every new match Record includes `metadata.game_version`:

```json
{
  "family_id": "example.number-duel",
  "declared_version": "1.0.0",
  "implementation_sha256": "<64 lowercase hex characters or null>",
  "fingerprint_scope": "declared_closure",
  "sources": [
    {"name": "module:number_duel.game", "sha256": "<64 lowercase hex characters>"}
  ],
  "assurance": "content_addressed"
}
```

- `family_id`: author-declared identity, or deterministic class identity as fallback.
- `declared_version`: optional author-declared version; never a content fingerprint.
- `implementation_sha256`: digest of the named source scope, or `null` when unresolved.
- `fingerprint_scope`: `declared_closure`, `class_source`, or `unresolved`.
- `sources`: portable source names and per-source hashes; never absolute paths.
- `assurance`: `content_addressed`, `class_source_only`, or `unresolved`.

The Game may declare `GAME_FAMILY_ID`, `GAME_VERSION`, and
`GAME_IMPLEMENTATION_MODULES`. Without a declared closure, Core fingerprints the
Game class source and labels the narrower assurance explicitly.

## 4. Invariants

1. **GVP1 Recorded Identity**: Every new match contains `metadata.game_version`.
2. **GVP2 Identity Separation**: Implementation identity and effective Game configuration remain distinct facts.
3. **GVP3 Deterministic Fingerprint**: Equal portable names and bytes produce the same digest regardless of path, input order, or time.
4. **GVP4 Honest Scope**: The descriptor states whether it covers a declared closure, class source only, or unresolved source.
5. **GVP5 No False Precision**: Core never emits a digest for source bytes it could not read.
6. **GVP6 Non-Blocking Provenance**: Unresolved source remains visible but does not prevent execution.
7. **GVP7 Portable Sources**: Persisted source identities contain no machine-specific paths.
8. **GVP8 Historical Immutability**: Existing Records are never rewritten to backfill provenance.

## 5. Errors

- Invalid explicit declarations fail with the offending field named.
- Missing declared modules produce an unresolved descriptor, not a fabricated digest.
- Duplicate or non-qualified module names are rejected.

## 6. Testing

- Deterministic hashing across reordered declared modules.
- Declared closure, class-source fallback, and unresolved fallback.
- Recorder persistence separated from effective Game configuration.

## 7. References

- [SPEC-GAME](SPEC-GAME.md)
- [SPEC-RECORDER](SPEC-RECORDER.md)
- [Specification Authoring Guidelines](GUIDELINES.md)
