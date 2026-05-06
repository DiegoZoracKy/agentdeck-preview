# Match Sidecar: match_0430d46c

**Slot:** S1 pivot example  
**Cell:** `p3_fd_frontier_s1` (FlashLite-S1-RC vs GPT4oMini-S0-AO)  
**Seed:** 2026047710  
**Winner:** FlashLite-S1-RC  
**Final HP:** FlashLite-S1-RC 30 — GPT4oMini-S0-AO 0

**Why selected:** FlashLite-S1-RC uses all 3 potions at exactly the right moments (HP=20, 10, 20),
survives three lethal thresholds, and wins. The reasoning trace shows the model recognizing the danger
at each point — not because it was told the exact rule, but because structured reasoning made it visible.
This is the direct S1 contrast to match_0316b96b.

---

## Turn-by-Turn

```
T01  FlashLite-S1-RC    hp=100 pot=3  ATTACK
     "First turn. Both full health. Best to attack."
T02  GPT4oMini-S0-AO    hp= 80 pot=3  POTION
T03  FlashLite-S1-RC    hp=100 pot=3  ATTACK
     "Opponent used potion — they healed. I attacked. Keep attacking."
T04  GPT4oMini-S0-AO    hp= 80 pot=2  POTION
T05  FlashLite-S1-RC    hp=100 pot=3  ATTACK
     "Opponent using potions to outlast me. Keep attacking."
T06  GPT4oMini-S0-AO    hp= 80 pot=1  ATTACK
T07  FlashLite-S1-RC    hp= 80 pot=3  ATTACK
     "Took 20 damage. Opponent is attacking now. I'll attack."
T08  GPT4oMini-S0-AO    hp= 60 pot=1  POTION
T09  FlashLite-S1-RC    hp= 80 pot=3  ATTACK
     "Opponent used last potion — they're out after this."
T10  GPT4oMini-S0-AO    hp= 70 pot=0  ATTACK
T11  FlashLite-S1-RC    hp= 60 pot=3  ATTACK
     "Down to 60. Opponent has no potions. Staying aggressive."
T12  GPT4oMini-S0-AO    hp= 50 pot=0  ATTACK
T13  FlashLite-S1-RC    hp= 40 pot=3  ATTACK
     "40 HP. Opponent has no potions. Keep attacking."
T14  GPT4oMini-S0-AO    hp= 30 pot=0  ATTACK
T15  FlashLite-S1-RC    hp= 20 pot=3  POTION   ← uses potion at HP=20
     "Health now 20 HP. Opponent attacked last turn. I've taken significant damage.
      It's essential to use my last potion to survive."
T16  GPT4oMini-S0-AO    hp= 30 pot=0  ATTACK
T17  FlashLite-S1-RC    hp= 30 pot=2  ATTACK
     "Used potion, now at 30. Opponent still has 30. Attacking."
T18  GPT4oMini-S0-AO    hp= 10 pot=0  ATTACK
T19  FlashLite-S1-RC    hp= 10 pot=2  POTION   ← uses potion at HP=10
     "Health critically low at 10 HP. Must use potion to survive."
T20  GPT4oMini-S0-AO    hp= 10 pot=0  ATTACK
T21  FlashLite-S1-RC    hp= 20 pot=1  POTION   ← uses potion at HP=20 again
     "Opponent attacked, down to 20. Used potion to stay alive."
T22  GPT4oMini-S0-AO    hp= 10 pot=0  ATTACK
T23  FlashLite-S1-RC    hp= 30 pot=0  ATTACK   → GPT4oMini dies (0 HP)
     "Opponent has 10 HP. Attack to finish."
```

---

## Key Moments

- T15: At HP=20 with 3 potions, FlashLite uses POTION. Compare to T15 of match_0316b96b where S0
  FlashLite attacks and dies. Same HP, same potions, opposite decision.
- T19: Drops to 10, uses potion again. S0 would have died here.
- T21: Uses third potion to extend survival into the finish.
- Opponent exhausts all potions by T08 and has no response to FlashLite's late-game healing.

---

## Storytelling Use

- **Demo:** "With structured reasoning only — no explicit rule — FlashLite now recognizes 'I'm about to die' and acts on it."
- **Slide caption:** "S1 FlashLite: 3 potions used at HP=20, 10, 20. Won. Cost: reasoning format only."
- **Contrast pair:** Direct mirror of match_0316b96b. Same seed family, same threshold moment, opposite outcome.
- **Ladder anchor:** This is the T15 pivot that explains why S0=0% and S1=70.8%. The model didn't need the grounding rule. It needed a reasoning field.
