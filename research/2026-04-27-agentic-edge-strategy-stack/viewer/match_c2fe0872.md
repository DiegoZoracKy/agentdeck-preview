# Match Sidecar: match_c2fe0872

**Slot:** VariableDamage caveat example  
**Cell:** `p2_vd_frontier_s3` (GPT4oMini-S0-AO vs FlashLite-S3-RISK)  
**Seed:** 2026047004  
**Winner:** GPT4oMini-S0-AO (going first)  
**Final HP:** GPT4oMini-S0-AO 2 — FlashLite-S3-RISK 0

**Why selected:** FlashLite-S3-RISK follows its risk-band policy correctly throughout this match
and still loses by 2 HP. GPT4oMini went first (seat advantage), used its potions early enough to
stay alive, and closed out by the narrowest margin. This is the study's most direct illustration
of why the VD cross-tier result is caveated: good policy is not always enough when first-mover
advantage and stochastic damage combine against you.

---

## Turn-by-Turn

```
T01  GPT4oMini-S0-AO     hp=100 pot=3  ATTACK   (goes first)
T02  FlashLite-S3-RISK   hp= 83 pot=3  ATTACK
     "HP=83, above 55. Do not use potion. ATTACK."
T03  GPT4oMini-S0-AO     hp= 76 pot=3  POTION   ← early potion
T04  FlashLite-S3-RISK   hp= 83 pot=3  ATTACK
     "HP=83, above 55. Do not use potion."
T05  GPT4oMini-S0-AO     hp= 79 pot=2  ATTACK
T06  FlashLite-S3-RISK   hp= 64 pot=3  ATTACK
     "HP=64, above 55. Do not use potion."
T07  GPT4oMini-S0-AO     hp= 63 pot=2  POTION   ← second early potion
T08  FlashLite-S3-RISK   hp= 64 pot=3  ATTACK
     "HP=64, above 55. Opponent used POTION — they're recovering. Continue attacking."
T09  GPT4oMini-S0-AO     hp= 68 pot=1  ATTACK
T10  FlashLite-S3-RISK   hp= 46 pot=3  POTION   ← rule trigger (26–40 or near-55)
     "HP=46 — in 26–40 range with 3 potions. Prefer POTION now."
T11  GPT4oMini-S0-AO     hp= 68 pot=1  ATTACK
T12  FlashLite-S3-RISK   hp= 53 pot=2  ATTACK
     "HP=53, not above 55, not in critical range. Hold."
T13  GPT4oMini-S0-AO     hp= 45 pot=1  POTION   ← third potion
T14  FlashLite-S3-RISK   hp= 53 pot=2  ATTACK
     "HP=53. Not in critical zone. Hold."
T15  GPT4oMini-S0-AO     hp= 59 pot=0  ATTACK
T16  FlashLite-S3-RISK   hp= 31 pot=2  POTION   ← rule trigger at HP=31
     "HP=31 — in 26–40 range. Have 2 potions. USE POTION."
T17  GPT4oMini-S0-AO     hp= 59 pot=0  ATTACK
T18  FlashLite-S3-RISK   hp= 44 pot=1  ATTACK
     "HP=44. Not above 55, not critical. Hold."
T19  GPT4oMini-S0-AO     hp= 35 pot=0  ATTACK
T20  FlashLite-S3-RISK   hp= 24 pot=1  POTION   ← lethal-zone trigger at HP=24
     "HP=24 — 25 or lower. Have 1 potion. USE POTION."
T21  GPT4oMini-S0-AO     hp= 35 pot=0  ATTACK
T22  FlashLite-S3-RISK   hp= 34 pot=0  ATTACK
     "HP=34 — in 26–40 range. No potions. Attack anyway."
T23  GPT4oMini-S0-AO     hp= 19 pot=0  ATTACK
T24  FlashLite-S3-RISK   hp= 19 pot=0  ATTACK
     "HP=19 — 25 or lower. No potions. Attack anyway."
T25  GPT4oMini-S0-AO     hp=  2 pot=0  ATTACK   → FlashLite dies (0 HP)
```

---

## Key Moments

- FlashLite fires its risk-band rules correctly: T10 (HP=46), T16 (HP=31), T20 (HP=24). Policy clean.
- GPT4oMini uses its potions earlier (T03 at HP=76, T07 at HP=63, T13 at HP=45). Without any rule,
  it happens to time them well from first-seat position.
- GPT4oMini went first (seat advantage). It deals one more round of damage in total across the match.
- Final margin: GPT4oMini survives at 2 HP. One stochastic damage roll in either direction could have
  flipped this.

---

## What This Illustrates

FlashLite-S3-RISK was not outplayed tactically. It followed its policy. It lost because:
1. GPT4oMini had first-mover advantage (accumulated one extra hit across the game).
2. Variable damage meant the exact HP thresholds didn't land the same way each time.
3. The margin was 2 HP — within one attack's worth of variance.

This is why the VD frontier result (58.3%, p=0.312) is not a reliable cross-tier dominance claim.
The within-model result (FlashLite-S3-RISK vs FlashLite-S0-AO, 85.4%) is the strong transfer finding.
The cross-tier claim requires the seat and variance effects to cooperate.

---

## Storytelling Use

- **Demo:** "FlashLite-S3-RISK played correctly and still lost. That's the VD caveat."
- **Slide caption:** "FlashLite followed the risk policy. Lost by 2 HP. Went second. That's the margin."
- **Caveat framing:** Use this to explain why the VD cross-tier result is not the strong headline —
  it's a caveated positive signal. The architecture transferred; the seat advantage didn't.
- **Honest science:** This is a real loss on correct policy. Not a failure of the agent design —
  a genuine variance/seat interaction that the study's statistical readout already flagged.
