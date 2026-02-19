#!/usr/bin/env python3
"""Run benchmark matrix cells (preflight/phase/custom) with AgentDeck-native components."""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml

# Local development import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

from agentdeck import (  # noqa: E402
    ActionOnlyController,
    AgentDeck,
    AgentDeckConfig,
    ClaudePlayer,
    FixedDamageGame,
    GeminiPlayer,
    GPTPlayer,
    LogLevel,
    ReasoningController,
)
from agentdeck.spectators import (  # noqa: E402
    ProgressDisplay,
    StatisticalAnalysisSpectator,
    StatsTracker,
    TokenUsageTracker,
)


@dataclass
class CellPlan:
    """Resolved execution plan for one matrix cell."""

    cell_id: str
    matches: int
    seed: int
    cell: Dict[str, Any]


def parse_args() -> argparse.Namespace:
    default_matrix = Path(__file__).resolve().parents[1] / "matrix.yaml"
    parser = argparse.ArgumentParser(
        description="Run matrix benchmark cells with AgentDeck-native execution flow."
    )
    parser.add_argument(
        "--matrix",
        type=Path,
        default=default_matrix,
        help=f"Path to matrix.yaml (default: {default_matrix})",
    )
    parser.add_argument(
        "--mode",
        choices=["preflight", "phase", "cells"],
        default="preflight",
        help="Execution selection mode (default: preflight).",
    )
    parser.add_argument(
        "--phase-id",
        type=str,
        default=None,
        help="Phase id when --mode phase (e.g., A1).",
    )
    parser.add_argument(
        "--cell-id",
        action="append",
        default=[],
        help="Specific cell id(s) when --mode cells. Can be repeated.",
    )
    parser.add_argument(
        "--matches-per-cell",
        type=int,
        default=None,
        help="Override matches for every selected cell.",
    )
    parser.add_argument(
        "--seed-base",
        type=int,
        default=420000,
        help="Base seed for first selected cell (default: 420000).",
    )
    parser.add_argument(
        "--seed-step",
        type=int,
        default=1000,
        help="Seed increment between selected cells (default: 1000).",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Session concurrency (default: 10).",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        default=30,
        help="Turn cap per match (default: 30).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Sampling temperature for all players (default: 1.0).",
    )
    parser.add_argument(
        "--anthropic-max-tokens",
        type=int,
        default=8192,
        help="High required max_tokens for Anthropic requests (default: 8192).",
    )
    parser.add_argument(
        "--google-project-id",
        type=str,
        default=os.getenv("VERTEX_PROJECT_ID"),
        help="Google Vertex project id (default: $VERTEX_PROJECT_ID).",
    )
    parser.add_argument(
        "--google-location",
        type=str,
        default=os.getenv("VERTEX_LOCATION", "us-central1"),
        help="Google Vertex location (default: $VERTEX_LOCATION or us-central1).",
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="Continue with next cells if one cell fails.",
    )
    parser.add_argument(
        "--log-level",
        choices=["debug", "info", "off"],
        default="info",
        help="Console log level (default: info).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print resolved plan and provider requirements without execution.",
    )
    return parser.parse_args()


def load_matrix(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Matrix file not found: {path}")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid matrix payload (expected mapping): {path}")
    return payload


