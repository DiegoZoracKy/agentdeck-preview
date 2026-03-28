# Research Rerun Comparison

This note compares the rebuilt official experiment outputs at `HEAD` against the
pre-rerun research state at commit `6209a72`.

## Scope

- Compared rebuilt package outputs against the last pre-refresh commit.
- Covered all rebuilt experiment packages under `research/`.
- Final rebuilt set validated with:
  - `python scripts/research_index.py --research-dir research --output research/INDEX.md`
  - `python scripts/research_validate.py --research-dir research`

## Integrity Notes

- The rebuilt set now has `59` checked matrix cells with `0` missing complete
  official sessions.
- Two late export-shape issues were cleaned before final comparison:
  - `2026-03-25-variable-damage-openai-baseline-1` had duplicated pilot sessions
    accidentally aggregated.
  - `2026-03-26-variable-damage-premium-final-1` still included an old `3`-match
    partial session.
- The numbers below refer to the final cleaned rebuilt exports, not the
  intermediate duplicate-inclusive exports.

## Stable Findings

- The strongest negative OpenAI result held and strengthened:
  - `FixedDamage OpenAI Parity 1`
  - `GPT4oMini-RC` vs `GPT5Mini-AO` moved from `8-40` to `5-43`
  - Read: RC is still clearly harmful for `gpt-4o-mini` in this ladder.

- The VariableDamage top tier still compresses into near-parity rather than a
  clear premium runaway:
  - `GPT5Mini-AO` vs `Flash-AO`: `25-23` to `26-22`, still null
  - `GPT5Mini-AO` vs `Haiku-AO`: `14-10` to `12-12`
  - Read: `Flash`, `GPT5Mini`, and `Haiku` remain close enough that the right
    story is co-top baselines with different policy styles, not a single dominant
    premium winner.

- The VariableDamage risk-grounded Flash-Lite intervention remains real:
  - `FlashLite-RC-RISK` vs `Flash-AO`: `12-12` to `13-11` in the pilot package
  - `FlashLite-RC-RISK` vs `Flash-AO`: `26-22` remained `26-22` in the expansion
  - `FlashLite-RC-RISK` vs `GPT5Mini-AO`: `11-13` to `13-11`, still null
  - Read: the intervention still converts Flash-Lite from broken to competitive.

- VariableDamage Mini RC still does not justify a branch:
  - `Mini-RC` vs `Mini-AO` moved from `13-11` to `12-12`
  - Read: if anything, the rebuilt set weakens the case for Mini RC.

## Materially Changed Findings

### 1. FixedDamage Flash-Lite No Longer Has A Defensible "Decisive Win" Over Flash

The biggest narrative change is the tuned Flash-Lite ladder in `FixedDamage`.

- `Parity 3`: `FlashLite-RC-TR-HP` vs `Flash-AO`
  - old: `31-17`, `p=0.059`
  - rebuilt: `24-24`, `p=1.0`
- `Parity 4`: `FlashLite-RC-TR-HP` vs `Flash-AO`
  - old: `28-20`, `p=0.312`
  - rebuilt: `21-27`, `p=0.471`
- `Exit 1`: `FlashLite-RC-TR-HP-exit` vs `Flash-AO`
  - old: `35-13`, `p=0.0021`
  - rebuilt: `28-20`, `p=0.312`

Read:
- The tuned Flash-Lite stack is still competitive.
- The rebuilt set does **not** support the older stronger claim that the full
  FixedDamage stack clearly beat `Flash-AO`.
- The correct carry-forward language is now: competitive / near-parity, not
  decisive champion.

### 2. FixedDamage Plain Ordering Sharpened In Flash's Favor

The plain-model completion packages changed the FixedDamage ordering more than
anything else outside the Flash-Lite ladder.

- `Flash-AO` vs `Haiku-AO`
  - old: `26-22`, `p=0.665`
  - rebuilt: `33-15`, `p=0.0133`
- `Flash-AO` vs `Mini-AO`
  - old: `36-12`, `p=7.17e-04`
  - rebuilt: `32-16`, `p=0.0293`
- `Flash-AO` vs `GPT5Mini-AO`
  - old: `12-36`, `p=7.17e-04`
  - rebuilt: `15-33`, `p=0.0133`

Read:
- `GPT5Mini-AO` still sits above `Flash-AO`.
- `Flash-AO` now has cleaner support over `Haiku-AO` in FixedDamage.
- The rebuilt plain-ordering read is:
  - `GPT5Mini-AO > Flash-AO > Haiku-AO > Mini-AO > FlashLite-AO`

### 3. Some Earlier VariableDamage Package Edges Weakened

The VariableDamage arc mostly held, but a few individual package reads softened.

- `Haiku-AO` vs `Mini-AO` in `VariableDamage Baseline 3`
  - old: `31-17`, `p=0.059`
  - rebuilt: `27-21`, `p=0.471`
- `FlashLite-RC-TR` vs `Flash-AO` in `VariableDamage Reinforcement 1`
  - old: `10-14`, `p=0.541`
  - rebuilt: `13-11`, `p=0.839`

Read:
- The overall VariableDamage story remains intact.
- But the rebuilt set gives even less support to broad claims like:
  - "Haiku clearly separated from Mini"
  - "TR has a reliable standalone effect"

## What Survived The Rebuild Best

- `FlashLite` remains the model with the clearest intervention upside.
- `Mini` remains behaviorally conservative and hard to help with RC.
- `Haiku` remains much healthier in VariableDamage than in FixedDamage.
- `GPT5Mini` remains a clean premium / co-top baseline rather than a runaway
  ceiling in VariableDamage.

## Implications For Existing Summaries

The old package outputs are no longer the right source of truth for release-facing
claims. The rebuilt exports should now be treated as canonical.

The highest-priority summary refreshes should be:

- `FixedDamage Arc 1`
  - downgrade the tuned Flash-Lite claim from decisive win to competitive
  - update the plain ordering to `GPT5Mini > Flash > Haiku > Mini > FlashLite`
- `Cross-Game Comparison 1`
  - remove any reliance on `Flash ≈ Haiku` in FixedDamage
  - keep the stronger VariableDamage co-top interpretation
- `VariableDamage Arc 1`
  - mostly stable, but should absorb the cleaned `OpenAI Baseline 1` and
    `Premium Final 1` numbers

## Bottom Line

The rebuild did **not** overturn the product story. AgentDeck still shows:

- hidden behavioral failures
- intervention effects and non-effects
- transfer differences across games
- replayable, packageable experiments

But it **did** tighten the research story:

- several null-ish package edges were shown to be genuinely unstable
- the FixedDamage Flash-Lite ladder is weaker than the older storyline implied
- the FixedDamage plain baseline ordering is clearer than before
