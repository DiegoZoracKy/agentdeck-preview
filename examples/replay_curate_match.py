"""Generate viewer metadata sidecars from a recorded match."""

from __future__ import annotations

import sys
from pathlib import Path

from agentdeck.spectators import MatchCurator, curate_match_file

DEFAULT_MATCH = Path("viewer/matches/fixed-damage-01-flashlite-ao-collapse-vs-flash-ao.json")


def main() -> int:
    # This example intentionally uses MatchCurator's built-in deterministic
    # generator as a structural baseline. It produces factual metadata from the
    # replay, but it is not meant to match the editorial quality of the bundled
    # viewer sidecars under viewer/matches/*.meta.json, which were hand-curated
    # from the same replay data for the release surface.
    match_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_MATCH
    if not match_path.exists():
        raise SystemExit(f"Match file not found: {match_path}")

    canonical_sidecar = match_path.with_suffix(".meta.json")
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
    elif canonical_sidecar.exists():
        output_path = match_path.with_name(f"{match_path.stem}.generated.meta.json")
    else:
        output_path = canonical_sidecar

    curator = curate_match_file(
        match_path,
        curator=MatchCurator(source_path=match_path, output_path=output_path),
    )
    payload = curator.last_metadata
    output_path = curator.last_output_path

    if payload is None or output_path is None:
        raise SystemExit("Curator did not produce sidecar metadata.")

    print(f"Curated: {match_path}")
    print(f"Wrote:   {output_path}")
    if output_path != canonical_sidecar:
        print(f"Note:    canonical sidecar already exists at {canonical_sidecar}")
    print(f"Subtitle: {payload.subtitle}")
    print(f"Synopsis: {payload.synopsis}")
    print("Highlights:")
    for item in payload.highlights:
        print(f"  - turn {item.turn}: {item.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
