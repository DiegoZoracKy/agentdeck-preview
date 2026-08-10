"""
VariableDamageGame: stochastic sibling of FixedDamageGame for AgentDeck.

Simple turn-based combat game demonstrating:
- information_level support ("full" vs "partial")
- JSON-serializable state
- deterministic RNG usage
- explicit random damage contract with replay-friendly seed flow
"""

from typing import Any, Dict, List

from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.types import ActionResult, GameStatus, RandomGenerator


class VariableDamageGame(TurnBasedGame):
    """
    Simple stochastic turn-based combat game for research and tutorials.

    Rules:
        - Each player starts with max_health HP and starting_potions potions
        - ATTACK deals uniformly sampled integer damage in [min_attack_damage, max_attack_damage]
        - POTION restores fixed HP
        - First player to reduce opponent to 0 HP wins
        - information_level controls opponent visibility

    State structure intentionally matches FixedDamageGame:
        {
            "health": {player: int},
            "potions": {player: int},
            "last_action": {player: str | None},
            "turn": int
        }
    """

    GAME_FAMILY_ID = "agentdeck.game.variable-damage"
    GAME_VERSION = "0.1.0"
    GAME_IMPLEMENTATION_MODULES = ("agentdeck.games.examples.variable_damage.game",)
    SUPPORTED_INFORMATION_LEVELS = {"full", "partial"}

    def __init__(
        self,
        max_health: int = 100,
        min_attack_damage: int = 15,
        max_attack_damage: int = 25,
        potion_heal: int = 30,
        starting_potions: int = 3,
        information_level: str = "full",
    ):
        super().__init__()
        if information_level not in self.SUPPORTED_INFORMATION_LEVELS:
            raise ValueError("information_level must be 'full' or 'partial'")
        if min_attack_damage <= 0 or max_attack_damage <= 0:
            raise ValueError("attack damage bounds must be positive integers")
        if min_attack_damage > max_attack_damage:
            raise ValueError("min_attack_damage must be <= max_attack_damage")
        self.max_health = max_health
        self.min_attack_damage = min_attack_damage
        self.max_attack_damage = max_attack_damage
        self.potion_heal = potion_heal
        self.starting_potions = starting_potions
        self.information_level = information_level

    @property
    def instructions(self) -> str:
        return f"""
Variable Damage Combat Game

Starting Conditions:
- Each player starts with {self.max_health} HP
- Each player has {self.starting_potions} potion{"s" if self.starting_potions != 1 else ""}

Actions:
- ATTACK: Deals random damage from {self.min_attack_damage} to {self.max_attack_damage}
- POTION: Restores {self.potion_heal} HP (max {self.max_health})

Win Condition:
- First player to reduce opponent to 0 HP wins
- If both reach 0 HP simultaneously, the match is a draw

Information Level: {self.information_level}
- "full": Players see all stats (opponent HP/potions)
- "partial": Players see only their own HP/potions, but last actions remain visible
        """.strip()

    @property
    def allowed_actions(self) -> List[str]:
        return ["ATTACK", "POTION"]

    @property
    def default_handshake_template(self) -> str:
        return (
            "{game_instructions}\n\n"
            "When gameplay begins, use this response format:\n"
            "{controller_format}\n\n"
            "{handshake_controller_format}"
        )

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        if len(players) != 2:
            raise ValueError("VariableDamageGame requires exactly 2 players")
        return {
            "health": {p: self.max_health for p in players},
            "potions": {p: self.starting_potions for p in players},
            "last_action": {p: None for p in players},
            "turn": 1,
        }

    def update(
        self, game_state: Dict[str, Any], player: str, action: ActionResult, *, rng: RandomGenerator
    ) -> Dict[str, Any]:
        state = dict(game_state)

        action_str = action.action.upper()
        if action_str not in self.allowed_actions:
            raise ValueError(
                f"Invalid action '{action_str}'. Allowed actions: {self.allowed_actions}"
            )

        state["last_action"][player] = action_str

        if action_str == "ATTACK":
            opponent = next((p for p in state["health"] if p != player), None)
            if opponent is None:
                raise ValueError("Cannot attack in single-player game")
            damage = rng.randint(self.min_attack_damage, self.max_attack_damage)
            state["health"][opponent] = max(0, state["health"][opponent] - damage)

        elif action_str == "POTION":
            if state["potions"][player] > 0:
                state["health"][player] = min(
                    state["health"][player] + self.potion_heal, self.max_health
                )
                state["potions"][player] -= 1

        state["turn"] += 1
        return state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        alive = [p for p, hp in game_state["health"].items() if hp > 0]

        if len(alive) == 1:
            return GameStatus(is_over=True, winner=alive[0])
        if len(alive) == 0:
            return GameStatus(is_over=True, winner=None)
        return GameStatus(is_over=False, winner=None)

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        view = {
            "health": {player: game_state["health"][player]},
            "potions": {player: game_state["potions"][player]},
            "last_action": game_state["last_action"],
            "turn": game_state["turn"],
        }

        if self.information_level == "full":
            opponents = [p for p in game_state["health"] if p != player]
            for opp in opponents:
                view["health"][opp] = game_state["health"][opp]
                view["potions"][opp] = game_state["potions"][opp]

        return view
