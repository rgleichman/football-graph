from __future__ import annotations

import re
from pathlib import Path
from typing import Literal

from nwsl_graph.models import Match
from nwsl_graph.standings import compute_elo_ratings, compute_standings, normalize_scores

_WIN_COLOR = "#1b5e20"
_TIE_COLOR = "#757575"
_PEN_BASE = 0.45
_PEN_SCALE = 0.85
_PEN_MIN = 0.5
_PEN_MAX = 5.0


RankingMode = Literal["wl", "elo"]


def _nid(team: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", team.strip()).strip("_")
    if not s:
        s = "team"
    if s[0].isdigit():
        s = "t_" + s
    return s


def _penwidth(diff: int) -> str:
    w = _PEN_BASE + _PEN_SCALE * float(diff)
    w = max(_PEN_MIN, min(_PEN_MAX, w))
    return f"{w:.3f}"


def _maybe_import_graphviz():
    try:
        import graphviz  # type: ignore

        return graphviz
    except Exception:
        return None


def print_rankings_table(matches: list[Match], *, ranking: RankingMode) -> None:
    if ranking == "wl":
        rows = compute_standings(matches)
        print("Ranking: wl (normalized (wins-losses)/played)")
        print(f"{'team':30} {'P':>3} {'W-D-L':>7} {'norm':>8}")
        for r in rows:
            wdl = f"{r.wins}-{r.draws}-{r.losses}"
            print(f"{r.team:30} {r.played:>3} {wdl:>7} {r.points:>8.3f}")
        return

    if ranking == "elo":
        elo = compute_elo_ratings(matches, initial_rating=1500.0, k_factor=20.0)
        norm = normalize_scores(elo)
        ordered = sorted(elo.keys(), key=lambda t: (norm.get(t, 0.0), elo[t], t), reverse=True)
        print("Ranking: elo (ELO init=1500 K=20; graph uses normalized 0..1)")
        print(f"{'team':30} {'elo':>10} {'norm':>8}")
        for team in ordered:
            print(f"{team:30} {elo[team]:>10.1f} {norm.get(team, 0.0):>8.3f}")
        return

    raise ValueError(f"Unknown ranking mode: {ranking}")


def _team_order_and_scores(matches: list[Match], *, ranking: RankingMode) -> tuple[list[str], dict[str, float]]:
    """
    Return a team ordering (high to low) plus the score used for grouping/order.
    For wl: score is StandingRow.points.
    For elo: score is normalized ELO in 0..1.
    """
    if ranking == "wl":
        standings = compute_standings(matches)
        score_by_team = {r.team: float(r.points) for r in standings}
        ordered = [r.team for r in standings]
        return ordered, score_by_team

    if ranking == "elo":
        elo = compute_elo_ratings(matches, initial_rating=1500.0, k_factor=20.0)
        score_by_team = normalize_scores(elo)
        ordered = sorted(score_by_team.keys(), key=lambda t: (score_by_team[t], t), reverse=True)
        return ordered, score_by_team

    raise ValueError(f"Unknown ranking mode: {ranking}")


def build_graphviz_digraph(
    matches: list[Match],
    badge_paths: dict[str, Path],
    *,
    ranking: RankingMode = "wl",
    show_invis_edges: bool = False,
    disable_rank_spine: bool = False,
):
    """Build a graphviz.Digraph if the Python package is available."""
    graphviz = _maybe_import_graphviz()
    if graphviz is None:
        return None

    ordered_teams, score_by_team = _team_order_and_scores(matches, ranking=ranking)
    teams: set[str] = set()
    for m in matches:
        teams.add(m.home)
        teams.add(m.away)

    g = graphviz.Digraph("nwsl", engine="dot")
    g.attr("graph", rankdir="TB", splines="true", bgcolor="white", fontname="Helvetica", fontsize="10")
    g.attr("edge", fontname="Helvetica", fontsize="8")
    g.attr("node", fontname="Helvetica", fontsize="8")

    def _node_attrs(team: str) -> dict[str, str]:
        img = badge_paths.get(team)
        attrs: dict[str, str] = {
            "shape": "none",
            "fixedsize": "true",
            "width": "0.9",
            "height": "0.9",
            "imagescale": "true",
            "label": "",
        }
        if img:
            attrs["image"] = str(img.resolve())
        return attrs

    if disable_rank_spine:
        # No explicit rank constraints; just emit all nodes and let edges drive layout.
        for team in sorted(teams):
            g.node(_nid(team), **_node_attrs(team))
    else:
        # Group by rounded normalized score to keep ranks readable.
        points_to_teams: dict[float, list[str]] = {}
        for team in ordered_teams:
            key = round(float(score_by_team.get(team, 0.0)), 3)
            points_to_teams.setdefault(key, []).append(team)
        for pl in points_to_teams:
            points_to_teams[pl].sort()
        ordered_points = sorted(points_to_teams.keys(), reverse=True)

        for p in ordered_points:
            group = points_to_teams[p]
            with g.subgraph() as s:
                s.attr(rank="same")
                for team in group:
                    nid = _nid(team)
                    s.node(nid, **_node_attrs(team))

        reps = [points_to_teams[p][0] for p in ordered_points]
        for i in range(len(reps) - 1):
            if show_invis_edges:
                g.edge(
                    _nid(reps[i]),
                    _nid(reps[i + 1]),
                    style="dashed",
                    color="#d32f2f",
                    penwidth="1.2",
                    constraint="true",
                )
            else:
                g.edge(_nid(reps[i]), _nid(reps[i + 1]), style="invis", constraint="true")

    common = {"constraint": "true"}
    for m in matches:
        a, b = _nid(m.home), _nid(m.away)
        diff = m.differential
        label = f"{m.home_goals}-{m.away_goals}"
        if m.is_tie():
            g.edge(
                a,
                b,
                dir="none",
                label=label,
                color=_TIE_COLOR,
                style="dashed",
                penwidth=_penwidth(0),
                **common,
            )
        elif m.home_goals > m.away_goals:
            g.edge(a, b, label=label, color=_WIN_COLOR, penwidth=_penwidth(diff), **common)
        else:
            g.edge(b, a, label=label, color=_WIN_COLOR, penwidth=_penwidth(diff), **common)

    return g


def write_and_render(
    matches: list[Match],
    badge_paths: dict[str, Path],
    output_base: Path,
    *,
    formats: list[str],
    ranking: RankingMode = "wl",
    show_invis_edges: bool = False,
    disable_rank_spine: bool = False,
) -> Path:
    g = build_graphviz_digraph(
        matches,
        badge_paths,
        ranking=ranking,
        show_invis_edges=show_invis_edges,
        disable_rank_spine=disable_rank_spine,
    )
    if g is None:
        raise RuntimeError(
            "Python package 'graphviz' is required to render. "
            "Install it (pip install graphviz) and ensure the Graphviz 'dot' binary is on PATH."
        )

    output_base = output_base.expanduser().resolve()
    output_base.parent.mkdir(parents=True, exist_ok=True)
    dot_path = output_base.with_suffix(".dot")
    dot_path.write_text(g.source, encoding="utf-8")

    for fmt in formats:
        # graphviz decides the exact output path; we also keep the .dot written above.
        g.render(
            filename=output_base.name,
            directory=str(output_base.parent),
            format=fmt,
            cleanup=True,
        )
    return dot_path
