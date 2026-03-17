# Viewer Status (2026-03-17)

## Positioning
- The replay viewer is now treated as a **beta offline surface**.
- The core product remains the engine, record contract, and research workflow.
- The viewer consumes records; it does not define the product contract.

## Current Scope
- Works with AgentDeck match records on schema `1.3+`.
- Supports local file loading, local library playback, and URL-based loading.
- Ships with FixedDamage-focused renderers plus a debug-oriented surface.
- Includes a smoke-check: `node scripts/viewer_smoke_check.js`.

## Explicit Limits
- Offline playback only.
- No live/broadcast replay work yet.
- Other games require renderer registration; FixedDamage is the default supported path.

## Next Work
1. Expand renderer coverage beyond FixedDamage.
2. Keep viewer docs aligned with the recorder contract as records evolve.
3. Decide whether hosted/public replay distribution belongs in-core or outside the repo.
