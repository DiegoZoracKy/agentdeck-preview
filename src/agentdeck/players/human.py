"""Synchronous local human-controlled Player."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional

from ..core.base.controller import Controller
from ..core.base.player import Player
from ..core.base.renderer import Renderer
from ..core.prompt_builder import _DEFAULT_TEMPLATE

ResponseReader = Callable[[str], str]


class HumanPlayer(Player):
    """Obtain exact raw responses from a local human.

    The terminal is the default adapter. An injected synchronous reader is
    useful for tests and local integrations, but every response still follows
    the standard Player -> Controller -> ActionResult -> Record lifecycle.
    """

    def __init__(
        self,
        name: str,
        *,
        controller: Controller,
        renderer: Optional[Renderer] = None,
        handshake_template: Optional[str | Path] = None,
        turn_template: Optional[str | Path] = None,
        conclusion_template: Optional[str | Path] | object = _DEFAULT_TEMPLATE,
        response_reader: Optional[ResponseReader] = None,
    ) -> None:
        if response_reader is not None and not callable(response_reader):
            raise TypeError("response_reader must be callable or None")

        super().__init__(
            name,
            controller=controller,
            renderer=renderer,
            handshake_template=handshake_template,
            turn_template=turn_template,
            conclusion_template=conclusion_template,
        )
        self._response_reader = response_reader

    @property
    def interaction_mode(self) -> str:
        """Return the declared local interaction mode."""

        return "terminal" if self._response_reader is None else "callable"

    def get_response(self, prompt: str) -> str:
        """Present one prompt and return the human response without alteration."""

        if self._response_reader is None:
            print(prompt)
            response = input("> ")
        else:
            response = self._response_reader(prompt)

        if not isinstance(response, str):
            raise TypeError("HumanPlayer response_reader must return a string")
        return response

    def clone(self) -> "HumanPlayer":
        """Reject parallel cloning because one local human interaction is serialized."""

        raise RuntimeError("HumanPlayer requires serialized execution; use concurrency=1")

    def describe(self) -> dict[str, Any]:
        """Return provider-free Player configuration and interaction provenance."""

        description = super().describe()
        description["interaction"] = {
            "authority": "human",
            "mode": self.interaction_mode,
        }
        return description

    def get_summary(self) -> dict[str, Any]:
        """Return a concise provider-free summary."""

        summary = super().get_summary()
        summary["interaction"] = {
            "authority": "human",
            "mode": self.interaction_mode,
        }
        return summary


__all__ = ["HumanPlayer", "ResponseReader"]
