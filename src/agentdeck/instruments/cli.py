"""Command-line interface for Instrument Package operations."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from .certify import certify_instrument
from .manifest import inspect_instrument, validate_instrument


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentdeck-instrument")
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "validate"):
        command = subparsers.add_parser(name)
        command.add_argument("package")
    certify = subparsers.add_parser("certify")
    certify.add_argument("package")
    certify.add_argument(
        "--trust-mode", required=True, choices=("structural", "trusted-local", "isolated")
    )
    certify.add_argument("--output")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "inspect":
        report = inspect_instrument(args.package)
    elif args.command == "validate":
        report = validate_instrument(args.package)
    else:
        report = certify_instrument(
            args.package,
            trust_mode=args.trust_mode,
            output_dir=args.output,
        )
    sys.stdout.write(report.canonical_json() + "\n")
    return 0 if report.valid else 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
