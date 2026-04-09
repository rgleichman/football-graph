from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone
from typing import Any

from nwsl_graph.http_util import get_json
from nwsl_graph.models import Match
from nwsl_graph.parse_espn import parse_scoreboard_payload

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.nwsl/scoreboard"


def _parse_iso_calendar_day(s: str) -> date | None:
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        return dt.astimezone(timezone.utc).date()
    except (ValueError, TypeError):
        return None


def _calendar_range(data: dict[str, Any]) -> tuple[date, date] | None:
    leagues = data.get("leagues") or []
    if not leagues:
        return None
    cal = leagues[0].get("calendar") or []
    days: list[date] = []
    for entry in cal:
        if isinstance(entry, str):
            d = _parse_iso_calendar_day(entry)
            if d:
                days.append(d)
    if not days:
        return None
    return min(days), max(days)


def _season_default_range(season: int) -> tuple[date, date]:
    return date(season, 3, 1), date(season, 11, 30)


def _week_ranges(start: date, end: date, *, span: int = 7) -> list[tuple[date, date]]:
    out: list[tuple[date, date]] = []
    d = start
    while d <= end:
        e = min(d + timedelta(days=span - 1), end)
        out.append((d, e))
        d = e + timedelta(days=1)
    return out


def fetch_season_matches_sync(season: int, *, chunk_days: int = 7, max_workers: int = 8) -> list[Match]:
    # ESPN intermittently returns 500 for season/seasontype parameters here; fall back to base endpoint.
    bootstrap = get_json(SCOREBOARD_URL)
    cr = _calendar_range(bootstrap)
    if cr:
        start, end = cr
    else:
        start, end = _season_default_range(season)

    ranges = _week_ranges(start, end, span=chunk_days)

    def _one(rng: tuple[date, date]) -> dict[str, Any]:
        a, b = rng
        return get_json(
            SCOREBOARD_URL,
            # Note: adding season params currently causes ESPN 500s for NWSL.
            {"dates": f"{a:%Y%m%d}-{b:%Y%m%d}"},
        )

    payloads: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(_one, r): r for r in ranges}
        for fut in as_completed(futs):
            payloads.append(fut.result())

    seen: set[str] = set()
    merged_events: list[dict[str, Any]] = []
    for payload in payloads:
        for ev in payload.get("events") or []:
            eid = str(ev.get("id") or "").strip()
            if not eid:
                comp = (ev.get("competitions") or [{}])[0]
                parts = [str(ev.get("uid", "")), str(comp.get("date", ""))]
                for c in comp.get("competitors") or []:
                    t = (c.get("team") or {}).get("displayName", "")
                    parts.append(str(t))
                eid = "synth:" + str(hash(tuple(parts)))
            if eid in seen:
                continue
            seen.add(eid)
            merged_events.append(ev)

    return parse_scoreboard_payload({"events": merged_events})
