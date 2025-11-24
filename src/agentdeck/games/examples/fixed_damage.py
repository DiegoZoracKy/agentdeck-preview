"""
FixedDamageGame: Reference implementation for AgentDeck v1.0.0.

Simple turn-based combat game demonstrating:
- information_level support ("full" vs "partial")
- JSON-serializable state
- Deterministic RNG usage
- Clear action handling with fail-fast

Per SPEC-GAME v0.4.0 §8 Example 2.
"""

from typing import Any, Dict, List

from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.types import ActionResult, GameStatus, RandomGenerator


class FixedDamageGame(TurnBasedGame):
    """
    Simple turn-based combat game for testing/tutorial.

    Rules:
        - Each player starts with max_health HP and starting_potions potions
        - Actions: ATTACK (deals fixed damage) or POTION (restores HP)
        - First player to reach 0 HP loses
        - information_level controls opponent visibility

    Configuration:
        - max_health: Starting HP for all players (default 100)
        - attack_damage: Damage dealt by ATTACK (default 20)
        - potion_heal: HP restored by POTION (default 30)
        - starting_potions: Number of potions each player starts with (default 3)
        - information_level: "full" (show all stats) or "partial" (hide opponent stats)

    Example usage:
        >>> game = FixedDamageGame(max_health=100, attack_damage=20,
        ...                        information_level="full")
        >>> state = game.setup(["Alice", "Bob"])
        >>> action = ActionResult(action="ATTACK", output="ATTACK", raw_response="I attack!")
        >>> new_state = game.update(state, "Alice", action, rng=rng)
        >>> status = game.status(new_state)
        >>> alice_view = game.get_view(new_state, "Alice")

    State structure:
        {
            "health": {player: int},       # HP for each player
            "potions": {player: int},      # Potion count for each player
            "last_action": {player: str},  # Last action taken by each player
            "turn": int                    # Turn counter
        }
    """

    def __init__(
        self,
        max_health: int = 100,
        attack_damage: int = 20,
        potion_heal: int = 30,
        starting_potions: int = 3,
        information_level: str = "full",
    ):
        """
        Initialize FixedDamageGame with configuration.

        Args:
            max_health: Starting HP for all players (default 100)
            attack_damage: Damage dealt by ATTACK (default 20)
            potion_heal: HP restored by POTION (default 30)
            starting_potions: Number of potions each player starts with (default 3)
            information_level: "full" (show all stats) or "partial" (hide opponent)

        Note: information_level per SPEC-GAME §5 IV1-IV5 is optional;
              perfect-information games can omit this parameter.
        """
        super().__init__()
        self.max_health = max_health
        self.attack_damage = attack_damage
        self.potion_heal = potion_heal
        self.starting_potions = starting_potions
        self.information_level = information_level  # IV1: Games MAY implement

    # ========================================================================
    # Required Properties
    # ========================================================================

    @property
    def instructions(self) -> str:
        """
        Reference-only description for docs/lobby UIs.

        Returns:
            Plain text description of game rules
        """
        return f"""
Fixed Damage Combat Game

Starting Conditions:
- Each player starts with {self.max_health} HP
- Each player has {self.starting_potions} potion{"s" if self.starting_potions != 1 else ""}

Actions:
- ATTACK: Deals {self.attack_damage} damage to opponent
- POTION: Restores {self.potion_heal} HP (max {self.max_health})

Win Condition:
- First player to reduce opponent to 0 HP wins
- If both reach 0 HP simultaneously, the match is a draw

Information Level: {self.information_level}
- "full": Players see all stats (opponent HP/potions)
- "partial": Players only see their own stats
        """.strip()

    @property
    def allowed_actions(self) -> List[str]:
        """
        Canonical list of valid actions.

        Returns:
            List of action strings accepted by update()
        """
        return ["ATTACK", "POTION"]

    @property
    def default_handshake_template(self) -> str:
        """
        Template for player handshake phase (HT1).

        Returns:
            Template string with placeholders for PromptBuilder
        """
        return "{game_instructions}\n\nRespond 'OK' when you're ready to begin the match."

    # ========================================================================
    # Required Methods
    # ========================================================================

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        """
        Build canonical game_state for match start (GS1, SPEC.md §5.5).

        Args:
            players: Ordered player roster from Console
            seed: Deterministic seed for reproducibility (per v1.0.0 contract)

        Returns:
            JSON-serializable dict with all required keys

        Example:
            >>> game = FixedDamageGame()
            >>> state = game.setup(["Alice", "Bob"], seed=42)
            >>> state["health"]
            {"Alice": 100, "Bob": 100}

        Note: FixedDamageGame is deterministic, so seed is not used during setup.
              More complex games might use seed to initialize starting positions.
        """
        return {
            "health": {p: self.max_health for p in players},
            "potions": {p: self.starting_potions for p in players},
            "last_action": {p: None for p in players},
            "turn": 1,
        }

    def update(
        self, game_state: Dict[str, Any], player: str, action: ActionResult, *, rng: RandomGenerator
    ) -> Dict[str, Any]:
        """
        Apply action to evolve game state (GS2, DT1).

        Args:
            game_state: Current canonical state
            player: Acting player name
            action: Parsed action from ActionController
            rng: Deterministic RNG fork (not used in FixedDamageGame)

        Returns:
            Updated state dict

        Raises:
            ValueError: If action is invalid (fail-fast per SPEC-GAME §4.50)

        Example:
            >>> state = game.setup(["Alice", "Bob"])
            >>> action = ActionResult(action="ATTACK", output="ATTACK",
            ...                       raw_response="I attack!")
            >>> new_state = game.update(state, "Alice", action, rng=rng)
            >>> new_state["health"]["Bob"]
            80  # 100 - 20
        """
        # Defensive copy for clarity (per design decision)
        state = dict(game_state)

        # Normalize action to uppercase
        action_str = action.action.upper()

        # Validate action (fail-fast)
        if action_str not in self.allowed_actions:
            raise ValueError(
                f"Invalid action '{action_str}'. " f"Allowed actions: {self.allowed_actions}"
            )

        # Record action
        state["last_action"][player] = action_str

        # Apply action logic
        if action_str == "ATTACK":
            # Find opponent (assumes 2-player game)
            opponent = next((p for p in state["health"] if p != player), None)
            if opponent is None:
                raise ValueError("Cannot attack in single-player game")

            state["health"][opponent] -= self.attack_damage

        elif action_str == "POTION":
            if state["potions"][player] > 0:
                # Restore HP, capped at max_health
                state["health"][player] = min(
                    state["health"][player] + self.potion_heal, self.max_health
                )
                state["potions"][player] -= 1
            # Silently no-op if no potions left (could also raise)

        # Increment turn counter
        state["turn"] += 1

        return state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        """
        Evaluate whether play continues and determine winner.

        Args:
            game_state: Latest canonical state

        Returns:
            GameStatus(is_over=bool, winner=Optional[str])

        Example:
            >>> state = {"health": {"Alice": 50, "Bob": 0}, ...}
            >>> status = game.status(state)
            >>> status.is_over
            True
            >>> status.winner
            'Alice'
        """
        # Find players still alive
        alive = [p for p, hp in game_state["health"].items() if hp > 0]

        if len(alive) == 1:
            # One winner
            return GameStatus(is_over=True, winner=alive[0])
        elif len(alive) == 0:
            # Draw (both died)
            return GameStatus(is_over=True, winner=None)
        else:
            # Game continues
            return GameStatus(is_over=False, winner=None)

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        """
        Produce filtered view for specific player (G15, OB3, IV2-IV3).

        Args:
            game_state: Canonical state (full truth)
            player: Requesting player identity

        Returns:
            View dict with visibility controlled by information_level

        Example (full information):
            >>> game = FixedDamageGame(information_level="full")
            >>> state = game.setup(["Alice", "Bob"])
            >>> view = game.get_view(state, "Alice")
            >>> "Bob" in view["health"]
            True

        Example (partial information):
            >>> game = FixedDamageGame(information_level="partial")
            >>> state = game.setup(["Alice", "Bob"])
            >>> view = game.get_view(state, "Alice")
            >>> "Bob" in view["health"]
            False
        """
        # Always include player's own stats
        view = {
            "health": {player: game_state["health"][player]},
            "potions": {player: game_state["potions"][player]},
            "last_action": game_state["last_action"],  # All actions visible
            "turn": game_state["turn"],
        }

        # Conditionally include opponent stats based on information_level (IV2-IV3)
        if self.information_level == "full":
            # IV2: Full visibility - show all player stats
            opponents = [p for p in game_state["health"] if p != player]
            for opp in opponents:
                view["health"][opp] = game_state["health"][opp]
                view["potions"][opp] = game_state["potions"][opp]

        # IV3: Partial visibility - only player's own stats (already handled above)

        return view
