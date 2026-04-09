from __future__ import annotations

import re
from pathlib import Path

from nwsl_graph.http_util import download_bytes

# NWSL image CDN — `t_q-best` for consistent sizing; paths from nwslsoccer.com standings assets.
BADGE_URL_BY_ESPN_DISPLAY_NAME: dict[str, str] = {
    "Angel City FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436088/prd/assets/teams/angel-city-fc.png",
    "Bay FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436090/prd/assets/teams/bay-fc.png",
    "Boston Legacy FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1749431607/prd/assets/teams/bos-nation-fc.png",
    "Chicago Stars FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1774457661/prd/assets/teams/chicago-stars.png",
    "Denver Summit FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1757004382/prd/assets/teams/denver-summit-fc.png",
    "Houston Dash": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436093/prd/assets/teams/houston-dash.png",
    "Kansas City Current": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436094/prd/assets/teams/kansas-city-current.png",
    "Gotham FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1768567024/prd/assets/teams/nj-ny-gotham-fc.png",
    "North Carolina Courage": "https://images.nwslsoccer.com/image/private/t_q-best/v1712866345/prd/assets/teams/north-carolina-courage.png",
    "Orlando Pride": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436099/prd/assets/teams/orlando-pride.png",
    "Portland Thorns FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436101/prd/assets/teams/portland-thorns-fc.png",
    "Racing Louisville FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436103/prd/assets/teams/racing-louisville-fc.png",
    "San Diego Wave FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436105/prd/assets/teams/san-diego-wave-fc.png",
    "Seattle Reign FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436107/prd/assets/teams/seattle-reign.png",
    "Seattle Reign": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436107/prd/assets/teams/seattle-reign.png",
    "Utah Royals": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436109/prd/assets/teams/utah-royals-fc.png",
    "Utah Royals FC": "https://images.nwslsoccer.com/image/private/t_q-best/v1710436109/prd/assets/teams/utah-royals-fc.png",
    "Washington Spirit": "https://images.nwslsoccer.com/image/private/t_q-best/v1712866158/prd/assets/teams/washington-spirit.png",
}


def badge_url_for_team(display_name: str) -> str | None:
    if display_name in BADGE_URL_BY_ESPN_DISPLAY_NAME:
        return BADGE_URL_BY_ESPN_DISPLAY_NAME[display_name]
    key = display_name.strip().lower()
    for name, url in BADGE_URL_BY_ESPN_DISPLAY_NAME.items():
        if name.lower() == key:
            return url
    return None


def _safe_filename(url: str) -> str:
    base = url.split("/teams/")[-1].split("?")[0]
    return re.sub(r"[^a-zA-Z0-9._-]", "_", base) or "badge.bin"

def ensure_badge_sync(display_name: str, cache_dir: Path) -> Path | None:
    """Download badge into cache_dir if missing; return local path."""
    url = badge_url_for_team(display_name)
    if not url:
        return None
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_dir / _safe_filename(url)
    if path.exists() and path.stat().st_size > 0:
        return path.resolve()
    data = download_bytes(url)
    path.write_bytes(data)
    return path.resolve()


def ensure_badges_sync(team_names: list[str], cache_dir: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for name in team_names:
        p = ensure_badge_sync(name, cache_dir)
        if p is not None:
            out[name] = p
    return out
