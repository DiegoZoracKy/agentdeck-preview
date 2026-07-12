# SPEC-RESEARCH-PACKAGER-CONTEXT v0.1.0

> Status: Final
> Audience: Research engineers and external execution integrators

## 1. Purpose

Allow a caller with a confirmed world configuration to preserve that configuration
when promoting a completed session into a Core Research Package.

## 2. Contract

`agentdeck.research.package_session` MUST accept an optional `game_config`
mapping. When provided, the packager MUST:

1. Copy it into `manifest.game.config` without mutating caller data.
2. Pass the same copied configuration to Core result export and behavioral
   scoring.
3. Keep session recordings, inferred game name, players, and match counts as
   the authoritative execution evidence.

The top-level `agentdeck.research.package_session` export is a supported
packaging entry point for external orchestrators.

## 3. Invariants

1. **RPC1 Optional context:** Omitting `game_config` preserves existing inferred
   package behavior.
2. **RPC2 No invented context:** A caller-provided configuration augments only
   `manifest.game.config`; it MUST NOT rewrite the inferred game identity,
   player identity, sessions, or recorded outcomes.
3. **RPC3 Behavioral parity:** Exported behavioral profiles MUST receive the
   package manifest's effective game configuration.
4. **RPC4 Copy isolation:** Later caller mutation MUST NOT change the package
   manifest or results.

## 4. Error Handling

- A non-mapping `game_config` MUST fail before package output is created.
- Existing package destinations continue to fail rather than being overwritten.
- Missing or incompatible recordings continue to fail under
  `SPEC-RESEARCH-PACKAGER`.

## 5. Testing Strategy

- Package a FixedDamage session with `game_config` and verify the manifest and
  behavioral profile both receive the configuration.
- Verify omission preserves existing output behavior.
- Verify a supplied mapping remains unmodified after packaging.

## 6. Non-Goals

- Reconfiguring a completed game session.
- Allowing package context to replace recorder provenance.
- Adding product-specific fields or UI behavior to Core packages.

## 7. Design Rationale

Recordings tell Core what happened. A confirmed Test Plan can additionally
carry the declared world parameters needed to interpret those recordings. The
packager preserves that context as data, while Core remains the sole owner of
export and behavioral semantics.
