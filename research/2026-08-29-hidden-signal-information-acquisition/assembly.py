"""No-provider Assembly for the Hidden Signal acceptance Study."""

from __future__ import annotations

from typing import Any, Dict

from agentdeck import (
    ActionOnlyController,
    AgentDeckConfig,
    Assembly,
    AssemblyRun,
    ConclusionPolicy,
    HiddenSignalGame,
    PlayerFactory,
    TextRenderer,
)
from agentdeck.core.base.player import Player


class HiddenSignalCalibrationBot(Player):
    """Inspect concealed signals and commit directly to visible signals."""

    def __init__(self, name: str, **config: Any) -> None:
        super().__init__(
            name=name,
            controller=ActionOnlyController(),
            renderer=TextRenderer(),
            conclusion_template=None,
            model="hidden-signal-calibration-policy",
            **config,
        )

    def get_response(self, prompt: str) -> str:
        if getattr(self, "_active_phase", None) == "handshake":
            return "OK"
        signal = self._signal_from_prompt(prompt)
        action = "INSPECT" if signal == "HIDDEN" else f"CHOOSE_{signal}"
        return f"ACTION: {action}"

    @staticmethod
    def _signal_from_prompt(prompt: str) -> str:
        for line in prompt.splitlines():
            if line.startswith("Signal: "):
                signal = line.split(":", 1)[1].strip().upper()
                if signal in {"HIDDEN", "RED", "BLUE"}:
                    return signal
        raise ValueError("HiddenSignalCalibrationBot could not resolve the visible signal")

    def get_summary(self) -> Dict[str, Any]:
        summary = super().get_summary()
        summary["type"] = self.__class__.__name__
        return summary


def create_assembly() -> Assembly:
    seed = 20260829
    session = AgentDeckConfig(
        seed=seed,
        max_turns=3,
        log_level=None,
        log_file_levels=[],
        concurrency=1,
        conclusion=ConclusionPolicy(enabled=False),
    )
    return Assembly(
        runs=(
            _run("hidden_signal", "hidden", seed, session),
            _run("visible_signal", "visible", seed, session),
        )
    )


def _run(
    name: str,
    visibility: str,
    seed: int,
    session: AgentDeckConfig,
) -> AssemblyRun:
    return AssemblyRun(
        name=name,
        game=HiddenSignalGame(signal_visibility=visibility),
        players=(PlayerFactory(HiddenSignalCalibrationBot, {"name": "SignalPolicy"}),),
        matches=20,
        seed=seed,
        session=session,
    )
