#!/usr/bin/env python3
"""Run matrix cells for the Agentic Edge study package."""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path
from typing import Any, Dict, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SRC_ROOT = REPO_ROOT / "src"
for import_root in (str(SRC_ROOT), str(REPO_ROOT)):
    if import_root not in sys.path:
        sys.path.insert(0, import_root)

from agentdeck import (  # noqa: E402
    AgentDeck,
    AgentDeckConfig,
    ConclusionPolicy,
    FixedDamageGame,
    VariableDamageGame,
)
from agentdeck.controllers import ActionOnlyController, ReasoningController  # noqa: E402
from agentdeck.games.examples.fixed_damage import AttackBot, PotionAt80Bot  # noqa: E402
from agentdeck.players import ClaudePlayer, GPTPlayer, GeminiPlayer  # noqa: E402


EXPERIMENT_DIR = Path(__file__).resolve().parents[1]
MATRIX_PATH = EXPERIMENT_DIR / "matrix.yaml"
MANIFEST_PATH = EXPERIMENT_DIR / "manifest.yaml"


def _load_yaml(path: Path) -> Dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _read_template(path_value: str) -> str:
    path = EXPERIMENT_DIR / path_value
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def _controller_from_name(name: str):
    if name == "ActionOnlyController":
        return ActionOnlyController
    if name == "ReasoningController":
        return ReasoningController
    raise ValueError(f"Unsupported controller in matrix: {name}")


def _bot_from_class(name: str):
    if name == "AttackBot":
        return AttackBot
    if name == "PotionAt80Bot":
        return PotionAt80Bot
    raise ValueError(f"Unsupported bot class in matrix: {name}")


def _llm_from_provider(provider: str):
    if provider == "openai":
        return GPTPlayer
    if provider == "anthropic":
        return ClaudePlayer
    if provider == "google":
        return GeminiPlayer
    raise ValueError(f"Unsupported provider in matrix: {provider}")


def _template_kwargs(prompt_builder: Dict[str, Any]) -> Dict[str, str]:
    kwargs: Dict[str, str] = {}
    if prompt_builder.get("handshake_template_path"):
        kwargs["handshake_template"] = _read_template(prompt_builder["handshake_template_path"])
    elif prompt_builder.get("handshake_template") is not None:
        kwargs["handshake_template"] = prompt_builder["handshake_template"]

    if prompt_builder.get("turn_template_path"):
        kwargs["turn_template"] = _read_template(prompt_builder["turn_template_path"])
    elif prompt_builder.get("turn_template") is not None:
        kwargs["turn_template"] = prompt_builder["turn_template"]

    if prompt_builder.get("conclusion_template_path"):
        kwargs["conclusion_template"] = _read_template(prompt_builder["conclusion_template_path"])
    elif "conclusion_template" in prompt_builder:
        kwargs["conclusion_template"] = prompt_builder["conclusion_template"]

    return kwargs


def _build_player(
    side: Dict[str, Any],
    *,
    player_registry: Dict[str, Dict[str, Any]],
    config_registry: Dict[str, Dict[str, Any]],
):
    player_ref = side.get("player_ref", side.get("model_ref"))
    if player_ref is None:
        raise KeyError("Cell side must define player_ref (legacy alias: model_ref).")

    player_spec = player_registry[player_ref]
    config_spec = config_registry[side["config_ref"]]
    controller_cls = _controller_from_name(config_spec["controller"])
    prompt_builder = config_spec.get("prompt_builder", {})

    common_kwargs = {
        "name": side["name"],
        "controller": controller_cls(),
        **_template_kwargs(prompt_builder),
    }

    kind = player_spec["kind"]
    if kind == "bot":
        return _bot_from_class(player_spec["class"])(**common_kwargs)

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


def _filtered_config(game_cls, config: Dict[str, Any]) -> Dict[str, Any]:
    signature = inspect.signature(game_cls.__init__)
    allowed = {name for name in signature.parameters if name != "self"}
    return {key: value for key, value in config.items() if key in allowed}


def _build_game(cell: Dict[str, Any], manifest: Dict[str, Any]):
    manifest_game = manifest.get("game") or {}
    cell_game = cell.get("game") or {}
    game_name = cell_game.get("name") or manifest_game.get("name")
    game_config = dict(manifest_game.get("config") or {})
    game_config.update(cell_game.get("config") or {})

    if game_name == "FixedDamageGame":
        return FixedDamageGame(**_filtered_config(FixedDamageGame, game_config))
    if game_name == "VariableDamageGame":
        return VariableDamageGame(**_filtered_config(VariableDamageGame, game_config))

    raise ValueError(
        f"Unsupported game for this runner: {game_name}. "
        "Customize _build_game() if the matrix adds another game."
    )


