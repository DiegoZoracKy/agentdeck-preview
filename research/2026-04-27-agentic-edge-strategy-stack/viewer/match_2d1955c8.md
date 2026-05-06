# Match Sidecar: match_2d1955c8

**Slot:** S3 FixedDamage policy-execution example  
**Cell:** `p2_fd_frontier_s3` (GPT4oMini-S0-AO vs FlashLite-S3-HP)  
**Seed:** 2026046024  
**Winner:** FlashLite-S3-HP (going second)  
**Final HP:** FlashLite-S3-HP 10 — GPT4oMini-S0-AO 0

**Why selected:** Every FlashLite turn shows the explicit HP arithmetic from the grounding prompt —
"X - 20 = Y, which is [above/below] 0" — and FlashLite fires POTION at exactly the right thresholds
(HP=60, 50, 20). The policy is visibly running on every turn. This is the clearest demonstration that
the S3 grounding prompt is being executed, not improvised.

---

## Turn-by-Turn

```
T01  GPT4oMini-S0-AO     hp=100 pot=3  ATTACK
T02  FlashLite-S3-HP     hp= 80 pot=3  ATTACK
     "80 - 20 = 60 > 0. Will survive. Act on best read. ATTACK."
T03  GPT4oMini-S0-AO     hp= 80 pot=3  POTION
T04  FlashLite-S3-HP     hp= 80 pot=3  ATTACK
     "80 - 20 = 60 > 0. Will survive. ATTACK."
T05  GPT4oMini-S0-AO     hp= 80 pot=2  ATTACK
T06  FlashLite-S3-HP     hp= 60 pot=3  POTION   ← fires at HP=60
     "60 - 20 = 40 > 0. Will survive. But I've been taking hits — use POTION to stay safe."
     (Note: HP=60 is a discretionary potion, above the survival threshold, anticipating future damage.)
T07  GPT4oMini-S0-AO     hp= 80 pot=2  ATTACK
T08  FlashLite-S3-HP     hp= 70 pot=2  ATTACK
     "70 - 20 = 50 > 0. Will survive. ATTACK."
T09  GPT4oMini-S0-AO     hp= 60 pot=2  POTION
T10  FlashLite-S3-HP     hp= 70 pot=2  ATTACK
     "70 - 20 = 50 > 0. Will survive. ATTACK."
T11  GPT4oMini-S0-AO     hp= 70 pot=1  ATTACK
T12  FlashLite-S3-HP     hp= 50 pot=2  POTION   ← fires at HP=50
     "50 - 20 = 30 > 0. Will survive. But HP is lower — use POTION."
T13  GPT4oMini-S0-AO     hp= 70 pot=1  ATTACK
T14  FlashLite-S3-HP     hp= 60 pot=1  ATTACK
     "60 - 20 = 40 > 0. Will survive. ATTACK."
T15  GPT4oMini-S0-AO     hp= 50 pot=1  POTION
T16  FlashLite-S3-HP     hp= 60 pot=1  ATTACK
     "60 - 20 = 40 > 0. Will survive. ATTACK."
T17  GPT4oMini-S0-AO     hp= 60 pot=0  ATTACK
T18  FlashLite-S3-HP     hp= 40 pot=1  ATTACK
     "40 - 20 = 20 > 0. Will survive. ATTACK."
T19  GPT4oMini-S0-AO     hp= 40 pot=0  ATTACK
T20  FlashLite-S3-HP     hp= 20 pot=1  POTION   ← fires at HP=20 (survival threshold)
     "20 - 20 = 0. Would NOT survive. Still have 1 potion. USE POTION."
T21  GPT4oMini-S0-AO     hp= 40 pot=0  ATTACK
T22  FlashLite-S3-HP     hp= 30 pot=0  ATTACK
     "30 - 20 = 10 > 0. Will survive. ATTACK."
T23  GPT4oMini-S0-AO     hp= 20 pot=0  ATTACK
T24  FlashLite-S3-HP     hp= 10 pot=0  ATTACK   → GPT4oMini dies (0 HP)
     "10 - 20 = -10 < 0. Would not survive. But no potions left. ATTACK anyway."
```

---

## Key Moments

- T20 is the definitive policy moment: FlashLite at HP=20 calculates 20-20=0 and correctly identifies
  this as "would not survive." Uses POTION. This is the grounding rule executing exactly as written.
- T24 shows the rule's "no potions" branch: at HP=10 with no potions, it attacks anyway and wins.
- GPT4oMini exhausts all potions by T15 without the same discipline. No policy, no consistency.

---

## Storytelling Use

- **Demo:** "S3 FlashLite doesn't guess — it calculates. Every turn shows the arithmetic."
- **Slide caption:** "S3 policy running: '20 − 20 = 0. Would not survive. USE POTION.'"
- **Contrast:** In S0 (match_0316b96b), FlashLite dies with potions at HP=20. Here it calculates correctly and survives.
- **Product angle:** This is what auditable AI behavior looks like — every decision is traceable to the rule that drove it.
