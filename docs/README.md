# AgentDeck Documentation Map

This repository keeps documentation lean and code-adjacent. Start here to find the right artifact.

- **Overview & Quickstart**: `README.md` (project purpose, installation, first experiment)
- **Walkthroughs**: `docs/first_game_walkthrough.md` (author a game, record, and replay without API keys)
- **Specifications**: `specs/SPEC.md` (navigation hub) and component specs under `specs/`
- **Roadmap & Contribution**: `ROADMAP.md` (current priorities) and `CONTRIBUTING.md` (spec-first workflow)
- **Research Assets**: `research/` (benchmarks, recordings) kept separate from docs for clarity

Planned structure (post-release): `overview → quickstart → guides → reference`, keeping specs as the authoritative contracts.

## Quick example: adopting lifecycle hooks (SPEC-GAME v0.7.0)

Hooks are opt-in and default to no-ops. This minimal game shows how to use them to capture handshake metadata, enrich forfeits, and store a winner-only conclusion.

```python
from agentdeck import AgentDeck
from agentdeck.core.base.game import GameStatus
from agentdeck.core.mechanics.turn_based import TurnBasedGame


class SupportLikeGame(TurnBasedGame):
    @property
    def instructions(self):
        return "Respond in JSON."

    @property
    def allowed_actions(self):
        return ["END"]

    @property
    def default_handshake_template(self):
        return "Reply OK when ready."

    def setup(self, players, seed):
        return {"winner": None, "persona": None, "conclusion": None, "_turn_count": 1}

    def get_view(self, state, player):
        return {"turn": state["_turn_count"]}

    def update(self, state, player, action, *, rng):
        if action.action == "END":
            state["winner"] = player
        state["_turn_count"] += 1
        return state

    def status(self, state):
        return GameStatus(is_over=state["winner"] is not None, winner=state["winner"])

    # Hooks (all optional; safe defaults if omitted)
    def on_handshake_complete(self, state, player, handshake_result):
        state["persona"] = handshake_result.metadata.get("persona")
        return state

    def on_match_forfeited(self, state, player_name, error, policy):
        state["resolution_status"] = "invalid_response"
        state["failed_player"] = player_name
        return state

    def requires_conclusion(self, state):
        return state["winner"]

    def get_conclusion_prompt(self, player, state):
        return 'Respond with JSON: {"summary": "..."}'

    def parse_conclusion(self, player, response):
        import json

        return json.loads(response) if response else {}

    def on_conclusion_received(self, state, player, conclusion):
        state["conclusion"] = conclusion
        return state


deck = AgentDeck(game=SupportLikeGame())
results = deck.play(players=[...], matches=1)
print(results[0].final_state["conclusion"])
```

Remove the hook methods and the game reverts to default behavior (no extra state, no additional LLM calls).
