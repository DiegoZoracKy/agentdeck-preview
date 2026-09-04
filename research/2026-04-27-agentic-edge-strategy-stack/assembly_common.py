"""Prepared-Assembly adapter for the frozen Agentic Edge matrix."""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any, Mapping

import yaml

from agentdeck import (
    ActionOnlyController,
    AgentDeckConfig,
    Assembly,
    AssemblyRun,
    ConclusionPolicy,
    FixedDamageGame,
    GPTPlayer,
    GeminiPlayer,
    PlayerFactory,
    ReasoningController,
    TextRenderer,
    VariableDamageGame,
)
from agentdeck.games.examples.fixed_damage import AttackBot, PotionAt80Bot


PACKAGE_ROOT = Path(__file__).resolve().parent
MATRIX = yaml.safe_load((PACKAGE_ROOT / "matrix.yaml").read_text(encoding="utf-8"))
MANIFEST = yaml.safe_load((PACKAGE_ROOT / "manifest.yaml").read_text(encoding="utf-8"))


def create_phase_assembly(phase_id: str) -> Assembly:
    """Materialize exactly the matrix Cells authored for one phase."""

    runs = tuple(_build_run(cell) for cell in MATRIX["cells"] if cell["phase"] == phase_id)
    if not runs:
        raise ValueError(f"The Agentic Edge matrix has no Cells for phase {phase_id!r}")
    return Assembly(runs=runs)


def _build_run(cell: Mapping[str, Any]) -> AssemblyRun:
    matches = int(cell["matches"])
    player_a = cell["player_a"]
    config = MATRIX["config_registry"][player_a["config_ref"]]
    _validate_fairness(cell, matches)
    seed = int(MANIFEST["run"]["seed_base"]) + int(cell.get("seed_offset", 0))
    conclusion = config.get("conclusion") or {"enabled": False}
    concurrency = _cell_concurrency(cell)
    session = AgentDeckConfig(
        seed=seed,
        max_turns=int(MANIFEST["run"].get("max_turns", 40)),
        concurrency=concurrency,
        pairing_policy=str(config["pairing_policy"]),
        first_player_policy=str(config["first_player_policy"]),
        conclusion=ConclusionPolicy(**conclusion),
    )
    return AssemblyRun(
        name=str(cell["id"]),
        game=_build_game(cell),
        players=(_build_player(player_a), _build_player(cell["player_b"])),
        matches=matches,
        seed=seed,
        session=session,
    )


def _build_player(side: Mapping[str, Any]) -> PlayerFactory:
    player_spec = MATRIX["player_registry"][side["player_ref"]]
    config = MATRIX["config_registry"][side["config_ref"]]
    controller = _controller(str(config["controller"]))
    kwargs: dict[str, Any] = {
        "name": str(side["name"]),
        "controller": controller,
        "renderer": TextRenderer(),
        **_template_kwargs(config.get("prompt_builder") or {}),
    }
    kind = str(player_spec["kind"])
    if kind == "bot":
        bot_types = {"AttackBot": AttackBot, "PotionAt80Bot": PotionAt80Bot}
        return PlayerFactory(bot_types[str(player_spec["class"])], kwargs)
    if kind != "llm":
        raise ValueError(f"Unsupported Agentic Edge Player kind: {kind}")
    player_types = {"google": GeminiPlayer, "openai": GPTPlayer}
    kwargs["model"] = str(player_spec["model"])
    for key in ("temperature", "max_tokens", "max_retries", "retry_delay"):
        if player_spec.get(key) is not None:
            kwargs[key] = player_spec[key]
    if player_spec.get("generation_config") is not None:
        kwargs["generation_config"] = dict(player_spec["generation_config"])
    return PlayerFactory(player_types[str(player_spec["provider"])], kwargs)


def _build_game(cell: Mapping[str, Any]):
    base = dict(MANIFEST["game"]["config"])
    base.update((cell.get("game") or {}).get("config") or {})
    game_name = str((cell.get("game") or {}).get("name"))
    game_type = {
        "FixedDamageGame": FixedDamageGame,
        "VariableDamageGame": VariableDamageGame,
    }[game_name]
    parameters = set(inspect.signature(game_type.__init__).parameters) - {"self"}
    return game_type(**{key: value for key, value in base.items() if key in parameters})


def _controller(name: str):
    return {
        "ActionOnlyController": ActionOnlyController,
        "ReasoningController": ReasoningController,
    }[name]()


def _template_kwargs(config: Mapping[str, Any]) -> dict[str, str | None]:
    result: dict[str, str | None] = {"conclusion_template": None}
    for key, output_key in (
        ("handshake_template_path", "handshake_template"),
        ("turn_template_path", "turn_template"),
        ("conclusion_template_path", "conclusion_template"),
    ):
        relative = config.get(key)
        if relative:
            result[output_key] = (PACKAGE_ROOT / str(relative)).read_text(encoding="utf-8")
    return result


def _validate_fairness(cell: Mapping[str, Any], matches: int) -> None:
    left = MATRIX["config_registry"][cell["player_a"]["config_ref"]]
    right = MATRIX["config_registry"][cell["player_b"]["config_ref"]]
    for key in ("pairing_policy", "first_player_policy"):
        if left[key] != right[key]:
            raise ValueError(f"Cell {cell['id']} has mismatched {key}")
    if left["pairing_policy"] == "paired_side_swap" and matches % 2:
        raise ValueError(f"Cell {cell['id']} requires an even fixed match count")


def _cell_concurrency(cell: Mapping[str, Any]) -> int:
    default = int(MANIFEST["run"].get("concurrency", 1))
    for phase in MATRIX["execution_plan"].get("phases", []):
        if phase["phase_id"] != cell["phase"]:
            continue
        policy = phase.get("concurrency_policy") or {}
        return int((policy.get("overrides") or {}).get(cell["id"], policy.get("default", default)))
    return default

