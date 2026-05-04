from __future__ import annotations

import csv
from pathlib import Path

from nwsl_graph.models import Match


def load_matches_csv(path: str | Path) -> list[Match]:
    p = Path(path)
    out: list[Match] = []
    with p.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        for i, row in enumerate(reader):
            home = (row.get("home") or "").strip()
            away = (row.get("away") or "").strip()
            hg = int(row.get("home_goals") or row.get("hg") or 0)
            ag = int(row.get("away_goals") or row.get("ag") or 0)
            out.append(
                Match(
                    event_id=f"csv-{i}",
                    date_utc=None,
                    home=home,
                    away=away,
                    home_goals=hg,
                    away_goals=ag,
                )
            )
    return out
