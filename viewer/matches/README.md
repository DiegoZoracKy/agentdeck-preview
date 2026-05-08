# Local Matches

This directory carries the curated research showcase set used by the replay
viewer across bundled combat games.

The bundled `*.meta.json` files were manually curated from the replay data for
the release viewer. `MatchCurator` can generate valid sidecars automatically,
but its default deterministic generator is intentionally factual and flat: a
useful starting point, not the final editorial voice used in the bundled
showcase set.

Bundled matches:

- `fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json`
- `fixed-damage-02-flashlite-rc-repair-vs-flash-ao.json`
- `fixed-damage-03-flashlite-final-stack-vs-flash-ao.json`
- `fixed-damage-04-gpt4omini-rc-backfires-vs-gpt5mini.json`
- `fixed-damage-05-haiku-seat-pathology-vs-flash.json`
- `fixed-damage-06-flash-vs-gpt5mini-premium-baseline.json`
- `variable-damage-01-flashlite-rc-risk-vs-gpt5mini.json`
- `variable-damage-02-gpt5mini-vs-flash.json`

To replace or extend the local library, drop replay files (`*.json`) here and
optional metadata sidecars (`*.meta.json`) here and refresh `manifest.json`.

You can generate the manifest automatically with:

```bash
node scripts/update_match_manifest.js
```

Sidecars are portable replay companions. They may contain:

- `subtitle`
- `synopsis`
- `highlights`
- optional `transcript`

Each highlight may also include an optional `kind`:

- `mistake`
- `smart_move`
- `surprise`
- `turning_point`

Only `subtitle`, `synopsis`, and `highlights` are promoted into
`manifest.json` for runtime viewer use.
