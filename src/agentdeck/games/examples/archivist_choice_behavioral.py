"""Deterministic behavioral scoring for ArchivistChoiceGame recordings."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, DefaultDict, Dict, Iterable, List, Mapping, Optional

from agentdeck.research.behavioral import BehavioralScorer


def _game_name(payload: Mapping[str, Any]) -> str | None:
    direct = payload.get("game")
    if isinstance(direct, str) and direct:
        return direct
    metadata = payload.get("metadata") or {}
    if not isinstance(metadata, Mapping):
        return None
    value = metadata.get("game")
    if isinstance(value, str) and value:
        return value
    match = metadata.get("match") or {}
    if isinstance(match, Mapping):
        value = match.get("game")
        if isinstance(value, Mapping):
            value = value.get("name")
        if value:
            return str(value)
    return None


def _mean(values: List[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)


class ArchivistChoiceBehavioralScorer(BehavioralScorer):
    """Score recorded Archivist choices without treating answer keys as prompts."""

    game_id = "archivist_choice"
    profile_id = "archivist_choice_behavioral"
    profile_version = "0.1.0"

    def supports(self, *, match_payloads: Iterable[Mapping[str, Any]]) -> bool:
        names = set()
        for payload in match_payloads:
            if not isinstance(payload, Mapping):
                return False
            name = _game_name(payload)
            if not name:
                return False
            names.add(name)
        return bool(names) and names == {"ArchivistChoiceGame"}

    def score(
        self,
        *,
        players: List[Mapping[str, Any]],
        match_payloads: Iterable[Mapping[str, Any]],
        config: Optional[Mapping[str, Any]] = None,
    ) -> Dict[str, Any]:
        del config
        roster = [str(player["name"]) for player in players if player.get("name")]
        if not roster:
            raise ValueError("Behavioral scoring requires player metadata with names")

        player_set = set(roster)
        match_list = list(match_payloads)
        matches_evaluable = 0
        turns_total = 0
        turns_evaluable = 0
        unsupported = set()

        final_scores: DefaultDict[str, List[float]] = defaultdict(list)
        processed_counts: DefaultDict[str, List[float]] = defaultdict(list)
        best_action_hits: DefaultDict[str, int] = defaultdict(int)
        best_action_totals: DefaultDict[str, int] = defaultdict(int)
        score_delta_sums: DefaultDict[str, float] = defaultdict(float)
        score_delta_totals: DefaultDict[str, int] = defaultdict(int)
        observed_matches: DefaultDict[str, int] = defaultdict(int)
        manuscript_metrics: DefaultDict[str, Dict[str, float]] = defaultdict(
            lambda: {
                "processed_cases": 0.0,
                "best_action_hits": 0.0,
                "best_action_total": 0.0,
                "score_delta_sum": 0.0,
                "score_delta_total": 0.0,
            }
        )

        for payload in match_list:
            if _game_name(payload) != "ArchivistChoiceGame":
                raise ValueError(
                    "ArchivistChoiceBehavioralScorer only supports ArchivistChoiceGame payloads"
                )

            metadata = payload.get("metadata") or {}
            match_meta = metadata.get("match") if isinstance(metadata, Mapping) else {}
            match_players = payload.get("players") or (
                match_meta.get("players") if isinstance(match_meta, Mapping) else []
            )
            if not isinstance(match_players, list) or not match_players:
                raise ValueError("Archivist Choice behavioral scoring requires match players")
            names = [str(name) for name in match_players]
            unknown = sorted(set(names) - player_set)
            if unknown:
                raise ValueError(f"Unknown players in Archivist Choice payload: {unknown}")

            events = payload.get("events") or []
            turns_total += sum(
                1 for event in events if isinstance(event, Mapping) and event.get("type") == "gameplay"
            )

            final_state = payload.get("final_state")
            if not isinstance(final_state, Mapping):
                unsupported.add("final_state")
                continue
            scores = final_state.get("scores")
            processed = final_state.get("processed")
            if not isinstance(scores, Mapping) or not isinstance(processed, Mapping):
                unsupported.add("final_state")
                continue
            if any(not isinstance(scores.get(name), (int, float)) for name in names):
                unsupported.add("mean_final_score")
                continue
            if any(not isinstance(processed.get(name), list) for name in names):
                unsupported.add("mean_processed_cases")
                continue

            matches_evaluable += 1
            for name in names:
                entries = processed[name]
                final_scores[name].append(float(scores[name]))
                processed_counts[name].append(float(len(entries)))
                observed_matches[name] += 1
                for entry in entries:
                    if not isinstance(entry, Mapping):
                        unsupported.add("processed_case")
                        continue
                    manuscript_id = entry.get("manuscript_id")
                    if not isinstance(manuscript_id, str) or not manuscript_id:
                        unsupported.add("manuscript_id")
                        continue
                    metrics = manuscript_metrics[manuscript_id]
                    metrics["processed_cases"] += 1
                    action = entry.get("action")
                    best_action = entry.get("best_action")
                    if isinstance(action, str) and isinstance(best_action, str):
                        best_action_totals[name] += 1
                        metrics["best_action_total"] += 1
                        if action == best_action:
                            best_action_hits[name] += 1
                            metrics["best_action_hits"] += 1
                    else:
                        unsupported.add("best_action_rate")
                    score_delta = entry.get("score_delta")
                    if isinstance(score_delta, (int, float)) and not isinstance(score_delta, bool):
                        score_delta_sums[name] += float(score_delta)
                        score_delta_totals[name] += 1
                        metrics["score_delta_sum"] += float(score_delta)
                        metrics["score_delta_total"] += 1
                    else:
                        unsupported.add("mean_score_delta_per_processed_case")
                    if (
                        isinstance(action, str)
                        and isinstance(best_action, str)
                        and isinstance(score_delta, (int, float))
                        and not isinstance(score_delta, bool)
                    ):
                        turns_evaluable += 1

        per_player: Dict[str, Dict[str, float | None]] = {}
        evidence_per_player: Dict[str, Dict[str, Dict[str, float | int]]] = {}
        for name in roster:
            final_score = _mean(final_scores[name])
            processed_cases = _mean(processed_counts[name])
            action_total = best_action_totals[name]
            delta_total = score_delta_totals[name]
            if final_score is None:
                unsupported.add("mean_final_score")
            if processed_cases is None:
                unsupported.add("mean_processed_cases")
            if action_total == 0:
                unsupported.add("best_action_rate")
            if delta_total == 0:
                unsupported.add("mean_score_delta_per_processed_case")
            per_player[name] = {
                "mean_final_score": final_score,
                "mean_processed_cases": processed_cases,
                "best_action_rate": (
                    best_action_hits[name] / action_total if action_total else None
                ),
                "mean_score_delta_per_processed_case": (
                    score_delta_sums[name] / delta_total if delta_total else None
                ),
            }
            evidence_per_player[name] = {
                "mean_final_score": {
                    "sum": sum(final_scores[name]),
                    "denominator": len(final_scores[name]),
                    "observed_matches": observed_matches[name],
                },
                "mean_processed_cases": {
                    "sum": sum(processed_counts[name]),
                    "denominator": len(processed_counts[name]),
                    "observed_matches": observed_matches[name],
                },
                "best_action_rate": {
                    "numerator": best_action_hits[name],
                    "denominator": action_total,
                },
                "mean_score_delta_per_processed_case": {
                    "sum": score_delta_sums[name],
                    "denominator": delta_total,
                },
            }

        by_manuscript: Dict[str, Dict[str, float | int | None]] = {}
        evidence_by_manuscript: Dict[str, Dict[str, float | int]] = {}
        for manuscript_id in sorted(manuscript_metrics):
            metrics = manuscript_metrics[manuscript_id]
            action_total = int(metrics["best_action_total"])
            delta_total = int(metrics["score_delta_total"])
            if action_total == 0:
                unsupported.add("best_action_rate")
            if delta_total == 0:
                unsupported.add("mean_score_delta_per_processed_case")
            by_manuscript[manuscript_id] = {
                "processed_cases": int(metrics["processed_cases"]),
                "best_action_rate": metrics["best_action_hits"] / action_total if action_total else None,
                "mean_score_delta": metrics["score_delta_sum"] / delta_total if delta_total else None,
            }
            evidence_by_manuscript[manuscript_id] = {
                "best_action_numerator": int(metrics["best_action_hits"]),
                "best_action_denominator": action_total,
                "score_delta_sum": metrics["score_delta_sum"],
                "score_delta_denominator": delta_total,
            }

        return {
            "schema_version": 2,
            "game_id": self.game_id,
            "profile_id": self.profile_id,
            "profile_version": self.profile_version,
            "coverage": {
                "matches_total": len(match_list),
                "matches_evaluable": matches_evaluable,
                "turns_total": turns_total,
                "turns_evaluable": turns_evaluable,
            },
            "aggregate_metrics": {},
            "per_player": per_player,
            "state_metrics": {"by_manuscript": by_manuscript},
            "evidence": {
                "aggregate_metrics": {},
                "per_player": evidence_per_player,
                "state_metrics": {"by_manuscript": evidence_by_manuscript},
            },
            "quality_flags": {
                "complete": not unsupported,
                "unsupported_metrics": sorted(unsupported),
            },
        }


__all__ = ["ArchivistChoiceBehavioralScorer"]
