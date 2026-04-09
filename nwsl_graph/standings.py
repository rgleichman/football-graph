from __future__ import annotations

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
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against


def compute_standings(matches: list[Match]) -> list[StandingRow]:
    """Aggregate results; sort NWSL-style: points, GD, goals scored."""
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