def _cells_by_id(matrix: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    raw_cells = matrix.get("cells") or []
    by_id: Dict[str, Dict[str, Any]] = {}
    for cell in raw_cells:
        cell_id = cell.get("id")
        if not cell_id:
            continue
        by_id[cell_id] = cell
    return by_id


def _select_cells(args: argparse.Namespace, matrix: Dict[str, Any]) -> List[str]:
    exec_plan = matrix.get("execution_plan") or {}
    if args.mode == "preflight":
        preflight = exec_plan.get("preflight") or {}
        cell_ids = preflight.get("cell_ids") or []
        if not cell_ids:
            raise ValueError("No preflight cell_ids configured in matrix.yaml")
        return list(cell_ids)

    if args.mode == "phase":
        if not args.phase_id:
            raise ValueError("--phase-id is required when --mode phase")
        phases = exec_plan.get("phases") or []
        for phase in phases:
            if phase.get("phase_id") == args.phase_id:
                cell_ids = phase.get("cell_ids") or []
                if not cell_ids:
                    raise ValueError(f"Phase {args.phase_id} has no cell_ids.")
                return list(cell_ids)
        raise ValueError(f"Unknown phase_id: {args.phase_id}")

    if args.mode == "cells":
        if not args.cell_id:
            raise ValueError("--cell-id is required when --mode cells")
        return list(args.cell_id)

    raise ValueError(f"Unsupported mode: {args.mode}")


def _resolve_cell_matches(
    args: argparse.Namespace,
    matrix: Dict[str, Any],
    cell: Dict[str, Any],
) -> int:
    if args.matches_per_cell is not None:
        return args.matches_per_cell

    if args.mode == "preflight":
        preflight = (matrix.get("execution_plan") or {}).get("preflight") or {}
        return int(preflight.get("matches_per_cell", 6))

    if "pilot_matches" in cell:
        return int(cell["pilot_matches"])

    sampling = matrix.get("sampling_policy") or {}
    return int(sampling.get("pilot_matches_per_cell", 24))


def build_cell_plans(args: argparse.Namespace, matrix: Dict[str, Any]) -> List[CellPlan]:
    selected = _select_cells(args, matrix)
    by_id = _cells_by_id(matrix)
    plans: List[CellPlan] = []
    for idx, cell_id in enumerate(selected):
        if cell_id not in by_id:
            raise ValueError(f"Cell id not found in matrix: {cell_id}")
        cell = by_id[cell_id]
        matches = _resolve_cell_matches(args, matrix, cell)
        seed = int(args.seed_base + idx * args.seed_step)
        plans.append(CellPlan(cell_id=cell_id, matches=matches, seed=seed, cell=cell))
    return plans


def _build_controller(controller_name: str):
    if controller_name == "ActionOnlyController":
        return ActionOnlyController()
    if controller_name == "ReasoningController":
        return ReasoningController()
    raise ValueError(f"Unsupported controller: {controller_name}")


def _resolve_log_level(value: str):
    mapping = {
        "debug": LogLevel.DEBUG,
        "info": LogLevel.INFO,
        "off": None,
    }
    return mapping[value]


def _required_providers(plans: List[CellPlan], matrix: Dict[str, Any]) -> List[str]:
    registry = matrix.get("model_registry") or {}
    providers = set()
    for plan in plans:
        for side in ("player_a", "player_b"):
            model_ref = (plan.cell.get(side) or {}).get("model_ref")
            provider = (registry.get(model_ref) or {}).get("provider")
            if provider:
                providers.add(provider)
    return sorted(providers)


def _validate_provider_requirements(args: argparse.Namespace, providers: List[str]) -> None:
    if "openai" in providers and not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is required for selected cells.")
    if "anthropic" in providers and not os.getenv("ANTHROPIC_API_KEY"):
        raise RuntimeError("ANTHROPIC_API_KEY is required for selected cells.")
    if "google" in providers and not args.google_project_id:
        raise RuntimeError(
            "VERTEX_PROJECT_ID (or --google-project-id) is required for selected Google cells."
        )


def _build_player(
    *,
    slot: str,
    side: Dict[str, Any],
    matrix: Dict[str, Any],
    args: argparse.Namespace,
):
    model_registry = matrix.get("model_registry") or {}
    config_registry = matrix.get("config_registry") or {}

    model_ref = side.get("model_ref")
    config_ref = side.get("config_ref")
    model_cfg = model_registry.get(model_ref) or {}
    run_cfg = config_registry.get(config_ref) or {}

    provider = model_cfg.get("provider")
    model_name = model_cfg.get("model")
    controller_name = run_cfg.get("controller")
    if not provider or not model_name or not controller_name:
        raise ValueError(
            f"Incomplete cell config. model_ref={model_ref} config_ref={config_ref} "
            f"provider={provider} model={model_name} controller={controller_name}"
        )

    prompt_builder = run_cfg.get("prompt_builder") or {}
    turn_template_mode = prompt_builder.get("turn_template_mode", "default")
    turn_template = prompt_builder.get("turn_template")

    player_name = f"{model_name}-{slot}"
    kwargs: Dict[str, Any] = {
        "name": player_name,
        "model": model_name,
        "controller": _build_controller(controller_name),
        "temperature": args.temperature,
    }

    if turn_template_mode == "custom" and turn_template:
        kwargs["turn_template"] = turn_template

    if provider == "openai":
        return GPTPlayer(**kwargs)
    if provider == "anthropic":
        kwargs["max_tokens"] = args.anthropic_max_tokens
        return ClaudePlayer(**kwargs)
    if provider == "google":
        kwargs["project_id"] = args.google_project_id
        kwargs["location"] = args.google_location
        return GeminiPlayer(**kwargs)

    raise ValueError(f"Unsupported provider in matrix: {provider}")


def _build_game() -> FixedDamageGame:
    return FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=2,
        information_level="partial",
    )


