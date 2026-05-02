"""Session-to-research package helper."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

from .export import export_results
from .factual_blocks import write_factual_markdown_blocks
from .index import generate_index
from .provider_utils import provider_from_module

RESEARCH_EXPERIMENT_PREFIX = "research_"
SESSION_PREFIX = "session_"


def normalize_research_experiment_id(experiment_id: str) -> str:
    """Return the process-owned research package id with the research_ prefix."""
    normalized = str(experiment_id or "").strip()
    if not normalized:
        raise ValueError("experiment_id must be non-empty")
    if normalized.startswith(RESEARCH_EXPERIMENT_PREFIX):
        return normalized
    if normalized.startswith(SESSION_PREFIX):
        return f"{RESEARCH_EXPERIMENT_PREFIX}{normalized[len(SESSION_PREFIX):]}"
    return f"{RESEARCH_EXPERIMENT_PREFIX}{normalized}"


def _resolve_session_paths(
    session_dir: Optional[Path],
    session_id: Optional[str],
    run_dir: Path,
) -> Tuple[Path, Path, str]:
    if session_dir:
        session_dir = session_dir.resolve()
        if (session_dir / "records").is_dir():
            session_root = session_dir
            records_dir = session_dir / "records"
        elif session_dir.name == "records" and session_dir.is_dir():
            records_dir = session_dir
            session_root = session_dir.parent
        else:
            raise FileNotFoundError(f"Session directory must contain records/: {session_dir}")
        session_id = session_root.name
    else:
        if not session_id:
            raise ValueError("Provide --session-dir or --session-id.")
        session_root = run_dir / session_id
        records_dir = session_root / "records"

    if not records_dir.is_dir():
        raise FileNotFoundError(f"Records directory not found: {records_dir}")

    return session_root, records_dir, session_id


def _resolve_session_inputs(
    session_dir: Optional[Path],
    session_id: Optional[str],
    session_dirs: Optional[Sequence[Path]],
    session_ids: Optional[Sequence[str]],
    run_dir: Path,
) -> List[Tuple[Path, Path, str]]:
    inputs: List[Tuple[str, Any]] = []
    if session_dir is not None:
        inputs.append(("dir", session_dir))
    if session_id:
        inputs.append(("id", session_id))
    for entry in session_dirs or []:
        inputs.append(("dir", entry))
    for entry in session_ids or []:
        inputs.append(("id", entry))

    if not inputs:
        raise ValueError("Provide --session-dir/--session-id or --session-dirs/--session-ids.")

    resolved: List[Tuple[Path, Path, str]] = []
    seen_ids = set()
    for input_type, value in inputs:
        if input_type == "dir":
            session_root, records_dir, resolved_session_id = _resolve_session_paths(
                Path(value), None, run_dir
            )
        else:
            session_root, records_dir, resolved_session_id = _resolve_session_paths(
                None, str(value), run_dir
            )
        if resolved_session_id in seen_ids:
            continue
        seen_ids.add(resolved_session_id)
        resolved.append((session_root, records_dir, resolved_session_id))

    return resolved


def _merge_batch_payloads(batches: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not batches:
        raise FileNotFoundError("No batch payloads available for aggregation.")
    if len(batches) == 1:
        return batches[0]

    merged = dict(batches[0])
    merged_metadata = dict((merged.get("metadata") or {}))
    merged_match_refs: List[Dict[str, Any]] = []

    total_planned = 0
    total_completed = 0
    seeds_used: List[int] = []
    started_at: Optional[str] = None
    ended_at: Optional[str] = None

    for batch in batches:
        batch_match_refs = batch.get("match_refs") or []
        batch_metadata = batch.get("metadata") or {}

        merged_match_refs.extend(batch_match_refs)

        planned = batch_metadata.get("matches_planned")
        if planned is None:
            planned = len(batch_match_refs)
        completed = batch_metadata.get("matches_completed")
        if completed is None:
            completed = len(batch_match_refs)

        total_planned += int(planned)
        total_completed += int(completed)

        for seed in batch_metadata.get("seeds_used") or []:
            if seed not in seeds_used:
                seeds_used.append(seed)

        batch_started = batch_metadata.get("started_at")
        if batch_started and (started_at is None or batch_started < started_at):
            started_at = batch_started

        batch_ended = batch_metadata.get("ended_at")
        if batch_ended and (ended_at is None or batch_ended > ended_at):
            ended_at = batch_ended

    merged["match_refs"] = merged_match_refs
    merged_metadata["matches_planned"] = total_planned
    merged_metadata["matches_completed"] = total_completed
    if seeds_used:
        merged_metadata["seeds_used"] = seeds_used
    if started_at:
        merged_metadata["started_at"] = started_at
    if ended_at:
        merged_metadata["ended_at"] = ended_at
    merged["metadata"] = merged_metadata

    return merged


def _load_batch_data(records_dir: Path) -> Dict[str, Any]:
    batch_files = sorted(records_dir.glob("batch_*.json"))
    if not batch_files:
        raise FileNotFoundError(f"No batch_*.json files found in {records_dir}")

    batches = [json.loads(path.read_text(encoding="utf-8")) for path in batch_files]
    return _merge_batch_payloads(batches)


def _load_match_files(records_dir: Path) -> List[Path]:
    match_files = sorted(records_dir.glob("match_*.json"))
    if not match_files:
        raise FileNotFoundError(f"No match_*.json files found in {records_dir}")
    return match_files


def _load_match_files_from_sessions(records_dirs: Sequence[Path]) -> List[Path]:
    combined: List[Path] = []
    seen_match_ids: Dict[str, Path] = {}
    for records_dir in records_dirs:
        for path in _load_match_files(records_dir):
            match_id = path.stem
            if match_id in seen_match_ids:
                raise ValueError(
                    f"Duplicate match file id '{match_id}' across sessions: "
                    f"{seen_match_ids[match_id]} and {path}"
                )
            seen_match_ids[match_id] = path
            combined.append(path)
    return combined


def _infer_game_name(metadata: Dict[str, Any]) -> Optional[str]:
    if metadata.get("game"):
        return metadata.get("game")
    config = metadata.get("configuration") or {}
    game_config = config.get("game") or {}
    return game_config.get("name")


def _collect_player_summaries(match_refs: Iterable[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    summaries: Dict[str, Dict[str, Any]] = {}
    for match_ref in match_refs:
        for summary in match_ref.get("player_summaries") or []:
            name = summary.get("name")
            if not name or name in summaries:
                continue
            summaries[name] = summary
    return summaries


def _collect_player_configs(metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
    config = metadata.get("configuration") or {}
    players = config.get("players") or []
    return [p for p in players if p.get("name")]


def _player_order(metadata: Dict[str, Any], player_names: List[str]) -> List[str]:
    config_players = _collect_player_configs(metadata)
    if config_players:
        return [p["name"] for p in config_players if p.get("name")]
    meta_players = metadata.get("players") or []
    if meta_players:
        return list(meta_players)
    return sorted(player_names)


def _infer_players(
    metadata: Dict[str, Any], match_refs: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    config_players = _collect_player_configs(metadata)
    summaries = _collect_player_summaries(match_refs)

    player_names = set()
    for player in config_players:
        player_names.add(player["name"])
    player_names.update(summaries.keys())

    ordered_names = _player_order(metadata, sorted(player_names))

    name_to_provider: Dict[str, str] = {}
    for player in config_players:
        module = player.get("module", "")
        provider = provider_from_module(module)
        name_to_provider[player["name"]] = provider

    players: List[Dict[str, Any]] = []
    for idx, name in enumerate(ordered_names):
        provider = name_to_provider.get(name)
        summary = summaries.get(name) or {}
        entry: Dict[str, Any] = {
            "id": chr(ord("A") + idx) if idx < 26 else f"P{idx + 1}",
            "provider": provider,
            "model": summary.get("model"),
        }
        if summary.get("controller") is not None:
            entry["controller"] = summary.get("controller")
        if summary.get("renderer") is not None:
            entry["renderer"] = summary.get("renderer")
        players.append(entry)

    missing = []
    for entry in players:
        if not entry.get("provider") or entry["provider"] == "unknown":
            missing.append(f"provider:{entry.get('id')}")
        if not entry.get("model"):
            missing.append(f"model:{entry.get('id')}")

    if missing:
        raise ValueError(f"Missing required player fields: {', '.join(missing)}")

    return players


def _session_compatibility_signature(
    batch_data: Dict[str, Any],
) -> Tuple[str, Tuple[Tuple[Any, ...], ...]]:
    metadata = batch_data.get("metadata") or {}
    match_refs = batch_data.get("match_refs") or []
    game_name = _infer_game_name(metadata) or ""
    players = _infer_players(metadata, match_refs)
    signature_players = tuple(
        (
            player.get("id"),
            player.get("provider"),
            player.get("model"),
            player.get("controller"),
            player.get("renderer"),
        )
        for player in players
    )
    return game_name, signature_players


def _validate_session_compatibility(session_batches: Sequence[Dict[str, Any]]) -> None:
    if len(session_batches) <= 1:
        return
    baseline = _session_compatibility_signature(session_batches[0])
    for idx, batch_data in enumerate(session_batches[1:], start=2):
        current = _session_compatibility_signature(batch_data)
        if current != baseline:
            raise ValueError(
                "Incompatible sessions for checkpoint aggregation: "
                f"session #{idx} differs in game or player identity/model/controller."
            )


def _infer_seed_base(metadata: Dict[str, Any], match_files: List[Path]) -> Optional[int]:
    seeds = metadata.get("seeds_used") or []
    if seeds:
        return seeds[0]

    if match_files:
        data = json.loads(match_files[0].read_text(encoding="utf-8"))
        seed = data.get("seed")
        if seed is not None:
            return seed

    return None


def _derive_status(matches_planned: int, matches_completed: int) -> str:
    if matches_completed <= 0:
        return "planned"
    if matches_planned and matches_completed >= matches_planned:
        return "complete"
    return "running"


def _infer_variants(players: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    models = sorted(
        {
            str(player.get("model"))
            for player in players
            if player.get("model") is not None and str(player.get("model")).strip()
        }
    )
    controllers = sorted(
        {
            str(player.get("controller"))
            for player in players
            if player.get("controller") is not None and str(player.get("controller")).strip()
        }
    )

    variants: Dict[str, List[str]] = {}
    if models:
        variants["models"] = models
    if controllers:
        variants["controllers"] = controllers
    return variants


def build_manifest(
    *,
    template_path: Path,
    experiment_id: str,
    question: str,
    batch_data: Dict[str, Any],
    match_files: List[Path],
    status: Optional[str] = None,
    title: Optional[str] = None,
) -> Dict[str, Any]:
    experiment_id = normalize_research_experiment_id(experiment_id)
    manifest = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    metadata = batch_data.get("metadata") or {}
    match_refs = batch_data.get("match_refs") or []

    game_name = _infer_game_name(metadata)
    if not game_name:
        raise ValueError("Unable to infer game.name from batch metadata.")

    matches_completed = metadata.get("matches_completed")
    if matches_completed is None:
        matches_completed = len(match_refs) or len(match_files)

    matches_planned = metadata.get("matches_planned")
    if matches_planned is None:
        matches_planned = matches_completed

    seed_base = _infer_seed_base(metadata, match_files)
    if seed_base is None:
        raise ValueError("Unable to infer run.seed_base from recordings.")

    players = _infer_players(metadata, match_refs)

    manifest["schema_version"] = 1
    manifest["experiment_id"] = experiment_id
    manifest["title"] = title or experiment_id
    manifest["status"] = status or _derive_status(matches_planned, matches_completed)
    manifest["question"] = question
    manifest.setdefault("game", {})
    manifest["game"]["name"] = game_name
    manifest["players"] = players
    variants = _infer_variants(players)
    if variants:
        manifest["variants"] = variants
    else:
        manifest.pop("variants", None)

    manifest.setdefault("run", {})
    manifest["run"]["seed_base"] = int(seed_base)
    manifest["run"]["matches_planned"] = int(matches_planned)
    manifest["run"]["matches_completed"] = int(matches_completed)

    if metadata.get("started_at"):
        manifest["started_at"] = metadata.get("started_at")
    if metadata.get("ended_at"):
        manifest["completed_at"] = metadata.get("ended_at")

    return manifest


def _write_manifest(path: Path, manifest: Dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def _write_recordings_readme(path: Path, session_sources: Sequence[Tuple[str, Path]]) -> None:
    lines = ["# Recordings", ""]
    if len(session_sources) == 1:
        session_id, session_root = session_sources[0]
        lines.extend(
            [
                f"- session_id: {session_id}",
                f"- session_path: {session_root}",
            ]
        )
    else:
        lines.extend(
            [
                "- source_mode: multi-session-checkpoints",
                f"- source_count: {len(session_sources)}",
                "- sessions:",
            ]
        )
        for session_id, session_root in session_sources:
            lines.append(f"  - {session_id}: {session_root}")

    lines.extend(
        [
            "",
            "Recordings are stored outside the repository. This file points to the source session(s).",
            "",
        ]
    )
    content = "\n".join(lines)
    path.write_text(content, encoding="utf-8")


def _prune_matrix_references(manifest: Dict[str, Any]) -> None:
    run = manifest.get("run")
    if isinstance(run, dict):
        run.pop("matrix_source", None)

    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        artifacts.pop("matrix_yaml", None)


def package_session(
    *,
    run_dir: Path,
    research_dir: Path,
    question: str,
    session_dir: Optional[Path] = None,
    session_id: Optional[str] = None,
    session_dirs: Optional[Sequence[Path]] = None,
    session_ids: Optional[Sequence[str]] = None,
    experiment_id: Optional[str] = None,
    status: Optional[str] = None,
    title: Optional[str] = None,
    include_matrix: bool = False,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if not question or not question.strip():
        raise ValueError("Question is required to create a research package.")
    if status and status not in {"planned", "running", "complete", "archived"}:
        raise ValueError(f"Unsupported status: {status}")

    resolved_sessions = _resolve_session_inputs(
        session_dir, session_id, session_dirs, session_ids, run_dir
    )
    session_roots = [entry[0] for entry in resolved_sessions]
    records_dirs = [entry[1] for entry in resolved_sessions]
    resolved_session_ids = [entry[2] for entry in resolved_sessions]

    session_batches = [_load_batch_data(records_dir) for records_dir in records_dirs]
    _validate_session_compatibility(session_batches)
    batch_data = _merge_batch_payloads(session_batches)
    match_files = _load_match_files_from_sessions(records_dirs)

    experiment_id = normalize_research_experiment_id(experiment_id or resolved_session_ids[0])
    template_dir = research_dir / "_templates"
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Missing templates directory: {template_dir}")

    dest_dir = research_dir / experiment_id
    if dest_dir.exists():
        raise FileExistsError(f"Experiment directory already exists: {dest_dir}")

    manifest = build_manifest(
        template_path=template_dir / "manifest.yaml",
        experiment_id=experiment_id,
        question=question,
        batch_data=batch_data,
        match_files=match_files,
        status=status,
        title=title,
    )
    if len(resolved_session_ids) > 1:
        manifest.setdefault("run", {})
        manifest["run"]["source_sessions"] = resolved_session_ids
    if not include_matrix:
        _prune_matrix_references(manifest)

    if dry_run:
        return {
            "session_id": resolved_session_ids[0],
            "session_ids": resolved_session_ids,
            "session_root": session_roots[0],
            "session_roots": session_roots,
            "records_dir": records_dirs[0],
            "records_dirs": records_dirs,
            "experiment_dir": dest_dir,
            "manifest": manifest,
        }

    shutil.copytree(template_dir, dest_dir)
    if not include_matrix:
        matrix_path = dest_dir / "matrix.yaml"
        if matrix_path.exists():
            matrix_path.unlink()

    _write_manifest(dest_dir / "manifest.yaml", manifest)

    recordings_dir = dest_dir / "recordings"
    recordings_dir.mkdir(parents=True, exist_ok=True)
    _write_recordings_readme(
        recordings_dir / "README.md",
        list(zip(resolved_session_ids, session_roots)),
    )

    if len(records_dirs) == 1:
        export_results(records_dirs[0], dest_dir, experiment_id)
    else:
        export_results(records_dirs, dest_dir, experiment_id)
    write_factual_markdown_blocks(dest_dir, manifest)

    index_content = generate_index(research_dir)
    (research_dir / "INDEX.md").write_text(index_content, encoding="utf-8")

    return {
        "session_id": resolved_session_ids[0],
        "session_ids": resolved_session_ids,
        "session_root": session_roots[0],
        "session_roots": session_roots,
        "records_dir": records_dirs[0],
        "records_dirs": records_dirs,
        "experiment_dir": dest_dir,
        "manifest": manifest,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a research package from an AgentDeck session."
    )
    parser.add_argument("--session-dir", type=Path, default=None)
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument(
        "--session-dirs",
        nargs="+",
        type=Path,
        default=None,
        help="Checkpoint mode: package from multiple session roots.",
    )
    parser.add_argument(
        "--session-ids",
        nargs="+",
        type=str,
        default=None,
        help="Checkpoint mode: package from multiple session ids under --run-dir.",
    )
    parser.add_argument("--run-dir", type=Path, default=Path("agentdeck_runs"))
    parser.add_argument("--research-dir", type=Path, default=Path("research"))
    parser.add_argument(
        "--experiment-id",
        type=str,
        default=None,
        help="Experiment id. The research_ prefix is added when omitted.",
    )
    parser.add_argument("--question", type=str, required=True)
    parser.add_argument(
        "--status", type=str, choices=["planned", "running", "complete", "archived"]
    )
    parser.add_argument("--title", type=str, default=None)
    parser.add_argument(
        "--include-matrix",
        action="store_true",
        help="Include matrix.yaml scaffold (recommended only for benchmark grids).",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    result = package_session(
        session_dir=args.session_dir,
        session_id=args.session_id,
        session_dirs=args.session_dirs,
        session_ids=args.session_ids,
        run_dir=args.run_dir,
        research_dir=args.research_dir,
        experiment_id=args.experiment_id,
        question=args.question,
        status=args.status,
        title=args.title,
        include_matrix=args.include_matrix,
        dry_run=args.dry_run,
    )

    if args.dry_run:
        manifest = result.get("manifest", {})
        print("Dry run: no files written.")
        print(f"Experiment dir: {result.get('experiment_dir')}")
        print(yaml.safe_dump(manifest, sort_keys=False))
    else:
        print(f"Experiment created: {result.get('experiment_dir')}")


if __name__ == "__main__":
    main()
