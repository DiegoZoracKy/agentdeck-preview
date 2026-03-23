# Phase 1 Run Notes

- Goal: run the final FixedDamage prompt repair against the best known
  Flash-Lite stack without changing the engine, controller, or model.
- Cell:
  - `p1_c01_flash_lite_rc_tr_hp_exit_vs_flash_ao`
- Seed base:
  - `20242`
- Expected comparison anchor:
  - Parity 3 full stack (`FlashLite-RC-TR-HP` vs `Flash-AO`)
- Runtime note:
  - the package keeps the stronger Flash retry/backoff profile used in the
    recent Gemini packages because earlier regional runs hit repeated Vertex
    `429 RESOURCE_EXHAUSTED` responses
  - canonical execution should use `VERTEX_LOCATION=global` from the start
  - the only gameplay change is the new no-potion escape clause in the HP
    instruction
- Final result:
  - `FlashLite-RC-TR-HP-exit` beat `Flash-AO` `35-13` at `N=48`
  - exact binomial `p=0.0021`
  - first player won `37/48`
  - `FlashLite-RC-TR-HP-exit` won `11/24` as second player vs `Flash-AO` `0/24`
- Tail note:
  - the earlier `10 HP / 0 potions` deadlock no longer produced runaway turns
  - Flash-Lite's worst raw response in this package was `848` chars, far below
    Parity 3's `13,126`-char outlier
