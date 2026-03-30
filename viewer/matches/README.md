# Local Matches

This directory now carries the curated `FixedDamage` research showcase set used
by the beta viewer.

Bundled matches:

- `fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json`
- `fixed-damage-02-flashlite-rc-repair-vs-flash-ao.json`
- `fixed-damage-03-flashlite-final-stack-vs-flash-ao.json`
- `fixed-damage-04-gpt4omini-rc-backfires-vs-gpt5mini.json`
- `fixed-damage-05-haiku-seat-pathology-vs-flash.json`
- `fixed-damage-06-flash-vs-gpt5mini-premium-baseline.json`

To replace or extend the local library, drop replay files (`*.json`) here and
refresh `manifest.json`.

You can generate the manifest automatically with:

```bash
node scripts/update_match_manifest.js
```