def _iter_selected_cells(
    matrix: Dict[str, Any], *, phase: str | None, cell_ids: set[str] | None
) -> Iterable[Dict[str, Any]]:
    phase_to_cells: Dict[str, set[str]] = {}
    preflight = matrix.get("execution_plan", {}).get("preflight") or {}
    if preflight.get("phase_id"):
        phase_to_cells[preflight["phase_id"]] = set(preflight.get("cell_ids", []))
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
        matches = cell.get("matches", "?")
        game_name = (cell.get("game") or {}).get("name", "?")
        print(
            f"{cell['id']} [{cell.get('phase', '?')}] "
            f"{game_name} matches={matches} - {cell.get('question', '')}"
        )


def _resolve_matches(cell: Dict[str, Any], matrix: Dict[str, Any], override: int | None) -> int:
    if override is not None:
        return override
    if cell.get("matches") is not None:
        return int(cell["matches"])

    sampling = matrix.get("sampling_policy") or {}
    phase = str(cell.get("phase") or "")
    if phase == "P0" and sampling.get("preflight_matches_per_cell") is not None:
        return int(sampling["preflight_matches_per_cell"])
    if sampling.get("pilot_matches_per_cell") is not None:
        return int(sampling["pilot_matches_per_cell"])

    raise KeyError(
        f"Cell {cell.get('id', '<unknown>')} must define matches or the matrix must "
        "define a phase-appropriate default."
    )


def _validate_cell_runtime(cell: Dict[str, Any], matches: int, config_registry) -> None:
    if matches < 1:
        raise ValueError(f"Cell {cell['id']} has invalid matches={matches}")

    player_a_config = config_registry[cell["player_a"]["config_ref"]]
    player_b_config = config_registry[cell["player_b"]["config_ref"]]

    for key in ("pairing_policy", "first_player_policy"):
        if player_a_config[key] != player_b_config[key]:
            raise ValueError(
                f"Cell {cell['id']} has mismatched {key}: "
                f"{player_a_config[key]} != {player_b_config[key]}"
            )

    if player_a_config["pairing_policy"] == "paired_side_swap" and matches % 2 != 0:
        raise ValueError(
            f"Cell {cell['id']} uses paired_side_swap and requires an even match count; "
            f"got matches={matches}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", help="Run all cells in one phase (e.g. P0 or P1)")
    parser.add_argument("--cell", action="append", dest="cells", help="Run one or more cell IDs")
    parser.add_argument("--list-cells", action="store_true", help="List available cells and exit")
    parser.add_argument("--matches", type=int, help="Override matches for every selected cell")
    parser.add_argument("--concurrency", type=int, help="Override session concurrency")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan without running")
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

    player_registry = matrix.get("player_registry") or matrix.get("model_registry")
    if not isinstance(player_registry, dict):
        raise KeyError("matrix.yaml must define player_registry (legacy alias: model_registry).")

    config_registry = matrix["config_registry"]
    manifest_run = manifest["run"]
    base_seed = int(manifest_run["seed_base"])
    default_concurrency = args.concurrency or manifest_run.get("concurrency", 1)
    max_turns = manifest_run.get("max_turns", 40)

    for cell in selected:
        matches = _resolve_matches(cell, matrix, args.matches)
        _validate_cell_runtime(cell, matches, config_registry)

        player_a_config = config_registry[cell["player_a"]["config_ref"]]
        pairing_policy = player_a_config["pairing_policy"]
        first_player_policy = player_a_config["first_player_policy"]
        conclusion_cfg = player_a_config.get("conclusion", {"enabled": False})
        run_dir = EXPERIMENT_DIR / "agentdeck_runs" / cell["id"]
        seed = base_seed + int(cell.get("seed_offset", 0))
        game_name = (cell.get("game") or {}).get("name", manifest.get("game", {}).get("name"))

        print("=" * 72)
        print(f"Cell: {cell['id']}")
        print(f"Phase: {cell.get('phase', '?')} | Game: {game_name}")
        print(f"Question: {cell.get('question', '')}")
        print(f"Run dir: {run_dir}")
        print(f"Matches: {matches} ({matches // 2} side-swap pair(s) if paired)")
        print(f"Seed: {seed}")
        print(f"Pairing: {pairing_policy} | First player: {first_player_policy}")
        print(
            "Players: "
            f"{cell['player_a']['name']} ({cell['player_a']['config_ref']}) vs "
            f"{cell['player_b']['name']} ({cell['player_b']['config_ref']})"
        )

        if args.dry_run:
            continue

        players = [
            _build_player(
                cell["player_a"],
                player_registry=player_registry,
                config_registry=config_registry,
            ),
            _build_player(
                cell["player_b"],
                player_registry=player_registry,
                config_registry=config_registry,
            ),
        ]

        with AgentDeck(
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
        ) as deck:
            results = deck.play(players=players, matches=matches, seed=seed)
            print(f"Completed matches: {len(results)}")
            print(f"Win rates: {results.win_rates}")


if __name__ == "__main__":
    main()
