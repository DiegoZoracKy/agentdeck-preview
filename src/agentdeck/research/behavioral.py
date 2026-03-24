"""Behavioral scorer interface and scorer resolution helpers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Iterable, List, Mapping, Optional


CANONICAL_JSON_KWARGS = {
    "sort_keys": True,
    "separators": (",", ":"),
    "ensure_ascii": True,
    "allow_nan": False,
}


class BehavioralScorer(ABC):
    """Base contract for game-specific behavioral scorers."""

    game_id: str = ""
    profile_id: str = ""
    profile_version: str = ""

    @abstractmethod
    def supports(self, *, match_payloads: Iterable[Mapping[str, Any]]) -> bool:
        """Return whether this scorer can evaluate the supplied match payloads."""

    @abstractmethod
    def score(
        self,
        *,
        players: List[Mapping[str, Any]],
        match_payloads: Iterable[Mapping[str, Any]],
        config: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Compute a behavioral profile from recorder payloads."""

    def canonical_json(self, payload: Mapping[str, Any]) -> str:
        """Serialize scorer output using the canonical contract settings."""
        return json.dumps(payload, **CANONICAL_JSON_KWARGS)


def _extract_game_name(match_payload: Mapping[str, Any]) -> str | None:
    direct = match_payload.get("game")
    if isinstance(direct, str) and direct:
        return direct

    metadata = match_payload.get("metadata") or {}
    meta_game = metadata.get("game")
    if isinstance(meta_game, str) and meta_game:
        return meta_game

    match_meta = metadata.get("match") or {}
    match_game = match_meta.get("game")
    if isinstance(match_game, Mapping):
        name = match_game.get("name")
        if name:
            return str(name)
    elif isinstance(match_game, str) and match_game:
        return match_game

    game_config = metadata.get("game_config") or {}
    name = game_config.get("name")
    if name:
        return str(name)
    return None


def get_behavioral_scorer(
    *,
    match_payloads: Iterable[Mapping[str, Any]],
    profile_id: str | None = "auto",
) -> BehavioralScorer | None:
    normalized_profile = (profile_id or "auto").strip().lower()
    if normalized_profile == "none":
        return None

    from agentdeck.games.examples.fixed_damage.behavioral import (
        FixedDamageBehavioralScorer,
    )
    from agentdeck.games.examples.variable_damage.behavioral import (
        VariableDamageBehavioralScorer,
    )

    scorers = [
        FixedDamageBehavioralScorer(),
        VariableDamageBehavioralScorer(),
    ]
    for scorer in scorers:
        if normalized_profile == scorer.profile_id.lower():
            return scorer
    if normalized_profile == "auto":
        for scorer in scorers:
            if scorer.supports(match_payloads=match_payloads):
                return scorer
    return None


def compute_behavioral_profile(
    *,
    players: List[Mapping[str, Any]],
    match_payloads: Iterable[Mapping[str, Any]],
    profile_id: str | None = "auto",
    config: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any] | None:
    match_payload_list = list(match_payloads)
    scorer = get_behavioral_scorer(
        match_payloads=match_payload_list, profile_id=profile_id
    )
    if scorer is None:
        return None
    return scorer.score(
        players=players,
        match_payloads=match_payload_list,
        config=config,
    )


__all__ = [
    "BehavioralScorer",
    "CANONICAL_JSON_KWARGS",
    "compute_behavioral_profile",
    "get_behavioral_scorer",
]
