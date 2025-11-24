"""
AgentDeck UX Research: Minimal Configuration with Monitors

Purpose:
    Demonstrate minimal configuration with parallel execution and progress monitoring.
    Smart defaults handle templates, controllers, rendering, and progress reporting.

Usage:
    export OPENAI_API_KEY="sk-..."
    python examples/test_prompt_builder_ux_minimal.py

What This Demonstrates:
    ✓ Zero template configuration (smart defaults used)
    ✓ Minimal player setup (just action_controller required)
    ✓ Out-of-the-box three-phase lifecycle (handshake → turn → conclusion)
    ✓ Parallel execution with real-time progress monitoring (SPEC-MONITOR v1.0.0)
    ✓ Auto-attached ProgressMonitor when concurrency > 1
    ✓ Turn-by-turn narrative via MatchNarrator spectator
    ✓ Dual-tier observation: monitors (console events) + spectators (match events)

Smart Defaults Used (SPEC-PLAYER v1.0.0):
    handshake_controller: AcceptOKHandshakeController()
    renderer: TextRenderer()
    handshake_template: "You are playing {game_name}.\n\n{game_instructions}\n\n{player_instructions}\n\n{controller_format}\n\n{handshake_controller_format}"
    turn_template: "{game_view}\n\n{controller_format}"
    conclusion_template: None

Parallel Execution (SPEC-PARALLEL v1.0.0):
    - concurrency=10: Run up to 10 matches concurrently
    - Deep-copy isolation: Each worker has isolated game/player state
    - Event replay: Spectators receive events in match_index order
    - Deterministic seeding: base_seed + match_index

Progress Monitoring (SPEC-MONITOR v1.0.0):
    - ProgressMonitor auto-attached when concurrency > 1 (mode="normal")
    - Displays milestone updates with ETA during parallel execution
    - Logger injection: Same pattern as spectators (LI1-LI5)
    - Custom monitors can use self.logger for structured logging to files

Observability:
    - Monitors: Console-level events (batch progress, worker lifecycle)
    - Spectators: Match-level events (turn-by-turn narrative)
    - Logger auto-injected to both monitors and spectators
    - Output flows to info.log/debug.log and console (INFO level)

Note: {player_instructions} renders as empty string when not in extras (no error).
"""

from agentdeck import AgentDeck
from agentdeck.controllers.action_only import ActionOnlyController
from agentdeck.core.session import AgentDeckConfig
from agentdeck.core.types import Event, LogLevel
from agentdeck.games.examples import FixedDamageGame
from agentdeck.monitors import Monitor, ProgressMonitor
from agentdeck.players.openai_player import GPTPlayer
from agentdeck.spectators import MatchNarrator
from agentdeck.prompts import DEFAULT_CONCLUSION_TEMPLATE_PATH


class CustomMonitor(Monitor):
    """
    Example custom monitor demonstrating logger usage.

    Logger is auto-injected by Console (same as spectators).
    Output flows to agentdeck_logs/session_XXX/info.log and console.
    """

    def on_console_batch_start(self, event: Event) -> None:
        """Log batch start to structured log files."""
        data = event.data
        if self.logger:
            self.logger.info(
                f"[CustomMonitor] Batch starting: {data['total_matches']} matches "
                f"(concurrency={data['concurrency']}, mode={data['mode']})"
            )

    def on_console_batch_complete(self, event: Event) -> None:
        """Log batch completion with statistics."""
        data = event.data
        if self.logger:
            self.logger.info(
                f"[CustomMonitor] Batch complete: {data['completed']}/{data['total']} matches "
                f"in {data['duration']:.1f}s (avg {data['avg_match_duration']:.1f}s/match)"
            )

    def on_console_worker_complete(self, event: Event) -> None:
        """Log individual worker completion (only in parallel mode)."""
        data = event.data
        if self.logger:
            self.logger.debug(
                f"[CustomMonitor] Worker {data['worker_id']} complete: "
                f"winner={data['winner']}, turns={data['turns']}, duration={data['duration']:.1f}s"
            )


def main():
    """
    Run FixedDamageGame with parallel execution and progress monitoring.

    Demonstrates:
    1. Auto-attached ProgressMonitor (concurrency > 1)
    2. Optional custom monitor with logger usage
    3. Spectators for match-level observation
    4. Logger injection for both monitors and spectators
    """

    game = FixedDamageGame(
        max_health=100,
        attack_damage=20,
        potion_heal=30,
        starting_potions=1,
        information_level="partial"
    )

    # Identical players with minimal configuration
    players = [
        GPTPlayer(
            name="Player-1",
            model="gpt-4o-mini",
            temperature=0.7,
            controller=ActionOnlyController(),
            conclusion_template=DEFAULT_CONCLUSION_TEMPLATE_PATH,
        ),
        GPTPlayer(
            name="Player-2",
            model="gpt-4o-mini",
            temperature=0.7,
            controller=ActionOnlyController(),
            conclusion_template=DEFAULT_CONCLUSION_TEMPLATE_PATH,
        )
    ]

    # Option 1: Use default ProgressMonitor (auto-attached when concurrency > 1)
    config_default = AgentDeckConfig(
        seed=42,
        concurrency=2,
        log_level=LogLevel.INFO
    )

    # Option 2: Explicit monitor configuration with custom mode
    config_verbose = AgentDeckConfig(
        seed=42,
        concurrency=10,
        log_level=LogLevel.INFO,
        monitors=[
            ProgressMonitor(mode="verbose"),  # Show worker-level details
            CustomMonitor(),  # Also log to structured files
        ]
    )

    # Option 3: Silent execution (no progress monitor)
    config_silent = AgentDeckConfig(
        seed=42,
        concurrency=10,
        log_level=LogLevel.INFO,
        monitors=[]  # Explicitly opt-out of progress monitoring
    )

    # Run with default ProgressMonitor (mode="normal")
    print("\n=== Running with default ProgressMonitor ===\n")
    with AgentDeck(game=game, session=config_default, spectators=[MatchNarrator()]) as deck:
        deck.play(players=players, matches=10)

    # Uncomment to test verbose mode or silent execution:
    # print("\n=== Running with verbose ProgressMonitor + CustomMonitor ===\n")
    # with AgentDeck(game=game, session=config_verbose, spectators=[MatchNarrator()]) as deck:
    #     deck.play(players=players, matches=10)

    # print("\n=== Running with silent execution (no monitors) ===\n")
    # with AgentDeck(game=game, session=config_silent, spectators=[MatchNarrator()]) as deck:
    #     deck.play(players=players, matches=10)

if __name__ == "__main__":
    main()
