# Viewer Status (2026-05-08)

## Positioning
- The replay viewer is a curated replay surface for recorded AgentDeck matches.
- The core product remains the engine, record contract, and research workflow.
- The viewer consumes records; it does not define the product contract.
- The Agentic Edge public viewer is hosted as a Hugging Face Space:
  https://huggingface.co/spaces/agentdeck/agentic-edge-viewer

## Current Scope
- Works with AgentDeck match records on schema `1.3+`.
- Supports local file loading, local library playback, and URL-based loading.
- Ships with FixedDamage/VariableDamage-focused renderers plus a debug-oriented surface.
- Includes a smoke-check: `node scripts/viewer_smoke_check.js`.

## Explicit Limits
- No live/broadcast replay work yet.
- Other games require renderer registration.
- Hosted study viewers are curated bundles, not a generic hosted-record service.

## Next Work
1. Expand renderer coverage beyond FixedDamage.
2. Keep viewer docs aligned with the recorder contract as records evolve.
3. Keep the hosted Space and repo viewer bundle in sync for curated studies.
