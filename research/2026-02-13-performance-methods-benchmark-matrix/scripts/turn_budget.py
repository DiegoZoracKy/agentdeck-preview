#!/usr/bin/env python3
"""Turn-budget helpers for the performance benchmark matrix.

This module is intentionally kept in the experiment package (not in Game classes)
to keep AgentDeck components simple for newcomers while preserving reproducible
experiment configuration logic.
"""

from __future__ import annotations

import argparse
import math


def estimate_attacks_to_eliminate(
    *, max_health: int, attack_damage: int, potion_heal: int, starting_potions: int
) -> int:
    """Estimate attacks needed to eliminate one player with optimal potion usage."""
    if attack_damage <= 0:
        raise ValueError(f"attack_damage must be > 0, got {attack_damage}")
    if max_health <= 0:
        raise ValueError(f"max_health must be > 0, got {max_health}")
    if potion_heal < 0:
        raise ValueError(f"potion_heal must be >= 0, got {potion_heal}")
    if starting_potions < 0:
        raise ValueError(f"starting_potions must be >= 0, got {starting_potions}")

    effective_hp = max_health + (starting_potions * potion_heal)
    return max(1, math.ceil(effective_hp / attack_damage))


def estimate_meaningful_turn_cap(
    *,
    max_health: int,
    attack_damage: int,
    potion_heal: int,
    starting_potions: int,
    players_count: int = 2,
) -> int:
    """Estimate upper bound for meaningful gameplay turns (excludes lifecycle phases)."""
    if players_count < 2:
        raise ValueError(f"players_count must be >= 2, got {players_count}")

    attacks_to_eliminate = estimate_attacks_to_eliminate(
        max_health=max_health,
        attack_damage=attack_damage,
        potion_heal=potion_heal,
        starting_potions=starting_potions,
    )
    duel_turn_cap = (2 * attacks_to_eliminate) - 1
    potion_action_turns = players_count * starting_potions
    return duel_turn_cap + potion_action_turns


def recommend_max_turns(
    *,
    max_health: int,
    attack_damage: int,
    potion_heal: int,
    starting_potions: int,
    players_count: int = 2,
    safety_factor: float = 1.5,
    round_to: int = 5,
    min_turns: int = 20,
) -> int:
    """Recommend practical max_turns for runs with bounded latency and cost."""
    if safety_factor <= 0:
        raise ValueError(f"safety_factor must be > 0, got {safety_factor}")
    if round_to < 1:
        raise ValueError(f"round_to must be >= 1, got {round_to}")
    if min_turns < 1:
        raise ValueError(f"min_turns must be >= 1, got {min_turns}")

    base_cap = estimate_meaningful_turn_cap(
        max_health=max_health,
        attack_damage=attack_damage,
        potion_heal=potion_heal,
        starting_potions=starting_potions,
        players_count=players_count,
    )
    buffered = math.ceil(base_cap * safety_factor)
    rounded = int(math.ceil(buffered / round_to) * round_to)
    return max(min_turns, rounded)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute turn budget for FixedDamageGame configs.")
    parser.add_argument("--max-health", type=int, default=100)
    parser.add_argument("--attack-damage", type=int, default=20)
    parser.add_argument("--potion-heal", type=int, default=30)
    parser.add_argument("--starting-potions", type=int, default=2)
    parser.add_argument("--players-count", type=int, default=2)
    parser.add_argument("--safety-factor", type=float, default=1.5)
    parser.add_argument("--round-to", type=int, default=5)
    parser.add_argument("--min-turns", type=int, default=20)
    return parser


def main() -> None:
    args = _build_parser().parse_args()

    attacks = estimate_attacks_to_eliminate(
        max_health=args.max_health,
        attack_damage=args.attack_damage,
        potion_heal=args.potion_heal,
        starting_potions=args.starting_potions,
    )
    meaningful_cap = estimate_meaningful_turn_cap(
        max_health=args.max_health,
        attack_damage=args.attack_damage,
        potion_heal=args.potion_heal,
        starting_potions=args.starting_potions,
        players_count=args.players_count,
    )
    recommended = recommend_max_turns(
        max_health=args.max_health,
        attack_damage=args.attack_damage,
        potion_heal=args.potion_heal,
        starting_potions=args.starting_potions,
        players_count=args.players_count,
        safety_factor=args.safety_factor,
        round_to=args.round_to,
        min_turns=args.min_turns,
    )

    print(f"attacks_to_eliminate={attacks}")
    print(f"meaningful_turn_cap={meaningful_cap}")
    print(f"recommended_max_turns={recommended}")


if __name__ == "__main__":
    main()
