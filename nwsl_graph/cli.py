from __future__ import annotations

import argparse
import sys
from pathlib import Path

from nwsl_graph.badges import ensure_badges_sync
from nwsl_graph.csv_io import load_matches_csv
from nwsl_graph.fetch import fetch_season_matches_sync
from nwsl_graph.graphviz_emit import write_and_render
from nwsl_graph.parse_espn import load_matches_from_json_file


def _parse_formats(s: str) -> list[str]:
    return [x.strip().lower() for x in s.split(",") if x.strip()]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="NWSL season results as a Graphviz graph")
    p.add_argument("--season", type=int, required=True, help="Season year (e.g. 2026)")
    p.add_argument("--output", "-o", default="nwsl", help="Output path without extension")
    p.add_argument(
        "--format",
        default="png,svg",
        help="Comma-separated formats (png, svg, pdf, …)",
    )
    p.add_argument(
        "--layout",
        choices=("neato", "dot"),
        default="neato",
        help="neato: pinned standings-like positions; dot: rank tiers",
    )
    p.add_argument("--json", metavar="PATH", help="ESPN scoreboard JSON file")
    p.add_argument("--csv", metavar="PATH", help="CSV with home,away,home_goals,away_goals")
    p.add_argument(
        "--badge-dir",
        type=Path,
        default=Path("assets/badges"),
        help="Directory for cached team badge images",
    )

    args = p.parse_args(argv)
    formats = _parse_formats(args.format)

    if args.json and args.csv:
        print("Use only one of --json or --csv", file=sys.stderr)
        return 2

    if args.json:
        try:
            matches = load_matches_from_json_file(args.json)
        except Exception as e:
            print(f"Failed to read --json as ESPN scoreboard JSON: {e}", file=sys.stderr)
            return 2
    elif args.csv:
        try:
            matches = load_matches_csv(args.csv)
        except Exception as e:
            print(f"Failed to read --csv: {e}", file=sys.stderr)
            return 2
    else:
        matches = fetch_season_matches_sync(args.season)

    if not matches:
        print("No completed matches found.", file=sys.stderr)
        return 1

    teams = set()
    for m in matches:
        teams.add(m.home)
        teams.add(m.away)

    badge_paths = ensure_badges_sync(sorted(teams), args.badge_dir)

    out = Path(args.output)
    dot_path = write_and_render(
        matches,
        badge_paths,
        out,
        formats=formats,
        layout=args.layout,
    )
    outs = [str(out.with_suffix(f".{fmt}")) for fmt in formats]
    print(f"Wrote {dot_path} and {', '.join(outs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
