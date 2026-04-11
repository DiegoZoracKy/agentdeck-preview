"""Package-local behavioral scorer template.

Delete this file if the package does not need a custom behavioral profile.
If you keep it, customize the scorer below before running:

    agentdeck-research-score --experiment-dir research/YYYY-MM-DD-your-experiment
"""

from __future__ import annotations

from typing import Any, Iterable, List, Mapping, Optional

from agentdeck.research.behavioral import BehavioralScorer


_NOT_CONFIGURED = (
    "Customize scripts/behavioral_scorer.py for this package, or delete the file "
    "if the experiment does not need a package-local behavioral profile."
)


class PackageBehavioralScorer(BehavioralScorer):
    """Replace this stub with a scorer for your package-owned game."""

    game_id = "replace_me"
    profile_id = "replace_me_behavioral"
    profile_version = "0.1.0"

    def supports(self, *, match_payloads: Iterable[Mapping[str, Any]]) -> bool:
        raise ValueError(_NOT_CONFIGURED)

    def score(
        self,
        *,
        players: List[Mapping[str, Any]],
        match_payloads: Iterable[Mapping[str, Any]],
        config: Optional[Mapping[str, Any]] = None,
    ) -> Mapping[str, Any]:
        raise ValueError(_NOT_CONFIGURED)


# agentdeck-research-score auto-discovers this module-global scorer instance.
SCORER = PackageBehavioralScorer()
