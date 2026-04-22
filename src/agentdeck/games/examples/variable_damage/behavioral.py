"""VariableDamage behavioral scorer."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from statistics import median
from typing import Any, DefaultDict, Dict, Iterable, List, Mapping, Optional, Tuple

from agentdeck.research.behavioral import BehavioralScorer

CONSISTENCY_MIN_SUPPORT = 2
POSITION_DELTA_MIN_SUPPORT_PER_POSITION = 2
RISK_BAND_MIN_SUPPORT = 2
EVIDENCE_MAX_EXAMPLES = 3
RISK_BANDS = ("lethal", "danger", "safe")


NormalizedTurn = Dict[str, Any]


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _bucket_key(position: str, own_hp: int, own_potions: int) -> str:
    return f"position={position}|hp={own_hp}|potions={own_potions}"


def _shared_state_key(own_hp: int, own_potions: int) -> str:
    return f"hp={own_hp}|potions={own_potions}"


def _risk_bucket_key(position: str, risk_band: str, own_potions: int) -> str:
    return f"position={position}|risk={risk_band}|potions={own_potions}"


def _shared_risk_key(risk_band: str, own_potions: int) -> str:
    return f"risk={risk_band}|potions={own_potions}"


def _risk_scarcity_key(risk_band: str, scarcity_bucket: str) -> str:
    return f"risk={risk_band}|scarcity={scarcity_bucket}"


def _decision_key(
    position: str,
    own_hp: int,
    own_potions: int,
    last_action_self: str | None,
    last_action_opponent: str | None,
) -> str:
    self_value = last_action_self or "NONE"
    opponent_value = last_action_opponent or "NONE"
    return (
        f"position={position}|hp={own_hp}|potions={own_potions}|"
        f"self={self_value}|opp={opponent_value}"
    )


def _extract_turn_number(event_data: Mapping[str, Any]) -> int:
    turn_context = event_data.get("turn_context") or {}
    metadata = event_data.get("metadata") or {}
    prompt = event_data.get("prompt") or {}

    for value in (
        turn_context.get("turn_number"),
        metadata.get("turn_number"),
        (metadata.get("turn_context") or {}).get("turn_number"),
        prompt.get("turn_number"),
    ):
        if value is not None:
            return int(value)
    raise ValueError("Missing turn_number in gameplay event")


def _game_name(payload: Mapping[str, Any]) -> str:
    direct = payload.get("game")
    if isinstance(direct, str) and direct:
        return direct
    metadata = payload.get("metadata") or {}
    name = metadata.get("game")
    if isinstance(name, str) and name:
        return name
    game_config = metadata.get("game_config") or {}
    name = game_config.get("name")
    if name:
        return str(name)
    raise ValueError("Unable to determine game name for behavioral scoring")


def _risk_band(*, own_hp: int, max_attack_damage: int, potion_heal: int) -> str:
    if own_hp <= int(max_attack_damage):
        return "lethal"
    if own_hp <= int(max_attack_damage) + int(potion_heal):
        return "danger"
    return "safe"


def _top_half_min_damage(min_attack_damage: int, max_attack_damage: int) -> int:
    # Treat the midpoint as part of the upper half for odd-sized inclusive ranges.
    return int(math.ceil((int(min_attack_damage) + int(max_attack_damage)) / 2.0))


def _danger_split_hp(
    *,
    min_attack_damage: int,
    max_attack_damage: int,
    potion_heal: int,
) -> int:
    return min(
        int(max_attack_damage) + int(potion_heal),
        int(min_attack_damage) + int(max_attack_damage),
    )


def _danger_subband(
    *,
    own_hp: int,
    min_attack_damage: int,
    max_attack_damage: int,
    potion_heal: int,
) -> str | None:
    upper_danger = int(max_attack_damage) + int(potion_heal)
    if own_hp <= int(max_attack_damage) or own_hp > upper_danger:
        return None
    if own_hp <= _danger_split_hp(
        min_attack_damage=int(min_attack_damage),
        max_attack_damage=int(max_attack_damage),
        potion_heal=int(potion_heal),
    ):
        return "lower"
    return "upper"


def _scarcity_bucket(own_potions: int) -> str | None:
    if int(own_potions) <= 0:
        return None
    if int(own_potions) == 1:
        return "one"
    return "multiple"


def _resolve_config(
    *,
    config: Optional[Mapping[str, Any]],
    match_payloads: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    resolved = dict(config or {})
    wanted = {
        "min_attack_damage",
        "max_attack_damage",
        "potion_heal",
        "max_health",
    }
    if wanted.issubset(resolved.keys()):
        return resolved

    for payload in match_payloads:
        metadata = payload.get("metadata") or {}
        candidates = []

        game_config = metadata.get("game_config")
        if isinstance(game_config, Mapping):
            candidates.append(game_config)

        match_game = (metadata.get("match") or {}).get("game")
        if isinstance(match_game, Mapping):
            candidates.append(match_game)
            nested_config = match_game.get("config")
            if isinstance(nested_config, Mapping):
                candidates.append(nested_config)

        for candidate in candidates:
            for key in wanted:
                if key not in resolved and candidate.get(key) is not None:
                    resolved[key] = candidate.get(key)

        if wanted.issubset(resolved.keys()):
            break

    return resolved


class VariableDamageBehavioralScorer(BehavioralScorer):
    game_id = "variable_damage"
    profile_id = "variable_damage_behavioral"
    profile_version = "0.1.0"

    def supports(self, *, match_payloads: Iterable[Mapping[str, Any]]) -> bool:
        names = set()
        for payload in match_payloads:
            if not isinstance(payload, Mapping):
                return False
            try:
                names.add(_game_name(payload))
            except ValueError:
                return False
        return bool(names) and names == {"VariableDamageGame"}

    def score(
        self,
        *,
        players: List[Mapping[str, Any]],
        match_payloads: Iterable[Mapping[str, Any]],
        config: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        roster = [str(player["name"]) for player in players if player.get("name")]
        if not roster:
            raise ValueError("Behavioral scoring requires player metadata with names")

        player_names = set(roster)
        match_list = list(match_payloads)
        config_map = _resolve_config(config=config, match_payloads=match_list)

        min_attack_damage = config_map.get("min_attack_damage")
        max_attack_damage = config_map.get("max_attack_damage")
        potion_heal = config_map.get("potion_heal")
        max_health = config_map.get("max_health")

        risk_metrics = {
            "action_by_risk_band",
            "safe_zone_potion_rate",
            "lethal_zone_potion_rate",
            "danger_zone_potion_rate",
            "lethal_zone_attack_rate",
            "danger_zone_attack_rate",
            "risk_band_potion_rate_by_scarcity",
            "risk_band_policy_delta",
        }
        unsupported_metrics = set()
        if max_attack_damage is None or potion_heal is None:
            unsupported_metrics.update(risk_metrics)
            unsupported_metrics.update(
                {
                    "lower_danger_zone_potion_rate",
                    "upper_danger_zone_potion_rate",
                }
            )
        if max_attack_damage is None:
            unsupported_metrics.add("first_lethal_entry_inventory")
        if min_attack_damage is None:
            unsupported_metrics.update(
                {
                    "lower_danger_zone_potion_rate",
                    "upper_danger_zone_potion_rate",
                }
            )
        if min_attack_damage is None or max_attack_damage is None:
            unsupported_metrics.add("high_roll_recovery_rate")
        if max_health is None:
            unsupported_metrics.add("wasted_full_health_potion_rate")

        turns: List[NormalizedTurn] = []
        matches_total = len(match_list)
        matches_evaluable = 0

        matches_played = Counter()
        all_attack_matches = Counter()
        first_potion_values: DefaultDict[str, List[int]] = defaultdict(list)
        never_used_matches = Counter()
        first_lethal_entry_values: DefaultDict[str, List[int]] = defaultdict(list)
        never_entered_lethal_matches = Counter()
        first_lethal_zero_matches = Counter()
        decisive_losses = Counter()
        losses_with_unused_potions = Counter()
        per_player_turns: DefaultDict[str, List[NormalizedTurn]] = defaultdict(list)
        shocks_by_player: DefaultDict[str, List[Dict[str, Any]]] = defaultdict(list)
        can_compute_realized_damage = True

        for payload in match_list:
            if _game_name(payload) != "VariableDamageGame":
                raise ValueError(
                    "VariableDamageBehavioralScorer only supports VariableDamageGame payloads"
                )

            match_id = str(payload.get("match_id") or "")
            if not match_id:
                raise ValueError("Missing match_id in behavioral payload")

            metadata = payload.get("metadata") or {}
            match_meta = metadata.get("match") or {}
            match_players = [
                str(name) for name in (payload.get("players") or match_meta.get("players") or [])
            ]
            if len(match_players) != 2:
                raise ValueError(
                    "VariableDamage behavioral scoring requires exactly two players per match"
                )
            unknown = sorted(set(match_players) - player_names)
            if unknown:
                raise ValueError(f"Unknown players in match payload: {unknown}")

            first_player = (match_meta.get("first_player") or {}).get("name")
            if not first_player:
                raise ValueError("Missing first_player metadata for behavioral scoring")
            first_player = str(first_player)
            if first_player not in match_players:
                raise ValueError(f"first_player '{first_player}' not present in match players")

            second_player = next(name for name in match_players if name != first_player)
            position_by_player = {first_player: "first", second_player: "second"}

            gameplay_events = [
                event for event in (payload.get("events") or []) if event.get("type") == "gameplay"
            ]
            if gameplay_events:
                matches_evaluable += 1

            match_turns_by_player: DefaultDict[str, List[NormalizedTurn]] = defaultdict(list)

            for player in match_players:
                matches_played[player] += 1

            for event in gameplay_events:
                event_data = event.get("data") or {}
                player = str(event_data.get("player") or "")
                if not player:
                    raise ValueError("Gameplay event missing player")
                if player not in player_names:
                    raise ValueError(f"Unknown player in gameplay event: {player}")

                state_before = event_data.get("state_before") or {}
                health_before = state_before.get("health") or {}
                potions_before = state_before.get("potions") or {}
                last_action = state_before.get("last_action") or {}
                if player not in health_before or player not in potions_before:
                    raise ValueError(
                        f"Gameplay state_before missing acting player fields for {player}"
                    )

                opponent = next(name for name in match_players if name != player)
                action = str(event_data.get("action") or "").upper()
                record: NormalizedTurn = {
                    "match_id": match_id,
                    "player": player,
                    "position": position_by_player[player],
                    "turn_number": _extract_turn_number(event_data),
                    "action": action,
                    "own_hp": int(health_before[player]),
                    "own_potions": int(potions_before[player]),
                    "last_action_self": last_action.get(player),
                    "last_action_opponent": last_action.get(opponent),
                }

                if max_attack_damage is not None and potion_heal is not None:
                    record["risk_band"] = _risk_band(
                        own_hp=record["own_hp"],
                        max_attack_damage=int(max_attack_damage),
                        potion_heal=int(potion_heal),
                    )

                state_after = event_data.get("state_after")
                if isinstance(state_after, Mapping) and action == "ATTACK":
                    health_after = state_after.get("health") or {}
                    if opponent in health_before and opponent in health_after:
                        record["damage_dealt"] = int(health_before[opponent]) - int(
                            health_after[opponent]
                        )

                turns.append(record)
                per_player_turns[player].append(record)
                match_turns_by_player[player].append(record)

                if (
                    action == "ATTACK"
                    and min_attack_damage is not None
                    and max_attack_damage is not None
                ):
                    if not isinstance(state_after, Mapping):
                        can_compute_realized_damage = False
                        continue
                    health_after = state_after.get("health") or {}
                    if player not in health_before or opponent not in health_before:
                        continue
                    if player not in health_after or opponent not in health_after:
                        can_compute_realized_damage = False
                        continue

                    target_before = int(health_before[opponent])
                    target_after = int(health_after[opponent])
                    realized_damage = target_before - target_after
                    high_roll_min_damage = _top_half_min_damage(
                        int(min_attack_damage), int(max_attack_damage)
                    )
                    if target_after > 0 and realized_damage >= high_roll_min_damage:
                        shocks_by_player[opponent].append(
                            {
                                "match_id": match_id,
                                "shock_turn_number": record["turn_number"],
                                "damage_dealt": realized_damage,
                            }
                        )

            final_state = payload.get("final_state") or {}
            final_potions = final_state.get("potions") or {}
            winner = payload.get("winner")

            for player in match_players:
                player_turns = sorted(
                    match_turns_by_player.get(player, []),
                    key=lambda item: item["turn_number"],
                )
                if player_turns and all(turn["action"] == "ATTACK" for turn in player_turns):
                    all_attack_matches[player] += 1

                first_potion = next(
                    (
                        turn["own_hp"]
                        for turn in player_turns
                        if turn["action"] == "POTION" and turn["own_potions"] > 0
                    ),
                    None,
                )
                if first_potion is None:
                    never_used_matches[player] += 1
                else:
                    first_potion_values[player].append(int(first_potion))

                if max_attack_damage is not None:
                    first_lethal_turn = next(
                        (
                            turn
                            for turn in player_turns
                            if int(turn["own_hp"]) <= int(max_attack_damage)
                        ),
                        None,
                    )
                    if first_lethal_turn is None:
                        never_entered_lethal_matches[player] += 1
                    else:
                        lethal_potions_on_entry = int(first_lethal_turn["own_potions"])
                        first_lethal_entry_values[player].append(lethal_potions_on_entry)
                        if lethal_potions_on_entry == 0:
                            first_lethal_zero_matches[player] += 1

                if winner is not None and winner != player:
                    decisive_losses[player] += 1
                    if int(final_potions.get(player, 0)) > 0:
                        losses_with_unused_potions[player] += 1

        if not can_compute_realized_damage:
            unsupported_metrics.add("high_roll_recovery_rate")

        turns_total = len(turns)
        turns_evaluable = turns_total

        per_player_results: Dict[str, Dict[str, Any]] = {}
        action_by_state: Dict[str, Dict[str, Any]] = {}
        action_by_risk_band: Dict[str, Dict[str, Any]] = {}
        evidence_per_player: Dict[str, Dict[str, Any]] = {}

        consistency_scores: List[Tuple[float, int]] = []
        position_deltas: List[Tuple[float, int]] = []
        risk_band_deltas: List[Tuple[float, int]] = []
        all_attack_support = 0
        all_attack_hits = 0
        never_used_support = 0
        never_used_hits = 0
        first_potion_all_values: List[int] = []
        unused_loss_support = 0
        unused_loss_hits = 0
        first_lethal_support = 0
        first_lethal_zero_hits = 0
        first_lethal_all_values: List[int] = []
        first_lethal_never_entered_support = 0
        first_lethal_never_entered_hits = 0
        safe_potion_support = 0
        safe_potion_hits = 0
        lethal_potion_support = 0
        lethal_potion_hits = 0
        lethal_attack_support = 0
        lethal_attack_hits = 0
        danger_potion_support = 0
        danger_potion_hits = 0
        danger_attack_support = 0
        danger_attack_hits = 0
        lower_danger_potion_support = 0
        lower_danger_potion_hits = 0
        upper_danger_potion_support = 0
        upper_danger_potion_hits = 0
        scarcity_aggregate: DefaultDict[str, Dict[str, int]] = defaultdict(
            lambda: {"support_turns": 0, "potion_turns": 0}
        )
        high_roll_support = 0
        high_roll_hits = 0
        wasted_full_health_support = 0
        wasted_full_health_hits = 0

        risk_config_available = max_attack_damage is not None and potion_heal is not None
        danger_split_available = (
            min_attack_damage is not None
            and max_attack_damage is not None
            and potion_heal is not None
        )
        high_roll_config_available = min_attack_damage is not None and max_attack_damage is not None

        for player in roster:
            player_turn_list = sorted(
                per_player_turns.get(player, []),
                key=lambda item: (item["match_id"], item["turn_number"]),
            )
            match_support = matches_played[player]

            all_attack_rate = _safe_rate(all_attack_matches[player], match_support)
            never_used_rate = _safe_rate(never_used_matches[player], match_support)
            all_attack_support += match_support
            all_attack_hits += all_attack_matches[player]
            never_used_support += match_support
            never_used_hits += never_used_matches[player]

            potion_values = sorted(first_potion_values[player])
            first_potion_all_values.extend(potion_values)

            unused_loss_rate = _safe_rate(
                losses_with_unused_potions[player],
                decisive_losses[player],
            )
            unused_loss_support += decisive_losses[player]
            unused_loss_hits += losses_with_unused_potions[player]

            lethal_entry_values = sorted(first_lethal_entry_values[player])
            first_lethal_all_values.extend(lethal_entry_values)
            first_lethal_support += len(lethal_entry_values)
            first_lethal_zero_hits += first_lethal_zero_matches[player]
            first_lethal_never_entered_support += match_support
            first_lethal_never_entered_hits += never_entered_lethal_matches[player]

            by_decision_key: DefaultDict[str, Counter[str]] = defaultdict(Counter)
            by_shared_state: DefaultDict[str, Dict[str, Counter[str]]] = defaultdict(
                lambda: {"first": Counter(), "second": Counter()}
            )
            by_bucket: DefaultDict[str, Counter[str]] = defaultdict(Counter)
            by_shared_risk: DefaultDict[str, Dict[str, Counter[str]]] = defaultdict(
                lambda: {"first": Counter(), "second": Counter()}
            )
            by_risk_bucket: DefaultDict[str, Counter[str]] = defaultdict(Counter)

            for turn in player_turn_list:
                decision_key = _decision_key(
                    turn["position"],
                    turn["own_hp"],
                    turn["own_potions"],
                    turn["last_action_self"],
                    turn["last_action_opponent"],
                )
                by_decision_key[decision_key][turn["action"]] += 1

                shared_key = _shared_state_key(turn["own_hp"], turn["own_potions"])
                by_shared_state[shared_key][turn["position"]][turn["action"]] += 1

                bucket_key = _bucket_key(turn["position"], turn["own_hp"], turn["own_potions"])
                by_bucket[bucket_key][turn["action"]] += 1

                if risk_config_available:
                    band = str(turn["risk_band"])
                    risk_bucket_key = _risk_bucket_key(turn["position"], band, turn["own_potions"])
                    by_risk_bucket[risk_bucket_key][turn["action"]] += 1

                    shared_risk_key = _shared_risk_key(band, turn["own_potions"])
                    by_shared_risk[shared_risk_key][turn["position"]][turn["action"]] += 1

            consistency_weight = 0
            consistency_total = 0.0
            supported_keys = 0
            consistency_examples = []
            for decision_key, counts in by_decision_key.items():
                support = sum(counts.values())
                if support < CONSISTENCY_MIN_SUPPORT:
                    continue
                supported_keys += 1
                consistency = max(counts.values()) / support
                consistency_weight += support
                consistency_total += consistency * support
                attack_count = int(counts.get("ATTACK", 0))
                potion_count = int(counts.get("POTION", 0))
                if attack_count > potion_count:
                    dominant_action: str | None = "ATTACK"
                elif potion_count > attack_count:
                    dominant_action = "POTION"
                else:
                    dominant_action = None
                consistency_examples.append(
                    {
                        "decision_key": decision_key,
                        "consistency": consistency,
                        "support_turns": support,
                        "attack_count": attack_count,
                        "potion_count": potion_count,
                        "attack_rate": _safe_rate(attack_count, support),
                        "potion_rate": _safe_rate(potion_count, support),
                        "dominant_action": dominant_action,
                    }
                )
            consistency_examples.sort(
                key=lambda item: (
                    item["consistency"],
                    -item["support_turns"],
                    item["decision_key"],
                )
            )
            consistency_value = (
                consistency_total / consistency_weight if consistency_weight else 0.0
            )
            consistency_scores.append((consistency_value, consistency_weight))

            position_weight = 0
            position_total = 0.0
            shared_buckets = 0
            position_examples = []
            for shared_state_key, states in by_shared_state.items():
                first_counts = states["first"]
                second_counts = states["second"]
                first_support = sum(first_counts.values())
                second_support = sum(second_counts.values())
                if (
                    first_support < POSITION_DELTA_MIN_SUPPORT_PER_POSITION
                    or second_support < POSITION_DELTA_MIN_SUPPORT_PER_POSITION
                ):
                    continue
                shared_buckets += 1
                weight = first_support + second_support
                first_attack_rate = _safe_rate(first_counts.get("ATTACK", 0), first_support)
                second_attack_rate = _safe_rate(second_counts.get("ATTACK", 0), second_support)
                delta = abs(first_attack_rate - second_attack_rate)
                position_weight += weight
                position_total += delta * weight
                position_examples.append(
                    {
                        "shared_state_key": shared_state_key,
                        "delta": delta,
                        "support_turns": weight,
                        "first": {
                            "bucket_key": f"position=first|{shared_state_key}",
                            "attack_rate": first_attack_rate,
                            "potion_rate": _safe_rate(first_counts.get("POTION", 0), first_support),
                            "support_turns": first_support,
                            "source_path": (
                                f"state_metrics.action_by_state.{player}.position=first|{shared_state_key}"
                            ),
                        },
                        "second": {
                            "bucket_key": f"position=second|{shared_state_key}",
                            "attack_rate": second_attack_rate,
                            "potion_rate": _safe_rate(
                                second_counts.get("POTION", 0), second_support
                            ),
                            "support_turns": second_support,
                            "source_path": (
                                f"state_metrics.action_by_state.{player}.position=second|{shared_state_key}"
                            ),
                        },
                    }
                )
            position_examples.sort(
                key=lambda item: (
                    -item["delta"],
                    -item["support_turns"],
                    item["shared_state_key"],
                )
            )
            position_delta_value = position_total / position_weight if position_weight else 0.0
            position_deltas.append((position_delta_value, position_weight))

            risk_band_weight = 0
            risk_band_total = 0.0
            shared_risk_buckets = 0
            risk_band_examples = []
            if risk_config_available:
                for shared_risk_key, states in by_shared_risk.items():
                    first_counts = states["first"]
                    second_counts = states["second"]
                    first_support = sum(first_counts.values())
                    second_support = sum(second_counts.values())
                    if (
                        first_support < RISK_BAND_MIN_SUPPORT
                        or second_support < RISK_BAND_MIN_SUPPORT
                    ):
                        continue
                    shared_risk_buckets += 1
                    weight = first_support + second_support
                    first_attack_rate = _safe_rate(first_counts.get("ATTACK", 0), first_support)
                    second_attack_rate = _safe_rate(second_counts.get("ATTACK", 0), second_support)
                    delta = abs(first_attack_rate - second_attack_rate)
                    risk_band_weight += weight
                    risk_band_total += delta * weight
                    risk_band_examples.append(
                        {
                            "shared_risk_key": shared_risk_key,
                            "delta": delta,
                            "support_turns": weight,
                            "first": {
                                "attack_rate": first_attack_rate,
                                "potion_rate": _safe_rate(
                                    first_counts.get("POTION", 0), first_support
                                ),
                            },
                            "second": {
                                "attack_rate": second_attack_rate,
                                "potion_rate": _safe_rate(
                                    second_counts.get("POTION", 0), second_support
                                ),
                            },
                        }
                    )
                risk_band_examples.sort(
                    key=lambda item: (
                        -item["delta"],
                        -item["support_turns"],
                        item["shared_risk_key"],
                    )
                )
            risk_band_policy_value = risk_band_total / risk_band_weight if risk_band_weight else 0.0
            risk_band_deltas.append((risk_band_policy_value, risk_band_weight))

            action_by_state[player] = {}
            for bucket_key in sorted(by_bucket.keys()):
                counts = by_bucket[bucket_key]
                support = sum(counts.values())
                attack_count = int(counts.get("ATTACK", 0))
                potion_count = int(counts.get("POTION", 0))
                action_by_state[player][bucket_key] = {
                    "support_turns": support,
                    "attack_count": attack_count,
                    "potion_count": potion_count,
                    "attack_rate": _safe_rate(attack_count, support),
                    "potion_rate": _safe_rate(potion_count, support),
                }

            action_by_risk_band[player] = {}
            if risk_config_available:
                for bucket_key in sorted(by_risk_bucket.keys()):
                    counts = by_risk_bucket[bucket_key]
                    support = sum(counts.values())
                    attack_count = int(counts.get("ATTACK", 0))
                    potion_count = int(counts.get("POTION", 0))
                    action_by_risk_band[player][bucket_key] = {
                        "support_turns": support,
                        "attack_count": attack_count,
                        "potion_count": potion_count,
                        "attack_rate": _safe_rate(attack_count, support),
                        "potion_rate": _safe_rate(potion_count, support),
                    }

            lethal_support = lethal_potions = lethal_attacks = 0
            danger_support = danger_potions = danger_attacks = 0
            safe_support = safe_potions = 0
            lower_danger_support = lower_danger_potions = 0
            upper_danger_support = upper_danger_potions = 0
            scarcity_summary: DefaultDict[str, Dict[str, int]] = defaultdict(
                lambda: {"support_turns": 0, "potion_turns": 0}
            )
            if risk_config_available:
                for turn in player_turn_list:
                    if turn["own_potions"] <= 0:
                        continue
                    band = str(turn["risk_band"])
                    scarcity = _scarcity_bucket(int(turn["own_potions"]))
                    if scarcity is not None:
                        scarcity_key = _risk_scarcity_key(band, scarcity)
                        scarcity_summary[scarcity_key]["support_turns"] += 1
                        if turn["action"] == "POTION":
                            scarcity_summary[scarcity_key]["potion_turns"] += 1
                    if band == "lethal":
                        lethal_support += 1
                        if turn["action"] == "POTION":
                            lethal_potions += 1
                        if turn["action"] == "ATTACK":
                            lethal_attacks += 1
                    elif band == "danger":
                        danger_support += 1
                        if turn["action"] == "POTION":
                            danger_potions += 1
                        if turn["action"] == "ATTACK":
                            danger_attacks += 1
                        if danger_split_available:
                            subband = _danger_subband(
                                own_hp=int(turn["own_hp"]),
                                min_attack_damage=int(min_attack_damage),
                                max_attack_damage=int(max_attack_damage),
                                potion_heal=int(potion_heal),
                            )
                            if subband == "lower":
                                lower_danger_support += 1
                                if turn["action"] == "POTION":
                                    lower_danger_potions += 1
                            elif subband == "upper":
                                upper_danger_support += 1
                                if turn["action"] == "POTION":
                                    upper_danger_potions += 1
                    elif band == "safe":
                        safe_support += 1
                        if turn["action"] == "POTION":
                            safe_potions += 1

            safe_potion_support += safe_support
            safe_potion_hits += safe_potions
            lethal_potion_support += lethal_support
            lethal_potion_hits += lethal_potions
            lethal_attack_support += lethal_support
            lethal_attack_hits += lethal_attacks
            danger_potion_support += danger_support
            danger_potion_hits += danger_potions
            danger_attack_support += danger_support
            danger_attack_hits += danger_attacks
            lower_danger_potion_support += lower_danger_support
            lower_danger_potion_hits += lower_danger_potions
            upper_danger_potion_support += upper_danger_support
            upper_danger_potion_hits += upper_danger_potions
            for key, counts in scarcity_summary.items():
                scarcity_aggregate[key]["support_turns"] += counts["support_turns"]
                scarcity_aggregate[key]["potion_turns"] += counts["potion_turns"]

            if high_roll_config_available and "high_roll_recovery_rate" not in unsupported_metrics:
                player_shocks = sorted(
                    shocks_by_player.get(player, []),
                    key=lambda item: (item["match_id"], item["shock_turn_number"]),
                )
                recovered = 0
                eligible = 0
                for shock in player_shocks:
                    for next_turn in player_turn_list:
                        if next_turn["match_id"] != shock["match_id"]:
                            continue
                        if next_turn["turn_number"] <= shock["shock_turn_number"]:
                            continue
                        next_band = str(
                            next_turn.get("risk_band")
                            or _risk_band(
                                own_hp=next_turn["own_hp"],
                                max_attack_damage=int(max_attack_damage),
                                potion_heal=int(potion_heal),
                            )
                        )
                        if next_band == "safe":
                            break
                        if next_band in {"lethal", "danger"}:
                            eligible += 1
                            if next_turn["action"] == "POTION":
                                recovered += 1
                            break
                high_roll_support += eligible
                high_roll_hits += recovered
                high_roll_entry: Dict[str, Any] | None = {
                    "value": _safe_rate(recovered, eligible),
                    "recovered_events": recovered,
                    "support_events": eligible,
                    "shock_events": len(player_shocks),
                    "high_roll_min_damage": _top_half_min_damage(
                        int(min_attack_damage), int(max_attack_damage)
                    ),
                }
            else:
                high_roll_entry = None

            if max_health is not None:
                potion_turns = [turn for turn in player_turn_list if turn["action"] == "POTION"]
                potion_support = len(potion_turns)
                wasted_hits = sum(1 for turn in potion_turns if turn["own_hp"] == int(max_health))
                wasted_full_health_support += potion_support
                wasted_full_health_hits += wasted_hits
                wasted_entry: Dict[str, Any] | None = {
                    "value": _safe_rate(wasted_hits, potion_support),
                    "wasted_full_health_potions": wasted_hits,
                    "support_potions": potion_support,
                    "max_health": int(max_health),
                }
            else:
                wasted_entry = None

            if risk_config_available:
                scarcity_entries: Dict[str, Any] = {}
                for key in sorted(scarcity_summary.keys()):
                    support = int(scarcity_summary[key]["support_turns"])
                    if support < RISK_BAND_MIN_SUPPORT:
                        continue
                    potions = int(scarcity_summary[key]["potion_turns"])
                    scarcity_entries[key] = {
                        "value": _safe_rate(potions, support),
                        "potion_turns": potions,
                        "support_turns": support,
                    }
                scarcity_entry: Dict[str, Any] | None = {"entries": scarcity_entries}
            else:
                scarcity_entry = None

            player_entry: Dict[str, Any] = {
                "matches_played": match_support,
                "all_attack_match_rate": {
                    "value": all_attack_rate,
                    "all_attack_matches": all_attack_matches[player],
                    "support_matches": match_support,
                },
                "first_potion_profile": {
                    "median_first_potion_hp": (
                        float(median(potion_values)) if potion_values else None
                    ),
                    "first_potion_hp_values": potion_values,
                    "never_used_rate": never_used_rate,
                    "never_used_matches": never_used_matches[player],
                    "support_matches": match_support,
                },
                "first_lethal_entry_inventory": (
                    {
                        "median_potions_on_first_lethal_entry": (
                            float(median(lethal_entry_values)) if lethal_entry_values else None
                        ),
                        "first_lethal_entry_potion_values": lethal_entry_values,
                        "zero_potions_rate": _safe_rate(
                            first_lethal_zero_matches[player],
                            len(lethal_entry_values),
                        ),
                        "zero_potions_matches": first_lethal_zero_matches[player],
                        "support_matches": len(lethal_entry_values),
                        "never_entered_rate": _safe_rate(
                            never_entered_lethal_matches[player],
                            match_support,
                        ),
                        "never_entered_matches": never_entered_lethal_matches[player],
                        "total_matches": match_support,
                    }
                    if max_attack_damage is not None
                    else None
                ),
                "unused_potions_on_loss_rate": {
                    "value": unused_loss_rate,
                    "losses_with_unused_potions": losses_with_unused_potions[player],
                    "support_losses": decisive_losses[player],
                },
                "state_action_consistency": {
                    "value": consistency_value,
                    "supported_state_keys": supported_keys,
                    "support_turns": consistency_weight,
                },
                "position_policy_delta": {
                    "value": position_delta_value,
                    "shared_state_buckets": shared_buckets,
                    "support_turns": position_weight,
                },
                "lethal_zone_potion_rate": (
                    {
                        "value": _safe_rate(lethal_potions, lethal_support),
                        "potion_turns": lethal_potions,
                        "support_turns": lethal_support,
                    }
                    if risk_config_available
                    else None
                ),
                "safe_zone_potion_rate": (
                    {
                        "value": _safe_rate(safe_potions, safe_support),
                        "potion_turns": safe_potions,
                        "support_turns": safe_support,
                    }
                    if risk_config_available
                    else None
                ),
                "danger_zone_potion_rate": (
                    {
                        "value": _safe_rate(danger_potions, danger_support),
                        "potion_turns": danger_potions,
                        "support_turns": danger_support,
                    }
                    if risk_config_available
                    else None
                ),
                "lower_danger_zone_potion_rate": (
                    {
                        "value": _safe_rate(lower_danger_potions, lower_danger_support),
                        "potion_turns": lower_danger_potions,
                        "support_turns": lower_danger_support,
                        "danger_split_hp": _danger_split_hp(
                            min_attack_damage=int(min_attack_damage),
                            max_attack_damage=int(max_attack_damage),
                            potion_heal=int(potion_heal),
                        ),
                    }
                    if danger_split_available
                    else None
                ),
                "upper_danger_zone_potion_rate": (
                    {
                        "value": _safe_rate(upper_danger_potions, upper_danger_support),
                        "potion_turns": upper_danger_potions,
                        "support_turns": upper_danger_support,
                        "danger_split_hp": _danger_split_hp(
                            min_attack_damage=int(min_attack_damage),
                            max_attack_damage=int(max_attack_damage),
                            potion_heal=int(potion_heal),
                        ),
                    }
                    if danger_split_available
                    else None
                ),
                "lethal_zone_attack_rate": (
                    {
                        "value": _safe_rate(lethal_attacks, lethal_support),
                        "attack_turns": lethal_attacks,
                        "support_turns": lethal_support,
                    }
                    if risk_config_available
                    else None
                ),
                "danger_zone_attack_rate": (
                    {
                        "value": _safe_rate(danger_attacks, danger_support),
                        "attack_turns": danger_attacks,
                        "support_turns": danger_support,
                    }
                    if risk_config_available
                    else None
                ),
                "risk_band_potion_rate_by_scarcity": scarcity_entry,
                "risk_band_policy_delta": (
                    {
                        "value": risk_band_policy_value,
                        "shared_risk_buckets": shared_risk_buckets,
                        "support_turns": risk_band_weight,
                    }
                    if risk_config_available
                    else None
                ),
                "high_roll_recovery_rate": high_roll_entry,
                "wasted_full_health_potion_rate": wasted_entry,
            }

            evidence_per_player[player] = {
                "position_policy_delta": {"examples": position_examples[:EVIDENCE_MAX_EXAMPLES]},
                "state_action_consistency": {
                    "examples": consistency_examples[:EVIDENCE_MAX_EXAMPLES]
                },
                "risk_band_policy_delta": {"examples": risk_band_examples[:EVIDENCE_MAX_EXAMPLES]},
            }

            per_player_results[player] = player_entry

        aggregate_metrics: Dict[str, Any] = {
            "all_attack_match_rate": {
                "value": _safe_rate(all_attack_hits, all_attack_support),
                "all_attack_matches": all_attack_hits,
                "support_matches": all_attack_support,
            },
            "first_potion_profile": {
                "median_first_potion_hp": (
                    float(median(first_potion_all_values)) if first_potion_all_values else None
                ),
                "first_potion_hp_values": sorted(first_potion_all_values),
                "never_used_rate": _safe_rate(never_used_hits, never_used_support),
                "never_used_matches": never_used_hits,
                "support_matches": never_used_support,
            },
            "first_lethal_entry_inventory": (
                {
                    "median_potions_on_first_lethal_entry": (
                        float(median(sorted(first_lethal_all_values)))
                        if first_lethal_all_values
                        else None
                    ),
                    "first_lethal_entry_potion_values": sorted(first_lethal_all_values),
                    "zero_potions_rate": _safe_rate(first_lethal_zero_hits, first_lethal_support),
                    "zero_potions_matches": first_lethal_zero_hits,
                    "support_matches": first_lethal_support,
                    "never_entered_rate": _safe_rate(
                        first_lethal_never_entered_hits,
                        first_lethal_never_entered_support,
                    ),
                    "never_entered_matches": first_lethal_never_entered_hits,
                    "total_matches": first_lethal_never_entered_support,
                }
                if max_attack_damage is not None
                else None
            ),
            "unused_potions_on_loss_rate": {
                "value": _safe_rate(unused_loss_hits, unused_loss_support),
                "losses_with_unused_potions": unused_loss_hits,
                "support_losses": unused_loss_support,
            },
            "state_action_consistency": {
                "value": _safe_rate(
                    sum(score * weight for score, weight in consistency_scores),
                    sum(weight for _, weight in consistency_scores),
                ),
                "support_turns": sum(weight for _, weight in consistency_scores),
            },
            "position_policy_delta": {
                "value": _safe_rate(
                    sum(score * weight for score, weight in position_deltas),
                    sum(weight for _, weight in position_deltas),
                ),
                "support_turns": sum(weight for _, weight in position_deltas),
            },
            "safe_zone_potion_rate": (
                {
                    "value": _safe_rate(safe_potion_hits, safe_potion_support),
                    "potion_turns": safe_potion_hits,
                    "support_turns": safe_potion_support,
                }
                if risk_config_available
                else None
            ),
            "lethal_zone_potion_rate": (
                {
                    "value": _safe_rate(lethal_potion_hits, lethal_potion_support),
                    "potion_turns": lethal_potion_hits,
                    "support_turns": lethal_potion_support,
                }
                if risk_config_available
                else None
            ),
            "danger_zone_potion_rate": (
                {
                    "value": _safe_rate(danger_potion_hits, danger_potion_support),
                    "potion_turns": danger_potion_hits,
                    "support_turns": danger_potion_support,
                }
                if risk_config_available
                else None
            ),
            "lower_danger_zone_potion_rate": (
                {
                    "value": _safe_rate(lower_danger_potion_hits, lower_danger_potion_support),
                    "potion_turns": lower_danger_potion_hits,
                    "support_turns": lower_danger_potion_support,
                    "danger_split_hp": _danger_split_hp(
                        min_attack_damage=int(min_attack_damage),
                        max_attack_damage=int(max_attack_damage),
                        potion_heal=int(potion_heal),
                    ),
                }
                if danger_split_available
                else None
            ),
            "upper_danger_zone_potion_rate": (
                {
                    "value": _safe_rate(upper_danger_potion_hits, upper_danger_potion_support),
                    "potion_turns": upper_danger_potion_hits,
                    "support_turns": upper_danger_potion_support,
                    "danger_split_hp": _danger_split_hp(
                        min_attack_damage=int(min_attack_damage),
                        max_attack_damage=int(max_attack_damage),
                        potion_heal=int(potion_heal),
                    ),
                }
                if danger_split_available
                else None
            ),
            "lethal_zone_attack_rate": (
                {
                    "value": _safe_rate(lethal_attack_hits, lethal_attack_support),
                    "attack_turns": lethal_attack_hits,
                    "support_turns": lethal_attack_support,
                }
                if risk_config_available
                else None
            ),
            "danger_zone_attack_rate": (
                {
                    "value": _safe_rate(danger_attack_hits, danger_attack_support),
                    "attack_turns": danger_attack_hits,
                    "support_turns": danger_attack_support,
                }
                if risk_config_available
                else None
            ),
            "risk_band_potion_rate_by_scarcity": (
                {
                    "entries": {
                        key: {
                            "value": _safe_rate(counts["potion_turns"], counts["support_turns"]),
                            "potion_turns": counts["potion_turns"],
                            "support_turns": counts["support_turns"],
                        }
                        for key, counts in sorted(scarcity_aggregate.items())
                        if counts["support_turns"] >= RISK_BAND_MIN_SUPPORT
                    }
                }
                if risk_config_available
                else None
            ),
            "risk_band_policy_delta": (
                {
                    "value": _safe_rate(
                        sum(score * weight for score, weight in risk_band_deltas),
                        sum(weight for _, weight in risk_band_deltas),
                    ),
                    "support_turns": sum(weight for _, weight in risk_band_deltas),
                }
                if risk_config_available
                else None
            ),
            "high_roll_recovery_rate": (
                {
                    "value": _safe_rate(high_roll_hits, high_roll_support),
                    "recovered_events": high_roll_hits,
                    "support_events": high_roll_support,
                    "high_roll_min_damage": _top_half_min_damage(
                        int(min_attack_damage), int(max_attack_damage)
                    ),
                }
                if high_roll_config_available
                and "high_roll_recovery_rate" not in unsupported_metrics
                else None
            ),
            "wasted_full_health_potion_rate": (
                {
                    "value": _safe_rate(wasted_full_health_hits, wasted_full_health_support),
                    "wasted_full_health_potions": wasted_full_health_hits,
                    "support_potions": wasted_full_health_support,
                    "max_health": int(max_health),
                }
                if max_health is not None
                else None
            ),
        }

        return {
            "schema_version": 2,
            "game_id": self.game_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "coverage": {
                "matches_total": matches_total,
                "matches_evaluable": matches_evaluable,
                "turns_total": turns_total,
                "turns_evaluable": turns_evaluable,
            },
            "aggregate_metrics": aggregate_metrics,
            "per_player": per_player_results,
            "state_metrics": {
                "action_by_state": action_by_state,
                "action_by_risk_band": action_by_risk_band,
            },
            "evidence": {
                "aggregate_metrics": {},
                "per_player": evidence_per_player,
                "state_metrics": {},
            },
            "quality_flags": {
                "complete": not unsupported_metrics,
                "unsupported_metrics": sorted(unsupported_metrics),
            },
        }


__all__ = [
    "CONSISTENCY_MIN_SUPPORT",
    "EVIDENCE_MAX_EXAMPLES",
    "POSITION_DELTA_MIN_SUPPORT_PER_POSITION",
    "RISK_BAND_MIN_SUPPORT",
    "RISK_BANDS",
    "VariableDamageBehavioralScorer",
]
