# Last Potion — AgentDeck Acceptance Reference

Last Potion composes the existing FixedDamage and VariableDamage assets into a
single downstream behavioral-world reference. It does not add a Miningame type
or runtime to AgentDeck.

The world asks a small, legible question:

> When will an AI spend its scarce recovery resource?

`FixedDamageGame` is the canonical deterministic probe.
`VariableDamageGame` is a related stochastic probe that tests whether the same
behavioral language transfers when the next damage amount becomes uncertain.
They remain distinct executable Games and distinct Research Profiles.

## What is reused

- Game implementations and specs under `src/agentdeck/games/examples/`;
- the retro and debug replay Stages under `viewer/`;
- the canonical curated Record
  `viewer/matches/study-fd-03-s3-policy-flashlite-hp-vs-gpt4omini.json`;
- both Game Research Profiles, the Study, Measures, Evidence, and Findings from
  `research/2026-04-27-agentic-edge-strategy-stack/`;
- the checksum-verified, read-only frozen Hugging Face source.

`probe.yaml` freezes the downstream composition of exact Game implementation,
GRP, Study, Measure, and canonical Record identities, and names the reviewed
Stage entrypoints. It does not create a new AgentDeck authority layer or claim
that the complete Viewer dependency graph is content-addressed.

## Human journey

The generated `reference.md` presents three deliberately different units:

1. **Moment — ONE RUN · N=1**: one exact POTION decision at 20 HP, with a
   pointer into the canonical Record.
2. **Pattern — 48 RUNS / 189 CRITICAL-STATE TURNS**: one deterministic
   `critical-potion-response-rate` result with Evidence and corpus identity.
3. **Finding — authored interpretation**: a claim with a granular citation and
   explicit limitations.

The Moment is not Evidence. The Pattern is not a new Research primitive; it is
a human projection of one `EvidenceResult`. The Finding remains authored.

[`snapshot.md`](snapshot.md) is the reviewed human projection produced from the
frozen 432-Record reproduction used to close this checkpoint.

## Reproduce

First reproduce The Agentic Edge into external directories:

```bash
python3 research/2026-04-27-agentic-edge-strategy-stack/scripts/reproduce_current.py \
  --cache-dir /tmp/agentdeck-agentic-edge-cache \
  --output-root /tmp/agentdeck-agentic-edge-reproduction
```

Use the printed `analysis_*` directory to build the reference:

```bash
python3 research/references/last-potion/scripts/build_reference.py \
  --analysis-root /tmp/agentdeck-agentic-edge-reproduction/\
2026-04-27-agentic-edge-strategy-stack/analysis_<identity> \
  --output /tmp/agentdeck-last-potion-reference
```

The builder fails if any pinned Game, Profile, Study, Measure, Stage, Record,
Moment, or expected Pattern value has changed. It writes a deterministic JSON
projection and a human-readable Markdown projection into a new directory.

The frozen probe's Measure and Profile hashes belong to Python 3.10.12.
`source-lock.json` is a derived acceptance projection that pins the probe bytes,
Profile sources and all Measure material except Python's version. Other supported
Python versions retain their own full Research identities while verifying those
same sources, as SPEC-MEASURE ME5 and SPEC-GAME-RESEARCH-PROFILE GR8 require.
`reference.json` keeps the frozen `probe_revision` and records the current
identities and environment separately under `source_verification`.
Run reproduction and the builder in the same environment: Evidence must match
the current Measure and material environment, not merely the expected value.
Historical probes, snapshots and Records are not rewritten.

The Hugging Face dataset and Space remain frozen and read-only throughout.

## Stage

Open `viewer/index.html` and choose:

> Study 3 — S3 grounded policy: HP grounding makes the critical heal explicit

The retro Stage makes the trajectory watchable. The debug Stage exposes exact
state, prompt/response, action, and provenance. Both read the same canonical
Record; neither owns a second factual representation.

## What proved Game-specific

- HP, POTION, lethal thresholds, risk bands, opponent, and seat effects belong
  to the Games, GRPs, Measures, or authored Findings.
- The FixedDamage renderer can be reused by VariableDamage only because the two
  Games intentionally share state and action shape. That is family reuse, not a
  universal Stage contract.
- Competitive win rate is useful context here but is not required by AgentDeck
  Research. The second Gate A reference must close the same arc without a
  winner.