def _print_plan(plans: List[CellPlan], providers: List[str]) -> None:
    print("=" * 70)
    print("Resolved Matrix Run Plan")
    print("=" * 70)
    print(f"Cells: {len(plans)}")
    print(f"Providers required: {providers}")
    print("-" * 70)
    for plan in plans:
        q = plan.cell.get("question", "")
        print(
            f"{plan.cell_id}: matches={plan.matches}, seed={plan.seed}, "
            f"phase={plan.cell.get('phase')}, track={plan.cell.get('track')}"
        )
        print(f"  Question: {q}")
    print("=" * 70)


def main() -> None:
    args = parse_args()
    matrix = load_matrix(args.matrix)
    plans = build_cell_plans(args, matrix)
    providers = _required_providers(plans, matrix)
    _validate_provider_requirements(args, providers)
    _print_plan(plans, providers)

    if args.dry_run:
        print("Dry run complete. No matches executed.")
        return

    spectators = [
        ProgressDisplay(),
        StatsTracker(),
        TokenUsageTracker(),
        StatisticalAnalysisSpectator(print_on_complete=True, save_report=False),
    ]
    config = AgentDeckConfig(
        seed=args.seed_base,
        concurrency=args.concurrency,
        max_turns=args.max_turns,
        log_level=_resolve_log_level(args.log_level),
    )
    failures: List[str] = []

    with AgentDeck(game=_build_game(), session=config, spectators=spectators) as deck:
        for index, plan in enumerate(plans, start=1):
            print(f"\n[{index}/{len(plans)}] Running cell {plan.cell_id}")
            try:
                players = [
                    _build_player(slot="A", side=plan.cell["player_a"], matrix=matrix, args=args),
                    _build_player(slot="B", side=plan.cell["player_b"], matrix=matrix, args=args),
                ]
                results = deck.play(players=players, matches=plan.matches, seed=plan.seed)
                winner, win_rate = max(results.win_rates.items(), key=lambda item: float(item[1]))
                print(
                    f"Cell {plan.cell_id} complete: winner={winner}, "
                    f"win_rate={win_rate:.3f}, matches={plan.matches}"
                )
            except Exception as exc:  # pragma: no cover - runtime guard
                message = f"Cell {plan.cell_id} failed: {exc}"
                failures.append(message)
                print(message)
                if not args.continue_on_error:
                    raise

        stats = deck.get_session_stats()
        print("\nSession Artifacts")
        print(f"  Session ID: {stats['session_id']}")
        print(f"  Logs: {stats['log_directory']}")
        print(f"  Records: {stats['record_directory']}")

    if failures:
        print("\nFailures:")
        for failure in failures:
            print(f"  - {failure}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
