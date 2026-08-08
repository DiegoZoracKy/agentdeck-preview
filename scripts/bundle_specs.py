#!/usr/bin/env python3
"""Compatibility wrapper for the deterministic instrument-builder bundle."""

from __future__ import annotations

import argparse
from pathlib import Path

from spec_registry import ROOT, render_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=ROOT / "specs" / "SPECS_BUNDLE.md",
    )
    parser.add_argument("--profile", default="instrument-builder")
    args = parser.parse_args()
    args.output.write_bytes(render_bundle(args.profile))
    print(f"Bundled profile {args.profile} into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
