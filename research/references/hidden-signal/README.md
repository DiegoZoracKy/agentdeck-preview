# Hidden Signal acceptance reference

Hidden Signal is the second full Miningames Gate A reference. It exists to
falsify assumptions created by Last Potion:

- one Player rather than two;
- no opponent, competition, ranking, or winner;
- information acquisition rather than combat/resource recovery;
- fresh Recorder v2 Records rather than an imported historical corpus;
- a distinct Game-specific Stage over the current Match Surface protocol.

The reference closes:

```text
Game
→ Game Research Profile
→ Study / prepared Assemblies
→ 40 fresh canonical Records
→ identified RecordCorpus
→ deterministic Measure
→ Evidence
→ authored Finding
→ Record-backed Stage
```

`probe-v3.yaml` freezes the downstream composition for fresh execution of the exact Game, Study, Game
Research Profile, Measure, canonical Record, and Match Surface identities, and
names the reviewed Stage entrypoints. It is a reference-local manifest, not a
new AgentDeck authority or framework primitive. The reproducer fails before
execution if any pinned source identity has drifted.

The frozen probe's Measure and Profile hashes were prepared with Python 3.10.12.
`source-lock.json` is a derived acceptance projection of that baseline: it pins
the probe bytes, Profile sources and all Measure material except Python's version.
The reproducer checks that lock on other supported Python versions while keeping
their actual environment in every new Measure, Profile and Evidence identity
(SPEC-MEASURE ME5 and SPEC-GAME-RESEARCH-PROFILE GR8). `reference.json` records
`source_verification` with the lock hash and the current resolved identities.
Different environments can reproduce the same values without reproducing the
same Research hashes. The frozen probe and canonical artifacts are unchanged.

Revision 3 adds an explicit ABORT_MATCH policy to the single-player Game, which
changes its implementation and prepared Study identities. The revision-2
`probe.yaml` and canonical artifacts are preserved. The new probe explicitly
identifies the bundled Stage's Record as a frozen revision-2 illustration;
fresh revision-3 execution writes its own Record and Stage outside this tree.

Run it from a clean checkout:

```bash
python research/references/hidden-signal/reproduce.py \
  --output /tmp/hidden-signal-reference
```

No provider credential or network access is required. The command never writes
inside the authored Study or this reference package.

`canonical/` contains one frozen current-architecture Record and its derived
Match Surface so the Stage is immediately watchable. The end-to-end reproducer
always performs a new execution and writes a new external artifact tree.

The Stage is intentionally local to this reference. It is evidence about what
a non-combat Stage needs, not a new universal Viewer framework.
