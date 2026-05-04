from __future__ import annotations

import math
from dataclasses import dataclass

from nwsl_graph.models import Match


@dataclass(frozen=True)
class StandingRow:
    team: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int

    @property
    def points(self) -> float:
        # Normalized scoring: (win +1, loss -1, draw 0) per match played
        if self.played <= 0:
            return 0.0
        return float(self.wins - self.losses) / float(self.played)

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def compute_standings(matches: list[Match]) -> list[StandingRow]:
    """Aggregate results; sort by normalized points, then GD, then goals scored."""
    stats: dict[str, dict[str, int]] = {}

    def bump(team: str) -> dict[str, int]:
        if team not in stats:
            stats[team] = {
                "p": 0,
                "w": 0,
                "d": 0,
                "l": 0,
                "gf": 0,
                "ga": 0,
            }
        return stats[team]

    for m in matches:
        h = bump(m.home)
        a = bump(m.away)
        h["gf"] += m.home_goals
        h["ga"] += m.away_goals
        a["gf"] += m.away_goals
        a["ga"] += m.home_goals
        h["p"] += 1
        a["p"] += 1
        if m.is_tie():
            h["d"] += 1
            a["d"] += 1
        elif m.home_goals > m.away_goals:
            h["w"] += 1
            a["l"] += 1
        else:
            a["w"] += 1
            h["l"] += 1

    rows: list[StandingRow] = []
    for team, s in stats.items():
        rows.append(
            StandingRow(
                team=team,
                played=s["p"],
                wins=s["w"],
                draws=s["d"],
                losses=s["l"],
                goals_for=s["gf"],
                goals_against=s["ga"],
            )
        )

    rows.sort(
        key=lambda r: (r.points, r.goal_difference, r.goals_for),
        reverse=True,
    )
    return rows


def compute_elo_ratings(
    matches: list[Match],
    *,
    initial_rating: float = 1500.0,
    k_factor: float = 20.0,
) -> dict[str, float]:
    """
    Compute final ELO ratings for all teams appearing in matches.

    Assumptions:
    - Matches are provided in the desired chronological order.
    - No home advantage.
    """
    teams: set[str] = set()
    matches_sorted = sorted(
        matches,
        key=lambda m: (
            m.date_utc is None,
            m.date_utc,
            m.event_id,
        ),
    )

    for m in matches_sorted:
        teams.add(m.home)
        teams.add(m.away)

    ratings: dict[str, float] = {t: float(initial_rating) for t in teams}

    def expected(ra: float, rb: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (rb - ra) / 400.0))

    for m in matches_sorted:
        rh = ratings[m.home]
        ra = ratings[m.away]

        eh = expected(rh, ra)
        ea = 1.0 - eh

        if m.is_tie():
            sh, sa = 0.5, 0.5
        elif m.home_goals > m.away_goals:
            sh, sa = 1.0, 0.0
        else:
            sh, sa = 0.0, 1.0

        ratings[m.home] = rh + k_factor * (sh - eh)
        ratings[m.away] = ra + k_factor * (sa - ea)

    return ratings


def normalize_scores(scores: dict[str, float]) -> dict[str, float]:
    """Normalize arbitrary team scores into 0..1 range (stable on ties)."""
    if not scores:
        return {}
    vals = list(scores.values())
    lo = min(vals)
    hi = max(vals)
    if hi <= lo:
        return {t: 0.0 for t in scores}
    denom = hi - lo
    return {t: (v - lo) / denom for t, v in scores.items()}
