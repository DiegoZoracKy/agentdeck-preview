"""
HangmanGame: Cooperative word-guessing game for AgentDeck.

Research value: Tests LLM "tokenization blindness" - the challenge of
character-level reasoning when models process words as single tokens.

Key hypotheses to test:
- Do LLMs struggle with character-level tasks vs semantic tasks?
- Do models hallucinate letters based on word concepts vs actual spelling?
- Can multiple models cooperate effectively on character-level reasoning?
- Do models track shared context (previously guessed letters)?

Per SPEC-GAME v0.5.0.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agentdeck.core.mechanics.turn_based import TurnBasedGame
from agentdeck.core.types import (
    ActionResult,
    GameStatus,
    ParseFailurePolicy,
    RandomGenerator,
)

# Default word list for testing - mix of AI/ML terms
DEFAULT_WORDS = [
    "AGENT",
    "NEURAL",
    "TENSOR",
    "PYTORCH",
    "WEIGHTS",
    "GRADIENT",
    "EPOCH",
    "BATCH",
    "LAYER",
    "TOKEN",
    "EMBEDDING",
    "ATTENTION",
    "TRANSFORMER",
    "ENCODER",
    "DECODER",
    "SOFTMAX",
    "RELU",
    "DROPOUT",
    "KERNEL",
]


class HangmanGame(TurnBasedGame):
    """
    Cooperative Hangman: Multiple players work together to guess a word.

    Research Focus:
        Tests "tokenization blindness" - LLMs see "ELEPHANT" as one token,
        not 8 letters. This exposes character-level reasoning limitations.

    Rules:
        - System chooses a secret word
        - Players take turns guessing single letters (A-Z)
        - Correct guesses reveal letter positions
        - Wrong guesses increment failure counter
        - All players win if word is complete before max_wrong_guesses
        - All players lose if max_wrong_guesses reached

    Configuration:
        - word_list: Custom words to choose from (default: AI/ML terms)
        - max_wrong_guesses: Failures before game over (default: 6)

    Observable Behaviors:
        - Hallucinations: Guessing letters not in the word pattern
        - Context failures: Re-guessing already-tried letters
        - Strategy: Frequency-based (ETAOIN) vs pattern-based guessing
        - Cooperation: Do players build on each other's progress?

    State structure:
        {
            "secret_word": str,           # Hidden from players
            "guessed_letters": List[str], # All guesses so far
            "wrong_guesses": int,         # Failure counter
            "max_wrong_guesses": int,     # Limit before loss
            "guess_history": List[dict],  # Who guessed what
            "turn": int,                  # Turn counter
            "players": List[str]          # Player roster
        }
    """

    def __init__(
        self,
        word_list: List[str] | None = None,
        max_wrong_guesses: int = 6,
    ):
        """
        Initialize HangmanGame with configuration.

        Args:
            word_list: Words to choose from (default: AI/ML terms)
            max_wrong_guesses: Failures before game over (default: 6)
        """
        super().__init__()
        self.word_list = [w.upper() for w in (word_list or DEFAULT_WORDS)]
        self.max_wrong_guesses = max_wrong_guesses

    # ========================================================================
    # Required Properties
    # ========================================================================

    @property
    def instructions(self) -> str:
        """
        Game rules description for players.

        Returns:
            Plain text description of game rules
        """
        return f"""
Cooperative Hangman

Objective:
- Work together to guess the secret word before running out of attempts

Rules:
- On your turn, guess ONE letter (A-Z)
- Correct guesses reveal all instances of that letter in the word
- Wrong guesses count against the team (max {self.max_wrong_guesses})
- You can see which letters have already been guessed
- Win: Complete the word before {self.max_wrong_guesses} wrong guesses
- Lose: Reach {self.max_wrong_guesses} wrong guesses

