"""Optional user-authored components using AgentDeck's extension contracts."""

from __future__ import annotations

import copy
import json
import re

from agentdeck import Controller, Player, Renderer, RenderResult, Spectator
from agentdeck.core.types import ParseResult
from agentdeck.monitors import Monitor


class JsonActionController(Controller):
    """Parse an explicit JSON action without guessing or repairing responses."""

    def __init__(self) -> None:
        self._allowed = None

    def bind_game(self, game) -> None:
        self._allowed = frozenset(game.allowed_actions)

    def get_format_instructions(self) -> str:
        actions = sorted(self._allowed or {"SAFE", "EXPRESS"})
        return (
            'Return only one JSON object with exactly one key: {"action":"<action>"}. Allowed: '
            + ", ".join(actions)
        )

    def parse(self, response: str) -> ParseResult:
        if self._allowed is None:
            raise RuntimeError("JsonActionController must be bound before parsing")
        try:

            def unique_pairs(pairs):
                value = {}
                for key, item in pairs:
                    if key in value:
                        raise ValueError("Duplicate JSON key")
                    value[key] = item
                return value

            value = json.loads(response, object_pairs_hook=unique_pairs)
            if not isinstance(value, dict) or set(value) != {"action"}:
                raise ValueError("Expected exactly the action field")
            if not isinstance(value["action"], str) or value["action"].upper() not in self._allowed:
                raise ValueError("Unknown action")
            action = value["action"].upper()
            return ParseResult(
                success=True,
                action=action,
                raw_response=response.strip(),
                metadata={
                    "validated": True,
                    "declared_action": action,
                    "resolution_method": "explicit_json_action",
                    "contract_satisfied": True,
                },
            )
        except (ValueError, TypeError) as exc:
            return ParseResult(
                success=False,
                action=None,
                raw_response=response.strip(),
                error=str(exc),
                metadata={"contract_satisfied": False, "resolution_method": "unresolved"},
            )

    def describe(self) -> dict:
        return {"name": "JsonActionController", "version": "1.0.0", "format": "json"}


class JsonViewRenderer(Renderer):
    def render(self, game_view: dict, player: str, *, turn_context=None) -> RenderResult:
        return RenderResult(
            text=json.dumps(game_view, ensure_ascii=False, sort_keys=True),
            metadata={"format": "json", "version": 1},
        )


class CalibrationPlayer(Player):
    """A provider-free response source that sees only the rendered prompt."""

    def __init__(self, name: str, *, policy: str = "optimal", **kwargs) -> None:
        super().__init__(name=name, **kwargs)
        if policy not in {"optimal", "greedy", "conservative", "invalid"}:
            raise ValueError("Unknown calibration policy")
        self.policy = policy

    def get_response(self, prompt: str) -> str:
        if "Reply with exactly 'OK'" in prompt:
            return "OK"
        if "REFLECT_ON_DELIVERIES" in prompt:
            return "I followed the declared calibration policy."
        if self.policy == "invalid":
            return "I think SAFE sounds sensible but I did not declare an action."
        if self.policy == "greedy":
            action = "EXPRESS"
        elif self.policy == "conservative":
            action = "SAFE"
        else:
            index = int(re.search(r'"?delivery[ _]index"?\s*:\s*(\d+)', prompt, re.I).group(1))
            encoded = re.search(r'"?express[ _]rewards"?\s*:\s*(\[[^\]]+\])', prompt, re.I)
            if encoded:
                rewards = json.loads(encoded.group(1))
            else:
                block = re.search(r"Express Rewards:\s*\n((?:\s*-\s*\d+\n)+)", prompt, re.I).group(
                    1
                )
                rewards = [int(v) for v in re.findall(r"-\s*(\d+)", block)]
            action = "EXPRESS" if rewards[index] == max(rewards) else "SAFE"
        if isinstance(self.controller, JsonActionController):
            return json.dumps({"action": action})
        if "REASONING:" in self.controller.get_format_instructions():
            return f"REASONING: Follow the calibrated policy over public state.\nACTION: {action}"
        return f"ACTION: {action}"

    def describe(self) -> dict:
        return {**super().describe(), "calibration_policy": self.policy}


class DecisionTrail(Spectator):
    """Observe exact gameplay facts; never decide actions or Research meaning."""

    def __init__(self) -> None:
        super().__init__()
        self.rows = []

    def on_gameplay(self, event) -> None:
        self.rows.append(
            copy.deepcopy(
                {
                    "player": event.data["player"],
                    "action": event.data["action"],
                    "state_before": event.data["state_before"],
                    "state_after": event.data["state_after"],
                    "interaction": event.data.get("interaction"),
                }
            )
        )

    def describe(self) -> dict:
        return {"name": "DecisionTrail", "version": "1.0.0"}


class ProgressProbe(Monitor):
    def __init__(self) -> None:
        super().__init__()
        self.turns = []

    def on_console_worker_turn(self, event) -> None:
        self.turns.append(copy.deepcopy(dict(event.data)))

    def describe(self) -> dict:
        return {"name": "ProgressProbe", "version": "1.0.0"}
