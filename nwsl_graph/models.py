from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Match:
    """One completed match with a final score."""

    event_id: str
    home: str
    away: str
    home_goals: int
    away_goals: int

    @property
    def differential(self) -> int:
        return abs(self.home_goals - self.away_goals)

    def is_tie(self) -> bool:
        return self.home_goals == self.away_goals
