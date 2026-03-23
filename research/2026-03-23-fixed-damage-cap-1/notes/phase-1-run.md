# Phase 1 Run Notes

- Goal: run the first mild `max_tokens` cap against the best known Flash-Lite
  stack without changing controller, cadence, or HP-grounding.
- Cell:
  - `p1_c01_flash_lite_rc_tr_hp_cap128_vs_flash_ao`
- Seed base:
  - `19242`
- Expected comparison anchor:
  - Parity 3 full stack (`FlashLite-RC-TR-HP` vs `Flash-AO`)
- Runtime note:
  - the package bumps `Flash-AO` retry/backoff above the older parity default
    because the first run attempt failed on repeated Vertex `429
    RESOURCE_EXHAUSTED` responses before any match completed
- Final execution note:
  - the canonical run completed only after switching Vertex to the `global`
    endpoint
  - `max_tokens=128` reduced Flash-Lite cost enough to make it cheaper than
    plain Flash, but it also regressed the low-HP policy enough to flip the
    cell to a significant `16-32` loss
