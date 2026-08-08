"""Deterministic behavioral profile for the external Number Duel fixture."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from agentdeck import BehavioralScorer


class NumberDuelBehavioralScorer(BehavioralScorer):
    """Measure how often participants choose GAIN in generated records."""

    game_id = "number_duel"
    profile_id = "number_duel_behavioral"
    profile_version = "0.1.0"

    def supports(self, *, match_payloads: Iterable[Mapping[str, Any]]) -> bool:
        payloads = list(match_payloads)
        return bool(payloads) and all(
            (payload.get("metadata") or {}).get("game") == "NumberDuelGame"
            or ((payload.get("metadata") or {}).get("game_config") or {}).get("name")
            == "NumberDuelGame"
            for payload in payloads
        )

    def score(
        self,
        *,
        players: List[Mapping[str, Any]],
        match_payloads: Iterable[Mapping[str, Any]],
        config: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        del players, config
        payloads = list(match_payloads)
        actions = [
            ((event.get("data") or {}).get("action") or {}).get("value")
            for payload in payloads
            for event in payload.get("events", [])
            if event.get("type") == "gameplay"
        ]
        gain_count = sum(action == "GAIN" for action in actions)
        return {
            "schema_version": 1,
            "game_id": self.game_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "coverage": {"matches_total": len(payloads), "turns_total": len(actions)},
            "aggregate_metrics": {
                "gain_action_rate": {
                    "value": gain_count / len(actions) if actions else None,
                    "gain_actions": gain_count,
                    "support_turns": len(actions),
                }
            },
            "quality_flags": {"complete": bool(actions), "unsupported_metrics": []},
        }
