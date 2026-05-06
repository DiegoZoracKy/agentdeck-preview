# Match Sidecar: match_0316b96b

**Slot:** S0 failure example  
**Cell:** `p2_fd_tier_gap_s0` (FlashLite-S0-AO vs GPT4oMini-S0-AO)  
**Seed:** 2026045723  
**Winner:** GPT4oMini-S0-AO  
**Final HP:** FlashLite-S0-AO 0 — GPT4oMini-S0-AO 10

**Why selected:** FlashLite attacks every single turn, ignores 3 potions, and dies at HP=20 with full potion
inventory. GPT4oMini uses all 3 potions intelligently. The contrast is immediate and legible: same game,
same rules, one player has a survival policy and one does not.

---

## Turn-by-Turn

```
T01  FlashLite-S0-AO    hp=100 pot=3  ATTACK
T02  GPT4oMini-S0-AO    hp= 80 pot=3  POTION   ← GPT4oMini heals at 80
T03  FlashLite-S0-AO    hp=100 pot=3  ATTACK
T04  GPT4oMini-S0-AO    hp= 80 pot=2  POTION   ← again at 80
T05  FlashLite-S0-AO    hp=100 pot=3  ATTACK
T06  GPT4oMini-S0-AO    hp= 80 pot=1  ATTACK
T07  FlashLite-S0-AO    hp= 80 pot=3  ATTACK
T08  GPT4oMini-S0-AO    hp= 60 pot=1  POTION   ← heals at 60
T09  FlashLite-S0-AO    hp= 80 pot=3  ATTACK
T10  GPT4oMini-S0-AO    hp= 70 pot=0  ATTACK
T11  FlashLite-S0-AO    hp= 60 pot=3  ATTACK
T12  GPT4oMini-S0-AO    hp= 50 pot=0  ATTACK
T13  FlashLite-S0-AO    hp= 40 pot=3  ATTACK
T14  GPT4oMini-S0-AO    hp= 30 pot=0  ATTACK
T15  FlashLite-S0-AO    hp= 20 pot=3  ATTACK   ← 20 HP, 3 potions unused, attacks anyway
T16  GPT4oMini-S0-AO    hp= 10 pot=0  ATTACK   → FlashLite dies (0 HP)
```

---

## Key Moments

- T15 is the pivot: FlashLite is at 20 HP with 3 potions. One more attack will kill it. No reasoning
  means no awareness of the threshold. It attacks. It dies.
- GPT4oMini's three potions are well-timed (T02, T04, T08) and keep it alive long enough to finish.
- FlashLite's potions were never touched. All 3 wasted.

---

## Storytelling Use

- **Demo:** "Without any scaffolding, FlashLite doesn't know it's about to die."
- **Slide caption:** "S0 FlashLite: 0 potions used. Died at HP=20 with 3 potions in inventory."
- **Contrast setup:** Pair with match_0430d46c (S1) where FlashLite uses the potion at HP=20.
