# SPEC-GAME-VERSION-PROVENANCE: Game Implementation Identity

> Status: Final
> Version: 0.1.0
> Last Updated: 2026-08-10
> Implementation: Complete
> Review State: Consensus-approved
> Audience: Game authors, research operators, artifact consumers

## 1. Purpose

Identify the exact Game implementation that produced a new match record without
confusing Game identity with effective configuration or the surrounding Instrument.
Researchers need to distinguish "which world ran?" from "which settings and apparatus
were used?" before they can reason about comparability or transfer.

## 2. Scope & Philosophy Alignment

- Recorder persists provenance; it does not decide whether two Games are comparable.
- Game authors retain full freedom over mechanics, research purpose, and technology.
- Missing source closure is reported honestly and MUST NOT make an otherwise valid Game
  unexecutable. A capability tier may still require stronger provenance for the claim it
  awards without invalidating the Game or its runnable capability.
- Historical records remain immutable. No published artifact is rewritten to backfill
  provenance that was not captured at execution time.

Non-goals: semantic Game-family governance, comparability, evidence pooling,
Instrument identity, statistical validity, or a Game registry.

## 3. Contract

Every new match record includes `metadata.game_version`:

```json
{
  "family_id": "example.number-duel",
  "declared_version": "1.0.0",
  "implementation_sha256": "<64 lowercase hex characters or null>",
  "fingerprint_scope": "declared_closure",
  "sources": [
    {"name": "number_duel/game.py", "sha256": "<64 lowercase hex characters>"}
  ],
  "assurance": "content_addressed"
}
```

Required fields:

- `family_id`: non-empty portable identity. A deterministic class identity is the
  fallback when the author declares none.
- `declared_version`: author-declared version or `null`; it is never treated as a
  content fingerprint.
- `implementation_sha256`: deterministic digest of the named implementation closure,
  or `null` when the runtime cannot resolve source bytes.
- `fingerprint_scope`: `declared_closure`, `class_source`, or `unresolved`.
- `sources`: ordered portable names and per-source hashes; never absolute paths.
- `assurance`: `content_addressed`, `class_source_only`, or `unresolved`.

The exact runtime configuration remains in `metadata.game_config`. The exact certified
apparatus remains identified by the Instrument Package hash. These identities MUST NOT
be substituted for one another.

## 4. Behavior

- A Game MAY declare a family ID, human version, and source closure.
- Core derives hashes from source bytes; an author-supplied digest alone is not
  content-addressed assurance.
- When no closure is declared, Core SHOULD fingerprint the Game class source and label
  the narrower scope explicitly.
- When source bytes cannot be resolved, Core records an unresolved descriptor and
  continues execution.
- `evidence_ready` requires a complete content-addressed declared closure, while
  `runnable` retains the partial and unresolved fallbacks above.
- Equal portable source names and bytes MUST produce the same implementation digest,
  independent of checkout path, file metadata, ordering supplied by the caller, or
  wall-clock time.

## 5. Invariants

1. **GVP1 Recorded Identity**: Every newly recorded match contains a structured `metadata.game_version` descriptor.
2. **GVP2 Identity Separation**: Game implementation identity, effective Game configuration, and Instrument Package identity remain distinct provenance facts.
3. **GVP3 Deterministic Fingerprint**: Equal portable source names and bytes produce the same implementation digest regardless of host path, input ordering, or wall-clock time.
4. **GVP4 Honest Scope**: The descriptor states whether its fingerprint covers a declared closure, only the Game class source, or unresolved source.
5. **GVP5 No False Precision**: Core MUST NOT emit a non-null implementation digest when it cannot read the bytes claimed by the fingerprint scope.
6. **GVP6 Non-Blocking Provenance**: Unresolved implementation source MUST remain visible but MUST NOT invalidate or prevent execution of an otherwise valid Game.
7. **GVP7 Portable Sources**: Persisted source identities contain no absolute filesystem path or machine-specific checkout location.
8. **GVP8 Historical Immutability**: Adoption of this contract MUST NOT rewrite historical records; unknown legacy provenance is represented only by additive indexes or projections.

## 6. Errors

- Invalid explicit descriptors fail before recording with the offending field named.
- Missing or unreadable declared closure files produce an unresolved descriptor rather
  than a fabricated digest.
- Source names that are absolute, escape a declared root, or collide after
  normalization are rejected.

## 7. Testing Strategy

- Verify deterministic hashing across reordered inputs and different roots.
- Verify explicit closure, class-source fallback, and unresolved fallback.
- Verify Recorder persistence and separation from `game_config`.
- Verify an unresolved dynamic Game still executes and records honestly.

## 8. References

- [SPEC-GAME](SPEC-GAME.md)
- [SPEC-RECORDER](SPEC-RECORDER.md)
- [SPEC-INSTRUMENT-PACKAGE](SPEC-INSTRUMENT-PACKAGE.md)
- [Specification Authoring Guidelines](GUIDELINES.md)
