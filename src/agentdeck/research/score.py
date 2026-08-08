"""Standalone behavioral rescore CLI for packaged experiments."""

from __future__ import annotations

import argparse
import importlib.util
import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import yaml

from .behavioral import BehavioralScorer, get_behavioral_scorer
from .export import (
    behavioral_config_from_manifest,
    collect_players,
    load_match,
    recordings_dirs_for_cell,
)

EXECUTABLE_TRUST_MODES = {"trusted-local", "isolated"}
TRUST_MODES = {"structural", *EXECUTABLE_TRUST_MODES}


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _recordings_dirs_from_results(results_path: Path) -> List[Path]:
    """Read recordings path(s) from the source field of an existing results.json."""
    if not results_path.exists():
        return []
    data = json.loads(results_path.read_text(encoding="utf-8"))
    source = data.get("source") or {}
    dirs = source.get("recordings_dirs")
    if dirs:
        return [Path(d) for d in dirs]
    single = source.get("recordings_dir")
    if single:
        return [Path(single)]
    return []


def load_match_payloads_from_dirs(
    recordings_dirs: List[Path],
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Return (match_payloads, metadata_list) from match_*.json files in the given dirs."""
    match_files: List[Path] = []
    for directory in recordings_dirs:
        files = sorted(directory.glob("match_*.json"))
        if not files:
            raise FileNotFoundError(f"No match_*.json files found in {directory}")
        match_files.extend(files)

    match_payloads: List[Dict[str, Any]] = []
    metadata_list: List[Dict[str, Any]] = []
    seen_match_ids: Dict[str, Path] = {}

    for match_path in match_files:
        _, metadata, payload = load_match(match_path)
        match_id = str(payload.get("match_id") or "")
        if match_id and match_id in seen_match_ids:
            raise ValueError(
                f"Duplicate match_id '{match_id}' in {match_path} "
                f"and {seen_match_ids[match_id]}"
            )
        if match_id:
            seen_match_ids[match_id] = match_path
        match_payloads.append(payload)
        metadata_list.append(metadata)

    return match_payloads, metadata_list


def _list_matrix_cell_ids(experiment_dir: Path) -> List[str]:
    matrix = _load_yaml(experiment_dir / "matrix.yaml")
    return [cell["id"] for cell in matrix.get("cells", [])]


def _load_module_from_path(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load scorer module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _package_local_scorer_path(experiment_dir: Path) -> Path:
    return experiment_dir / "scripts" / "behavioral_scorer.py"


def _load_package_local_scorer(experiment_dir: Path) -> BehavioralScorer | None:
    scorer_path = _package_local_scorer_path(experiment_dir)
    if not scorer_path.exists():
        return None

    module = _load_module_from_path(scorer_path, "agentdeck_package_behavioral_scorer")

    scorer = getattr(module, "SCORER", None)
    if scorer is not None:
        if not isinstance(scorer, BehavioralScorer):
            raise ValueError(
                f"{scorer_path} defines SCORER, but it is not a BehavioralScorer instance"
            )
        return scorer

    scorer_classes = []
    for _, obj in inspect.getmembers(module, inspect.isclass):
        if not issubclass(obj, BehavioralScorer) or obj is BehavioralScorer:
            continue
        if getattr(obj, "__module__", None) != module.__name__:
            continue
        scorer_classes.append(obj)

    if not scorer_classes:
        raise ValueError(
            f"{scorer_path} must define SCORER or exactly one BehavioralScorer subclass"
        )
    if len(scorer_classes) > 1:
        names = ", ".join(sorted(cls.__name__ for cls in scorer_classes))
        raise ValueError(
            f"{scorer_path} defines multiple BehavioralScorer subclasses ({names}); "
            "export SCORER to disambiguate"
        )

    return scorer_classes[0]()


def _resolve_scorer(
    *,
    experiment_dir: Path,
    match_payloads: List[Dict[str, Any]],
    profile_id: str,
    trust_mode: str,
) -> Tuple[BehavioralScorer | None, str | None]:
    scorer_path = _package_local_scorer_path(experiment_dir)
    if scorer_path.exists() and trust_mode not in EXECUTABLE_TRUST_MODES:
        raise ValueError(
            "Package-local behavioral_scorer.py is executable Python. "
            "Choose trust_mode='trusted-local' for trusted code or invoke this command "
            "inside an isolated process with trust_mode='isolated'."
        )

    package_scorer = _load_package_local_scorer(experiment_dir)
    if package_scorer is not None:
        if not package_scorer.supports(match_payloads=match_payloads):
            raise ValueError(
                "Package-local scorer exists but does not support the supplied match payloads"
            )
        return package_scorer, "package_local"

    scorer = get_behavioral_scorer(match_payloads=match_payloads, profile_id=profile_id)
    if scorer is None:
        return None, None
    return scorer, "builtin"


def rescore_experiment(
    *,
    experiment_dir: Path,
    cell: Optional[str] = None,
    recordings_dir: Optional[Path] = None,
    profile_id: str = "auto",
    dry_run: bool = False,
    trust_mode: str = "structural",
) -> Dict[str, Any]:
    experiment_dir = experiment_dir.resolve()

    if trust_mode not in TRUST_MODES:
        raise ValueError(
            f"Unsupported trust_mode {trust_mode!r}; expected one of {sorted(TRUST_MODES)}"
        )

    if not experiment_dir.is_dir():
        raise FileNotFoundError(f"Experiment directory not found: {experiment_dir}")

    is_matrix = (experiment_dir / "matrix.yaml").exists()

    if is_matrix and cell is None:
        cell_ids = _list_matrix_cell_ids(experiment_dir)
        raise ValueError(
            f"--cell is required for matrix experiments because rescoring "
            f"updates one cell artifact at a time. "
            f"Available cells: {', '.join(cell_ids)}"
        )

    if is_matrix and cell:
        results_path = experiment_dir / "artifacts" / cell / "results.json"
        if not results_path.exists():
            raise FileNotFoundError(f"results.json not found for cell '{cell}': {results_path}")
        if recordings_dir is not None:
            resolved_recordings_dirs = [recordings_dir.resolve()]
        else:
            resolved_recordings_dirs = recordings_dirs_for_cell(experiment_dir, cell)
            if not resolved_recordings_dirs:
                raise FileNotFoundError(
                    f"No recordings found for cell '{cell}'. "
                    f"Provide --recordings-dir or ensure agentdeck_runs/{cell}/ exists."
                )
    else:
        results_path = experiment_dir / "results.json"
        if not results_path.exists():
            raise FileNotFoundError(f"results.json not found: {results_path}")
        if recordings_dir is not None:
            resolved_recordings_dirs = [recordings_dir.resolve()]
        else:
            resolved_recordings_dirs = _recordings_dirs_from_results(results_path)
            if not resolved_recordings_dirs:
                raise FileNotFoundError(
                    f"Could not resolve recordings path from {results_path}. "
                    f"Provide --recordings-dir explicitly."
                )

    match_payloads, metadata_list = load_match_payloads_from_dirs(resolved_recordings_dirs)
    players = collect_players(metadata_list)
    behavioral_config = behavioral_config_from_manifest(experiment_dir)
    package_scorer_path = _package_local_scorer_path(experiment_dir)
    if dry_run and package_scorer_path.exists() and trust_mode == "structural":
        return {
            "dry_run": True,
            "scorer_found": True,
            "scorer_source": "package_local",
            "profile_id": None,
            "profile_version": None,
            "recordings_dirs": [str(d) for d in resolved_recordings_dirs],
            "match_count": len(match_payloads),
            "results_path": str(results_path),
            "trust_mode": trust_mode,
            "execution_required": True,
        }

    scorer, scorer_source = _resolve_scorer(
        experiment_dir=experiment_dir,
        match_payloads=match_payloads,
        profile_id=profile_id,
        trust_mode=trust_mode,
    )

    if dry_run:
        return {
            "dry_run": True,
            "scorer_found": scorer is not None,
            "scorer_source": scorer_source,
            "profile_id": scorer.profile_id if scorer else None,
            "profile_version": scorer.profile_version if scorer else None,
            "recordings_dirs": [str(d) for d in resolved_recordings_dirs],
            "match_count": len(match_payloads),
            "results_path": str(results_path),
            "trust_mode": trust_mode,
        }

    if scorer is None:
        return {
            "scorer_found": False,
            "scorer_source": None,
            "profile_id": profile_id,
            "results_path": str(results_path),
            "updated": False,
            "trust_mode": trust_mode,
        }

    behavioral_profile = scorer.score(
        players=players,
        match_payloads=match_payloads,
        config=behavioral_config,
    )

    if behavioral_profile is None:
        return {
            "scorer_found": False,
            "scorer_source": scorer_source,
            "profile_id": profile_id,
            "results_path": str(results_path),
            "updated": False,
            "trust_mode": trust_mode,
        }

    results = json.loads(results_path.read_text(encoding="utf-8"))
    results["behavioral_profile"] = behavioral_profile
    results_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return {
        "scorer_found": True,
        "scorer_source": scorer_source,
        "profile_id": scorer.profile_id,
        "profile_version": scorer.profile_version,
        "recordings_dirs": [str(d) for d in resolved_recordings_dirs],
        "match_count": len(match_payloads),
        "results_path": str(results_path),
        "updated": True,
        "trust_mode": trust_mode,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agentdeck-research-score",
        description="Recompute the behavioral profile for a packaged experiment.",
    )
    parser.add_argument(
        "--experiment-dir",
        type=Path,
        required=True,
        help="Packaged experiment directory containing manifest.yaml and results.json.",
    )
    parser.add_argument(
        "--cell",
        type=str,
        default=None,
        help="Matrix cell ID (required for matrix experiments).",
    )
    parser.add_argument(
        "--recordings-dir",
        type=Path,
        default=None,
        help="Override recordings path from manifest or results.json.",
    )
    parser.add_argument(
        "--profile-id",
        type=str,
        default="auto",
        help="Scorer profile ID. 'auto' selects by game detection. 'none' disables scoring.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved scorer and coverage; do not write any files.",
    )
    parser.add_argument(
        "--trust-mode",
        choices=sorted(TRUST_MODES),
        default="structural",
        help=(
            "Trust declaration for package-local Python. 'structural' never imports it; "
            "'trusted-local' executes trusted code in-process; 'isolated' declares that "
            "the caller placed this command in an isolated process."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.profile_id == "none":
        print("Scoring disabled (--profile-id=none). Nothing to do.")
        return 0

    try:
        result = rescore_experiment(
            experiment_dir=args.experiment_dir,
            cell=args.cell,
            recordings_dir=args.recordings_dir,
            profile_id=args.profile_id,
            dry_run=args.dry_run,
            trust_mode=args.trust_mode,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1

    if args.dry_run:
        if result.get("scorer_found"):
            print(
                f"Scorer:       {result['profile_id']} v{result['profile_version']} "
                f"({result.get('scorer_source', 'unknown')})"
            )
        else:
            print(f"Scorer:       none (no scorer matched profile_id={args.profile_id!r})")
        print(f"Recordings:   {', '.join(result.get('recordings_dirs', []))}")
        print(f"Match count:  {result.get('match_count', 0)}")
        print(f"Results path: {result['results_path']}")
        print("(dry run — no files written)")
        return 0

    if not result.get("scorer_found"):
        print(f"No scorer matched for profile_id={args.profile_id!r}. " "results.json unchanged.")
        return 0

    print(
        f"Rescored: {result['results_path']} "
        f"({result['profile_id']} v{result['profile_version']}, "
        f"{result['match_count']} matches)"
    )
    return 0


__all__ = ["rescore_experiment", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