Strategy Tips:
- Common letters: E, T, A, O, I, N, S, R
- Look at the pattern to narrow down possibilities
- Don't repeat letters that were already guessed
        """.strip()

    @property
    def allowed_actions(self) -> List[str]:
        """
        Valid actions: single letters A-Z.

        Returns:
            List of valid letter guesses
        """
        return list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    @property
    def default_handshake_template(self) -> str:
        """
        Template for player handshake phase.

        Returns:
            Template string with placeholders for PromptBuilder
        """
        return "{game_instructions}\n\nRespond 'OK' when you're ready to begin."

    def on_action_parse_failure(
        self, player: str, error: str, state: Dict[str, Any]
    ) -> ParseFailurePolicy:
        """
        Handle parse failures - skip turn and penalize.

        SKIP_TURN allows game to continue but the update() method
        will increment wrong_guesses for the invalid action.
        """
        return ParseFailurePolicy.SKIP_TURN

    # ========================================================================
    # Required Methods
    # ========================================================================

    def setup(self, players: List[str], seed: int) -> Dict[str, Any]:
        """
        Initialize game state with secret word.

        Args:
            players: Player roster (cooperative team)
            seed: RNG seed for word selection

        Returns:
            Initial game state dict
        """
        import random

        rng = random.Random(seed)
        secret_word = rng.choice(self.word_list)

        return {
            "secret_word": secret_word,
            "guessed_letters": [],
            "wrong_guesses": 0,
            "max_wrong_guesses": self.max_wrong_guesses,
            "guess_history": [],
            "turn": 1,
            "players": list(players),
        }

    def update(
        self, game_state: Dict[str, Any], player: str, action: ActionResult, *, rng: RandomGenerator
    ) -> Dict[str, Any]:
        """
        Process a letter guess.

        Args:
            game_state: Current state
            player: Guessing player
            action: Parsed action (should be single letter)
            rng: Deterministic RNG (not used)

        Returns:
            Updated state
        """
        state = dict(game_state)
        state["guessed_letters"] = list(state["guessed_letters"])
        state["guess_history"] = list(state["guess_history"])

        # Extract and normalize guess
        guess = action.action.strip().upper()

        # Handle SKIP_TURN sentinel - count as wrong guess
        if guess == "__SKIP_TURN__":
            state["wrong_guesses"] += 1
            state["guess_history"].append(
                {
                    "player": player,
                    "guess": "[INVALID]",
                    "result": "skip",
                    "turn": state["turn"],
                }
            )
            state["turn"] += 1
            return state

        # Handle multi-character input - take first letter
        if len(guess) > 1:
            guess = guess[0]

        # Validate it's a letter
        if not guess.isalpha() or len(guess) != 1:
            raise ValueError(f"Invalid guess '{action.action}'. Must be a single letter A-Z.")

        # Check if already guessed - penalize as wrong guess
        if guess in state["guessed_letters"]:
            state["wrong_guesses"] += 1
            state["guess_history"].append(
                {
                    "player": player,
                    "guess": guess,
                    "result": "duplicate",
                    "turn": state["turn"],
                }
            )
            state["turn"] += 1
            return state

        # Record the guess
        state["guessed_letters"].append(guess)

        # Check if correct
        if guess in state["secret_word"]:
            result = "correct"
        else:
            result = "wrong"
            state["wrong_guesses"] += 1

        state["guess_history"].append(
            {
                "player": player,
                "guess": guess,
                "result": result,
                "turn": state["turn"],
            }
        )
        state["turn"] += 1

        return state

    def status(self, game_state: Dict[str, Any]) -> GameStatus:
        """
        Check win/lose conditions.

        Args:
            game_state: Current state

        Returns:
            GameStatus with is_over and winner
        """
        secret = game_state["secret_word"]
        guessed = game_state["guessed_letters"]

        # Win: All letters in secret word have been guessed
        if all(char in guessed for char in secret):
            # Cooperative win - all players win together
            # Return first player as winner (represents the team)
            return GameStatus(is_over=True, winner=game_state["players"][0])

        # Lose: Too many wrong guesses
        if game_state["wrong_guesses"] >= game_state["max_wrong_guesses"]:
            return GameStatus(is_over=True, winner=None)

        # Game continues
        return GameStatus(is_over=False, winner=None)

    def get_view(self, game_state: Dict[str, Any], player: str) -> Dict[str, Any]:
        """
        Create player view with masked word (hides secret).

        Args:
            game_state: Full state (includes secret_word)
            player: Requesting player

        Returns:
            View dict with board display and available letters
        """
        secret = game_state["secret_word"]
        guessed = game_state["guessed_letters"]

        # Create masked board (e.g., "A _ E _ T")
        board = " ".join([char if char in guessed else "_" for char in secret])

        # Available letters (not yet guessed)
        available = [c for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ" if c not in guessed]

        # Recent guess history (last 5 for context)
        recent_history = game_state["guess_history"][-5:] if game_state["guess_history"] else []

        return {
            "board": board,
            "word_length": len(secret),
            "wrong_guesses": game_state["wrong_guesses"],
            "max_wrong_guesses": game_state["max_wrong_guesses"],
            "guessed_letters": list(guessed),
            "available_letters": available,
            "recent_guesses": [
                f"{h['player']}: {h['guess']} ({h['result']})" for h in recent_history
            ],
            "turn": game_state["turn"],
        }
