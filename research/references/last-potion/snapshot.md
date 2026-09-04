# Last Potion

A small combat world for observing when an AI spends a scarce recovery resource under deterministic and stochastic damage.

## Moment

**ONE RUN · N=1**

FlashLite-S3-HP used its final POTION at 20 HP in this Run.

Turn 20: `FlashLite-S3-HP` chose `POTION` at 20 HP with 1 potion remaining.

Record: `sha256:2241e6b034a561fa3b22ddf65f8f273d81c8a636bab290af366fcec326ae68c6` · Match: `match_2d1955c8`

## Pattern

**48 RUNS · 189 CRITICAL-STATE TURNS · DERIVED PATTERN**

Across the identified p2-fd-frontier-s3 corpus, FlashLite-S3-HP chose POTION in 56.1% of 189 critical-state decision turns.

Evidence: `sha256:c1f3da2cea202d56337faaca1bf3d0877e2b08a66f99dd53a4cfd73ef9628720` · Result: `sha256:139c11c7474982cc675b76212238c04f05582b5b770ff8786797d10121a6f17e`

# Finding: fixed-damage-critical-recovery

In the declared FixedDamage Cell, the HP-grounded FlashLite Player used recovery frequently when acting at critical health.

Author: AgentDeck acceptance authors (human)
Finding: `sha256:4d04e3a89f5ed6e1108bf84d786d24c0c9b444940fb2f1be0ce6b8b0537b0bc3`

## Evidence citations

- **supports** `critical-potion-response-rate` = `0.5608465608465608` (Evidence `sha256:c1f3da2cea202d56337faaca1bf3d0877e2b08a66f99dd53a4cfd73ef9628720`, result `sha256:139c11c7474982cc675b76212238c04f05582b5b770ff8786797d10121a6f17e`, dimensions `{"cell":"p2-fd-frontier-s3","player":"FlashLite-S3-HP"}`, origin `imported`, phase `study, supplemental`)

## Limitations

- Critical health is a Game-local threshold declared by the Measure.
- The result applies to the identified Cell, Players, prompts, provider snapshots, and schedule.
- This does not establish general risk preference or privileged access to hidden reasoning.

## Assurance boundary

AgentDeck validated artifact identities and citation resolution. This Finding remains authored interpretation, not mechanically certified truth.

## Reference boundary

The Moment is one exact recorded occurrence. The Pattern is a deterministic projection of one EvidenceResult over an identified corpus. The Finding remains authored interpretation. The frozen Hugging Face source was read without mutation.
