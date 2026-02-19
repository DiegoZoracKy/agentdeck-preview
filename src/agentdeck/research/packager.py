"""Session-to-research package helper."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import yaml

from .provider_utils import provider_from_module

AUTO_FACTS_BEGIN = "<!-- AUTO_FACTS:BEGIN -->"
AUTO_FACTS_END = "<!-- AUTO_FACTS:END -->"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_script_function(script_name: str, func_name: str):
    script_path = _repo_root() / "scripts" / script_name
    if not script_path.exists():
        raise FileNotFoundError(f"Missing script: {script_path}")

    import importlib.util

    spec = importlib.util.spec_from_file_location(script_name.replace(".py", ""), script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, func_name):
        raise AttributeError(f"{script_path} missing {func_name}()")
    return getattr(module, func_name)


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


def _load_batch_data(records_dir: Path) -> Dict[str, Any]:
    batch_files = sorted(records_dir.glob("batch_*.json"))
    if not batch_files:
        raise FileNotFoundError(f"No batch_*.json files found in {records_dir}")
    return json.loads(batch_files[0].read_text(encoding="utf-8"))


def _load_match_files(records_dir: Path) -> List[Path]:
    match_files = sorted(records_dir.glob("match_*.json"))
    if not match_files:
        raise FileNotFoundError(f"No match_*.json files found in {records_dir}")
    return match_files


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


def _write_recordings_readme(path: Path, session_id: str, session_root: Path) -> None:
    content = "\n".join(
        [
            "# Recordings",
            "",
            f"- session_id: {session_id}",
            f"- session_path: {session_root}",
            "",
            "Recordings are stored outside the repository. This file points to the source session.",
            "",
        ]
    )
    path.write_text(content, encoding="utf-8")


def _format_pct(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"{numeric * 100:.1f}%"


def _format_usd(value: Any) -> str:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "N/A"
    return f"${numeric:.6f}"


def _replace_auto_facts_block(path: Path, lines: List[str]) -> None:
    if not path.exists():
        return

    content = path.read_text(encoding="utf-8")
    begin_idx = content.find(AUTO_FACTS_BEGIN)
    end_idx = content.find(AUTO_FACTS_END)

    if begin_idx == -1 or end_idx == -1 or end_idx < begin_idx:
        return

    insert_start = begin_idx + len(AUTO_FACTS_BEGIN)
    replacement = "\n" + "\n".join(lines).rstrip() + "\n"
    updated = content[:insert_start] + replacement + content[end_idx:]
    path.write_text(updated, encoding="utf-8")


def _player_label(player: Dict[str, Any]) -> str:
    player_id = player.get("id", "?")
    provider = player.get("provider", "unknown")
    model = player.get("model", "unknown")
    return f"{player_id}={provider}:{model}"


def _winner_topline(results: Dict[str, Any]) -> str:
    summary = results.get("summary") or {}
    win_rates = summary.get("win_rates") or {}
    if not isinstance(win_rates, dict) or not win_rates:
        return "No decisive winner (empty win_rates)"

    winner, rate = max(win_rates.items(), key=lambda item: float(item[1]))
    return f"{winner} ({_format_pct(rate)})"


def _first_player(results: Dict[str, Any]) -> str:
    matches = results.get("matches") or []
    if not matches:
        return "N/A"

    first = (matches[0].get("first_player") or {}).get("name")
    return first or "N/A"


def _load_results_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    if isinstance(payload, dict):
        return payload
    return {}


def _write_factual_markdown_blocks(dest_dir: Path, manifest: Dict[str, Any]) -> None:
    results = _load_results_json(dest_dir / "results.json")
    summary = results.get("summary") or {}
    run = manifest.get("run") or {}
    players = manifest.get("players") or []

    player_line = ", ".join(_player_label(player) for player in players) or "N/A"
    matches_planned = run.get("matches_planned", "N/A")
    matches_completed = run.get("matches_completed", "N/A")

    readme_lines = [
        f"- Status: {manifest.get('status', 'N/A')}",
        f"- Matches: {matches_completed}/{matches_planned}",
        f"- Game: {((manifest.get('game') or {}).get('name') or 'N/A')}",
        f"- Players: {player_line}",
        f"- Seed Base: {run.get('seed_base', 'N/A')}",
        f"- Topline Winner: {_winner_topline(results)}",
        f"- Avg Turns: {summary.get('avg_turns', 'N/A')}",
        f"- Avg Duration (s): {summary.get('avg_duration', 'N/A')}",
        f"- Total Cost: {_format_usd(summary.get('total_cost'))}",
    ]
    _replace_auto_facts_block(dest_dir / "README.md", readme_lines)

    analysis_lines = [
        f"- Sample size (`n`): {summary.get('total_matches', 'N/A')}",
        f"- Decisive matches: {summary.get('decisive_matches', 'N/A')}",
        f"- Draws: {summary.get('draws', 'N/A')}",
        f"- Win rates: {summary.get('win_rates', {})}",
        f"- Topline winner: {_winner_topline(results)}",
        f"- First player in first recorded match: {_first_player(results)}",
        f"- Average turns: {summary.get('avg_turns', 'N/A')}",
        f"- Average duration (s): {summary.get('avg_duration', 'N/A')}",
        f"- Total cost: {_format_usd(summary.get('total_cost'))}",
    ]
    _replace_auto_facts_block(dest_dir / "analysis.md", analysis_lines)


def _prune_matrix_references(manifest: Dict[str, Any]) -> None:
    run = manifest.get("run")
    if isinstance(run, dict):
        run.pop("matrix_source", None)

    artifacts = manifest.get("artifacts")
    if isinstance(artifacts, dict):
        artifacts.pop("matrix_yaml", None)


def package_session(
    *,
    session_dir: Optional[Path],
    session_id: Optional[str],
    run_dir: Path,
    research_dir: Path,
    experiment_id: Optional[str],
    question: str,
    status: Optional[str],
    title: Optional[str],
    include_matrix: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    if not question or not question.strip():
        raise ValueError("Question is required to create a research package.")
    if status and status not in {"planned", "running", "complete", "archived"}:
        raise ValueError(f"Unsupported status: {status}")

    session_root, records_dir, resolved_session_id = _resolve_session_paths(
        session_dir, session_id, run_dir
    )

    batch_data = _load_batch_data(records_dir)
    match_files = _load_match_files(records_dir)

    experiment_id = experiment_id or resolved_session_id
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
    if not include_matrix:
        _prune_matrix_references(manifest)

    if dry_run:
        return {
            "session_id": resolved_session_id,
            "session_root": session_root,
            "records_dir": records_dir,
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
    _write_recordings_readme(recordings_dir / "README.md", resolved_session_id, session_root)

    export_results = _load_script_function("research_export.py", "export_results")
    export_results(records_dir, dest_dir, experiment_id)
    _write_factual_markdown_blocks(dest_dir, manifest)

    generate_index = _load_script_function("research_index.py", "generate_index")
    index_content = generate_index(research_dir)
    (research_dir / "INDEX.md").write_text(index_content, encoding="utf-8")

    return {
        "session_id": resolved_session_id,
        "session_root": session_root,
        "records_dir": records_dir,
        "experiment_dir": dest_dir,
        "manifest": manifest,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a research package from an AgentDeck session."
    )
    parser.add_argument("--session-dir", type=Path, default=None)
    parser.add_argument("--session-id", type=str, default=None)
    parser.add_argument("--run-dir", type=Path, default=Path("agentdeck_runs"))
    parser.add_argument("--research-dir", type=Path, default=Path("research"))
    parser.add_argument("--experiment-id", type=str, default=None)
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
