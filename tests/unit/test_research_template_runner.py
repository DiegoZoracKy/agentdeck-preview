from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = ROOT / "research" / "_templates" / "scripts" / "run_experiment.py"


def _load_template_runner():
    spec = importlib.util.spec_from_file_location("agentdeck_template_runner", RUNNER_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_template_runner_accepts_legacy_model_ref_alias() -> None:
    runner = _load_template_runner()

    side = {"name": "Alice", "model_ref": "weak_model", "config_ref": "AO"}
    player_registry = {"weak_model": {"kind": "bot", "class": "AttackBot"}}
    config_registry = {"AO": {"controller": "ActionOnlyController"}}

    player = runner._build_player(
        side,
        player_registry=player_registry,
        config_registry=config_registry,
    )

    assert player.name == "Alice"
