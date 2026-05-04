from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from nwsl_graph.models import Match

_FINAL_NAMES = frozenset({"STATUS_FULL_TIME", "STATUS_FINAL"})


def parse_scoreboard_payload(data: dict[str, Any]) -> list[Match]:
    """Parse ESPN site API scoreboard JSON into normalized matches."""
    out: list[Match] = []
    for event in data.get("events") or []:
        m = _parse_event(event)
        if m is not None:
            out.append(m)
    return out


def load_matches_from_json_file(path: str) -> list[Match]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        # Array of raw events
        return [m for e in data if (m := _parse_event(e)) is not None]
    return parse_scoreboard_payload(data)


def _parse_event(event: dict[str, Any]) -> Match | None:
    eid = str(event.get("id", ""))
    comps = event.get("competitions") or []
    if not comps:
        return None
    comp = comps[0]
    dt_utc = _parse_competition_date_utc(comp)
    status = (comp.get("status") or {}).get("type") or {}
    name = status.get("name") or ""
    completed = bool(status.get("completed"))
    if name not in _FINAL_NAMES and not (completed and "FULL" in name.upper()):
        return None
    if not completed and name not in _FINAL_NAMES:
        return None

    teams: dict[str, dict[str, Any]] = {}
    for c in comp.get("competitors") or []:
        ha = c.get("homeAway")
        if ha not in ("home", "away"):
            continue
        teams[ha] = c

    if "home" not in teams or "away" not in teams:
        return None

    home_name = _team_name(teams["home"])
    away_name = _team_name(teams["away"])
    hg = _score_value(teams["home"])
    ag = _score_value(teams["away"])
    if hg is None or ag is None:
        return None

    return Match(
        event_id=eid or f"{home_name}-{away_name}-{hg}-{ag}",
        date_utc=dt_utc,
        home=home_name,
        away=away_name,
        home_goals=hg,
        away_goals=ag,
    )


def _parse_competition_date_utc(comp: dict[str, Any]) -> datetime | None:
    s = comp.get("date")
    if not s:
        return None
    try:
        if isinstance(s, str) and s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(str(s))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _team_name(comp: dict[str, Any]) -> str:
    t = comp.get("team") or {}
    return str(t.get("displayName") or t.get("name") or t.get("shortDisplayName") or "")


def _score_value(comp: dict[str, Any]) -> int | None:
    s = comp.get("score")
    if s is None:
        return None
    if isinstance(s, str):
        try:
            return int(s)
        except ValueError:
            return None
    if isinstance(s, (int, float)):
        return int(s)
    if isinstance(s, dict):
        v = s.get("value")
        if v is None and "displayValue" in s:
            try:
                return int(str(s["displayValue"]).split("-")[0])
            except (ValueError, IndexError):
                pass
        try:
            return int(v) if v is not None else None
        except (TypeError, ValueError):
            return None
    return None
