#!/usr/bin/env python3
"""Run FixedDamage Mini Parity 1 cells using AgentDeck-native configuration only."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agentdeck import AgentDeck, AgentDeckConfig, ConclusionPolicy, FixedDamageGame
from agentdeck.controllers import ActionOnlyController, ReasoningController
from agentdeck.players import ClaudePlayer, GPTPlayer, GeminiPlayer


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
MATRIX_PATH = EXPERIMENT_DIR / "matrix.yaml"
MANIFEST_PATH = EXPERIMENT_DIR / "manifest.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _controller_from_name(name: str):
    if name == "ActionOnlyController":
        return ActionOnlyController
    if name == "ReasoningController":
        return ReasoningController
    raise ValueError(f"Unsupported controller in matrix: {name}")


def _llm_from_provider(provider: str):
    if provider == "openai":
        return GPTPlayer
    if provider == "anthropic":
        return ClaudePlayer
    if provider == "google":
        return GeminiPlayer
    raise ValueError(f"Unsupported provider in matrix: {provider}")


def _build_player(
    side: Dict[str, Any],
    *,
    player_registry: Dict[str, Dict[str, Any]],
    config_registry: Dict[str, Dict[str, Any]],
):
    player_spec = player_registry[side["player_ref"]]
    config_spec = config_registry[side["config_ref"]]
    controller_cls = _controller_from_name(config_spec["controller"])
    prompt_builder = config_spec.get("prompt_builder", {})

    common_kwargs = {
        "name": side["name"],
        "controller": controller_cls(),
    }

    if prompt_builder.get("handshake_template") is not None:
        common_kwargs["handshake_template"] = prompt_builder["handshake_template"]
    if prompt_builder.get("turn_template") is not None:
        common_kwargs["turn_template"] = prompt_builder["turn_template"]

    kind = player_spec["kind"]
    if kind == "llm":
        player_cls = _llm_from_provider(player_spec["provider"])
        llm_kwargs = {"model": player_spec["model"], **common_kwargs}
        for key in ("temperature", "max_tokens", "max_retries", "retry_delay"):
            if player_spec.get(key) is not None:
                llm_kwargs[key] = player_spec[key]
        if player_spec.get("generation_config") is not None:
            llm_kwargs["generation_config"] = dict(player_spec["generation_config"])
        return player_cls(**llm_kwargs)

    raise ValueError(f"Unsupported player kind in matrix: {kind}")


def _build_game(cell: Dict[str, Any], manifest: Dict[str, Any]) -> FixedDamageGame:
    game_config = dict((manifest.get("game") or {}).get("config") or {})
    game_config.update(cell.get("game") or {})
    return FixedDamageGame(**game_config)


def _iter_selected_cells(matrix: Dict[str, Any], *, phase: str | None, cell_ids: set[str] | None):
    phase_to_cells: Dict[str, set[str]] = {}
    for phase_entry in matrix.get("execution_plan", {}).get("phases", []):
        phase_to_cells[phase_entry["phase_id"]] = set(phase_entry.get("cell_ids", []))

    for cell in matrix.get("cells", []):
        if phase and cell["id"] not in phase_to_cells.get(phase, set()):
            continue
        if cell_ids and cell["id"] not in cell_ids:
            continue
        yield cell


def _list_cells(matrix: Dict[str, Any]) -> None:
    for cell in matrix.get("cells", []):
        print(f"{cell['id']} [{cell['phase']}] - {cell['question']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", help="Run all cells in one phase (e.g. P1)")
    parser.add_argument("--cell", action="append", dest="cells", help="Run one or more specific cell IDs")
    parser.add_argument("--list-cells", action="store_true", help="List available cells and exit")
    parser.add_argument("--matches", type=int, help="Override matches for every selected cell")
    parser.add_argument("--concurrency", type=int, help="Override session concurrency")
    parser.add_argument("--dry-run", action="store_true", help="Print execution plan without running")
    args = parser.parse_args()

    matrix = _load_yaml(MATRIX_PATH)
    manifest = _load_yaml(MANIFEST_PATH)

    if args.list_cells:
        _list_cells(matrix)
        return

    selected = list(
        _iter_selected_cells(
            matrix,
            phase=args.phase,
            cell_ids=set(args.cells or []) or None,
        )
    )

    if not selected:
        raise SystemExit("No cells selected. Use --list-cells, --phase, or --cell.")

    player_registry = matrix["player_registry"]
    config_registry = matrix["config_registry"]
    manifest_run = manifest["run"]
    base_seed = manifest_run["seed_base"]
    default_concurrency = args.concurrency or manifest_run.get("concurrency", 1)
    max_turns = manifest_run.get("max_turns", 30)

    for cell in selected:
        player_a_config = config_registry[cell["player_a"]["config_ref"]]
        player_b_config = config_registry[cell["player_b"]["config_ref"]]
        if player_a_config["pairing_policy"] != player_b_config["pairing_policy"]:
            raise ValueError(f"{cell['id']}: pairing_policy mismatch between players")
        if player_a_config["first_player_policy"] != player_b_config["first_player_policy"]:
            raise ValueError(f"{cell['id']}: first_player_policy mismatch between players")

        pairing_policy = player_a_config["pairing_policy"]
        first_player_policy = player_a_config["first_player_policy"]
        conclusion_cfg = player_a_config.get("conclusion", {"enabled": False})
        run_dir = EXPERIMENT_DIR / "agentdeck_runs" / cell["id"]
        matches = args.matches or cell["matches"]
        seed = base_seed + int(cell.get("seed_offset", 0))

        print("=" * 72)
        print(f"Cell: {cell['id']}")
        print(f"Question: {cell['question']}")
        print(f"Run dir: {run_dir}")
        print(f"Matches: {matches}")
        print(f"Seed: {seed}")
        print(f"Pairing: {pairing_policy} | First player: {first_player_policy}")

        if args.dry_run:
            continue

        deck = AgentDeck(
            game=_build_game(cell, manifest),
            session=AgentDeckConfig(
                seed=seed,
                run_dir=str(run_dir),
                max_turns=max_turns,
                concurrency=default_concurrency,
                pairing_policy=pairing_policy,
                first_player_policy=first_player_policy,
                conclusion=ConclusionPolicy(**conclusion_cfg),
            ),
        )

        players = [
            _build_player(cell["player_a"], player_registry=player_registry, config_registry=config_registry),
            _build_player(cell["player_b"], player_registry=player_registry, config_registry=config_registry),
        ]

        results = deck.play(players=players, matches=matches, seed=seed)
        print(f"Completed matches: {len(results)}")
        print(f"Win rates: {results.win_rates}")


if __name__ == "__main__":
    main()
