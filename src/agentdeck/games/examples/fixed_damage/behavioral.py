"""FixedDamage behavioral scorer."""

from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any, DefaultDict, Dict, Iterable, List, Mapping, Optional, Tuple

from agentdeck.research.behavioral import BehavioralScorer


CONSISTENCY_MIN_SUPPORT = 2
POSITION_DELTA_MIN_SUPPORT_PER_POSITION = 2
SCARCITY_BUCKETS = (0, 1, 2, 3)
CRITICAL_POTION_HP_MULTIPLIER = 2


NormalizedTurn = Dict[str, Any]


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _bucket_key(position: str, own_hp: int, own_potions: int) -> str:
    return f"position={position}|hp={own_hp}|potions={own_potions}"


def _shared_state_key(own_hp: int, own_potions: int) -> str:
    return f"hp={own_hp}|potions={own_potions}"


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


class FixedDamageBehavioralScorer(BehavioralScorer):
    game_id = "fixed_damage"
    profile_id = "fixed_damage_behavioral"
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
        return bool(names) and names == {"FixedDamageGame"}

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

        config_map = dict(config or {})
        attack_damage = config_map.get("attack_damage")
        max_health = config_map.get("max_health")

        unsupported_metrics = set()
        if attack_damage is None:
            unsupported_metrics.update(
                {"critical_potion_response_rate", "error_recovery_rate"}
            )
        if max_health is None:
            unsupported_metrics.add("wasted_full_health_potion_rate")

        player_names = {name for name in roster}
        match_list = list(match_payloads)
        turns: List[NormalizedTurn] = []
        matches_total = len(match_list)
        matches_evaluable = 0

        matches_played = Counter()
        all_attack_matches = Counter()
        first_potion_values: DefaultDict[str, List[int]] = defaultdict(list)
        never_used_matches = Counter()
        decisive_losses = Counter()
        losses_with_unused_potions = Counter()
        per_player_turns: DefaultDict[str, List[NormalizedTurn]] = defaultdict(list)

        for payload in match_list:
            if _game_name(payload) != "FixedDamageGame":
                raise ValueError("FixedDamageBehavioralScorer only supports FixedDamageGame payloads")

            match_id = str(payload.get("match_id") or "")
            if not match_id:
                raise ValueError("Missing match_id in behavioral payload")

            metadata = payload.get("metadata") or {}
            match_meta = metadata.get("match") or {}
            match_players = [str(name) for name in (payload.get("players") or match_meta.get("players") or [])]
            if len(match_players) != 2:
                raise ValueError("FixedDamage behavioral scoring requires exactly two players per match")
            unknown = sorted(set(match_players) - player_names)
            if unknown:
                raise ValueError(f"Unknown players in match payload: {unknown}")

            first_player = ((match_meta.get("first_player") or {}).get("name"))
            if not first_player:
                raise ValueError("Missing first_player metadata for behavioral scoring")
            first_player = str(first_player)
            if first_player not in match_players:
                raise ValueError(f"first_player '{first_player}' not present in match players")

            second_player = next(name for name in match_players if name != first_player)
            position_by_player = {first_player: "first", second_player: "second"}

            gameplay_events = [
                event
                for event in (payload.get("events") or [])
                if event.get("type") == "gameplay"
            ]
            if gameplay_events:
                matches_evaluable += 1

            match_turns_by_player: DefaultDict[str, List[NormalizedTurn]] = defaultdict(list)

            for player in match_players:
                matches_played[player] += 1

            for event in gameplay_events:
                event_data = event.get("data") or {}
                player = event_data.get("player")
                if not player:
                    raise ValueError("Gameplay event missing player")
                player = str(player)
                if player not in player_names:
                    raise ValueError(f"Unknown player in gameplay event: {player}")

                state_before = event_data.get("state_before") or {}
                health = state_before.get("health") or {}
                potions = state_before.get("potions") or {}
                last_action = state_before.get("last_action") or {}
                if player not in health or player not in potions:
                    raise ValueError(f"Gameplay state_before missing acting player fields for {player}")

                opponent = next(name for name in match_players if name != player)
                record: NormalizedTurn = {
                    "match_id": match_id,
                    "player": player,
                    "position": position_by_player[player],
                    "turn_number": _extract_turn_number(event_data),
                    "action": str(event_data.get("action") or "").upper(),
                    "own_hp": int(health[player]),
                    "own_potions": int(potions[player]),
                    "last_action_self": last_action.get(player),
                    "last_action_opponent": last_action.get(opponent),
                }
                turns.append(record)
                per_player_turns[player].append(record)
                match_turns_by_player[player].append(record)

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
                    (turn["own_hp"] for turn in player_turns if turn["action"] == "POTION"),
                    None,
                )
                if first_potion is None:
                    never_used_matches[player] += 1
                else:
                    first_potion_values[player].append(int(first_potion))

                if winner is not None and winner != player:
                    decisive_losses[player] += 1
                    if int(final_potions.get(player, 0)) > 0:
                        losses_with_unused_potions[player] += 1

        turns_total = len(turns)
        turns_evaluable = turns_total

        per_player_results: Dict[str, Dict[str, Any]] = {}
        action_by_state: Dict[str, Dict[str, Any]] = {}
        scarcity_profile: Dict[str, Dict[str, Any]] = {}

        consistency_scores: List[Tuple[float, int]] = []
        position_deltas: List[Tuple[float, int]] = []
        all_attack_support = 0
        all_attack_hits = 0
        never_used_support = 0
        never_used_hits = 0
        first_potion_all_values: List[int] = []
        unused_loss_support = 0
        unused_loss_hits = 0
        critical_support = 0
        critical_hits = 0
        recovery_support = 0
        recovery_hits = 0
        wasted_full_health_support = 0
        wasted_full_health_hits = 0

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

            by_decision_key: DefaultDict[str, Counter[str]] = defaultdict(Counter)
            by_shared_state: DefaultDict[str, Dict[str, Counter[str]]] = defaultdict(
                lambda: {"first": Counter(), "second": Counter()}
            )
            by_bucket: DefaultDict[str, Counter[str]] = defaultdict(Counter)
            by_scarcity: DefaultDict[int, Counter[str]] = defaultdict(Counter)

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

                bucket_key = _bucket_key(
                    turn["position"], turn["own_hp"], turn["own_potions"]
                )
                by_bucket[bucket_key][turn["action"]] += 1

                if turn["own_potions"] in SCARCITY_BUCKETS:
                    by_scarcity[int(turn["own_potions"])][turn["action"]] += 1

            consistency_weight = 0
            consistency_total = 0.0
            supported_keys = 0
            for counts in by_decision_key.values():
                support = sum(counts.values())
                if support < CONSISTENCY_MIN_SUPPORT:
                    continue
                supported_keys += 1
                consistency_weight += support
                consistency_total += (max(counts.values()) / support) * support
            consistency_value = (
                consistency_total / consistency_weight if consistency_weight else 0.0
            )
            consistency_scores.append((consistency_value, consistency_weight))

            position_weight = 0
            position_total = 0.0
            shared_buckets = 0
            for states in by_shared_state.values():
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
                second_attack_rate = _safe_rate(
                    second_counts.get("ATTACK", 0), second_support
                )
                position_weight += weight
                position_total += abs(first_attack_rate - second_attack_rate) * weight
            position_delta_value = (
                position_total / position_weight if position_weight else 0.0
            )
            position_deltas.append((position_delta_value, position_weight))

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

            scarcity_profile[player] = {}
            for bucket in SCARCITY_BUCKETS:
                counts = by_scarcity.get(bucket, Counter())
                support = sum(counts.values())
                attack_count = int(counts.get("ATTACK", 0))
                potion_count = int(counts.get("POTION", 0))
                scarcity_profile[player][str(bucket)] = {
                    "support_turns": support,
                    "attack_count": attack_count,
                    "potion_count": potion_count,
                    "attack_rate": _safe_rate(attack_count, support),
                    "potion_rate": _safe_rate(potion_count, support),
                }

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
            }

            if attack_damage is not None:
                critical_threshold = int(CRITICAL_POTION_HP_MULTIPLIER * int(attack_damage))
                critical_turns = [
                    turn
                    for turn in player_turn_list
                    if turn["own_potions"] > 0 and turn["own_hp"] <= critical_threshold
                ]
                critical_turn_support = len(critical_turns)
                critical_turn_hits = sum(
                    1 for turn in critical_turns if turn["action"] == "POTION"
                )
                critical_support += critical_turn_support
                critical_hits += critical_turn_hits
                player_entry["critical_potion_response_rate"] = {
                    "value": _safe_rate(critical_turn_hits, critical_turn_support),
                    "critical_potion_turns": critical_turn_hits,
                    "support_turns": critical_turn_support,
                    "critical_hp_threshold": critical_threshold,
                }

                missed_indices = [
                    index
                    for index, turn in enumerate(player_turn_list)
                    if turn["own_potions"] > 0
                    and turn["own_hp"] <= critical_threshold
                    and turn["action"] == "ATTACK"
                ]
                recovered = 0
                eligible = 0
                for index in missed_indices:
                    for next_turn in player_turn_list[index + 1 :]:
                        if (
                            next_turn["own_potions"] > 0
                            and next_turn["own_hp"] <= critical_threshold
                        ):
                            eligible += 1
                            if next_turn["action"] == "POTION":
                                recovered += 1
                            break
                recovery_support += eligible
                recovery_hits += recovered
                player_entry["error_recovery_rate"] = {
                    "value": _safe_rate(recovered, eligible),
                    "recovered_events": recovered,
                    "support_events": eligible,
                    "missed_events": len(missed_indices),
                    "critical_hp_threshold": critical_threshold,
                }
            else:
                player_entry["critical_potion_response_rate"] = None
                player_entry["error_recovery_rate"] = None

            if max_health is not None:
                potion_turns = [
                    turn for turn in player_turn_list if turn["action"] == "POTION"
                ]
                potion_support = len(potion_turns)
                wasted_hits = sum(
                    1 for turn in potion_turns if turn["own_hp"] == int(max_health)
                )
                wasted_full_health_support += potion_support
                wasted_full_health_hits += wasted_hits
                player_entry["wasted_full_health_potion_rate"] = {
                    "value": _safe_rate(wasted_hits, potion_support),
                    "wasted_full_health_potions": wasted_hits,
                    "support_potions": potion_support,
                    "max_health": int(max_health),
                }
            else:
                player_entry["wasted_full_health_potion_rate"] = None

            per_player_results[player] = player_entry

        aggregate_metrics: Dict[str, Any] = {
            "all_attack_match_rate": {
                "value": _safe_rate(all_attack_hits, all_attack_support),
                "all_attack_matches": all_attack_hits,
                "support_matches": all_attack_support,
            },
            "first_potion_profile": {
                "median_first_potion_hp": (
                    float(median(first_potion_all_values))
                    if first_potion_all_values
                    else None
                ),
                "first_potion_hp_values": sorted(first_potion_all_values),
                "never_used_rate": _safe_rate(never_used_hits, never_used_support),
                "never_used_matches": never_used_hits,
                "support_matches": never_used_support,
            },
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
        }

        if attack_damage is not None:
            critical_threshold = int(CRITICAL_POTION_HP_MULTIPLIER * int(attack_damage))
            aggregate_metrics["critical_potion_response_rate"] = {
                "value": _safe_rate(critical_hits, critical_support),
                "critical_potion_turns": critical_hits,
                "support_turns": critical_support,
                "critical_hp_threshold": critical_threshold,
            }
            aggregate_metrics["error_recovery_rate"] = {
                "value": _safe_rate(recovery_hits, recovery_support),
                "recovered_events": recovery_hits,
                "support_events": recovery_support,
                "critical_hp_threshold": critical_threshold,
            }
        else:
            aggregate_metrics["critical_potion_response_rate"] = None
            aggregate_metrics["error_recovery_rate"] = None

        if max_health is not None:
            aggregate_metrics["wasted_full_health_potion_rate"] = {
                "value": _safe_rate(
                    wasted_full_health_hits, wasted_full_health_support
                ),
                "wasted_full_health_potions": wasted_full_health_hits,
                "support_potions": wasted_full_health_support,
                "max_health": int(max_health),
            }
        else:
            aggregate_metrics["wasted_full_health_potion_rate"] = None

        return {
            "schema_version": 1,
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
                "scarcity_action_profile": scarcity_profile,
            },
            "quality_flags": {
                "complete": not unsupported_metrics,
                "unsupported_metrics": sorted(unsupported_metrics),
            },
        }


__all__ = [
    "CRITICAL_POTION_HP_MULTIPLIER",
    "CONSISTENCY_MIN_SUPPORT",
    "FixedDamageBehavioralScorer",
    "POSITION_DELTA_MIN_SUPPORT_PER_POSITION",
    "SCARCITY_BUCKETS",
]
