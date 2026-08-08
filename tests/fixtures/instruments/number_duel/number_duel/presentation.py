"""Visible-state projection for the external Number Duel fixture."""

from __future__ import annotations

from typing import Any, Dict, Mapping


def visible_state(
    state: Mapping[str, Any], player: str, game_config: Mapping[str, Any]
) -> Dict[str, Any]:
    del game_config
    if player not in state["scores"]:
        raise ValueError("unknown Player")
    return {
        "scores": dict(state["scores"]),
        "turn": state["turn"],
        "seed": state["seed"],
    }
