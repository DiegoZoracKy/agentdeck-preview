"""Deterministic behavioral profile for the external Number Duel fixture."""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional

from agentdeck import BehavioralScorer


def _phase_index(event: Mapping[str, Any]) -> int:
    value = (event.get("data") or {}).get("phase_index")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("Gameplay event requires a non-negative phase_index")
    return value


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
        turns = [
            {
                "action": ((event.get("data") or {}).get("action") or {}).get("value"),
                "match_index": match_index,
                "phase_index": _phase_index(event),
            }
            for match_index, payload in enumerate(payloads)
            for event in payload.get("events", [])
            if event.get("type") == "gameplay"
        ]
        actions = [turn["action"] for turn in turns]
        gain_count = sum(action == "GAIN" for action in actions)
        definition = "Share of recorded gameplay turns whose canonical action was GAIN."
        eligible_events = [
            {"match_index": turn["match_index"], "phase_index": turn["phase_index"]}
            for turn in turns
        ]
        numerator_events = [
            {"match_index": turn["match_index"], "phase_index": turn["phase_index"]}
            for turn in turns
            if turn["action"] == "GAIN"
        ]
        return {
            "schema_version": 2,
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
            "per_player": {},
            "state_metrics": {},
            "evidence": {
                "aggregate_metrics": {},
                "per_player": {},
                "state_metrics": {},
            },
            "measurement_provenance": {
                "schema_version": "1.0",
                "aggregate_metrics": {
                    "gain_action_rate": {
                        "definition": definition,
                        "numerator": gain_count,
                        "denominator": len(actions),
                        "eligible_events": eligible_events,
                        "numerator_events": numerator_events,
                    }
                },
                "per_player": {},
            },
            "quality_flags": {"complete": bool(actions), "unsupported_metrics": []},
        }
