from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from nwsl_graph.models import Match
from nwsl_graph.standings import compute_standings

_WIN_COLOR = "#1b5e20"
_TIE_COLOR = "#757575"
_PEN_BASE = 0.45
_PEN_SCALE = 0.85
_PEN_MIN = 0.5
_PEN_MAX = 5.0


def _nid(team: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", team.strip()).strip("_")
    if not s:
        s = "team"
    if s[0].isdigit():
        s = "t_" + s
    return s


def _dot_escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _penwidth(diff: int) -> str:
    w = _PEN_BASE + _PEN_SCALE * float(diff)
    w = max(_PEN_MIN, min(_PEN_MAX, w))
    return f"{w:.3f}"


def _node_attr_lines(
    team: str,
    badge_paths: dict[str, Path],
    *,
    indent: int = 1,
) -> str:
    sp = "  " * indent
    nid = _nid(team)
    img = badge_paths.get(team)
    attrs: list[str] = [
        "shape=none",
        "fixedsize=true",
        "width=0.9",
        "height=0.9",
        "imagescale=true",
        'label=""',
    ]
    if img:
        ip = str(img.resolve()).replace("\\", "/")
        attrs.append(f'image="{_dot_escape(ip)}"')
    return f'{sp}{nid} [{" ".join(attrs)}]'

def _maybe_import_graphviz():
    try:
        import graphviz  # type: ignore

        return graphviz
    except Exception:
        return None


def build_dot_source(
    matches: list[Match],
    badge_paths: dict[str, Path],
) -> str:
    standings = compute_standings(matches)
    teams: set[str] = set()
    for m in matches:
        teams.add(m.home)
        teams.add(m.away)

    lines: list[str] = [
        "digraph nwsl {",
        '  graph [rankdir=TB splines=true bgcolor=white fontname=Helvetica fontsize=10 ranksep=1.1 nodesep=0.55]',
        '  edge [fontname=Helvetica fontsize=8]',
        '  node [fontname=Helvetica fontsize=8]',
    ]

    points_to_teams: dict[int, list[str]] = {}
    for r in standings:
        points_to_teams.setdefault(r.points, []).append(r.team)
    for pl in points_to_teams:
        points_to_teams[pl].sort()
    ordered_points = sorted(points_to_teams.keys(), reverse=True)

    for p in ordered_points:
        group = points_to_teams[p]
        lines.append("  {")
        lines.append("    rank=same;")
        for team in group:
            lines.append(_node_attr_lines(team, badge_paths, indent=2))
        lines.append("  }")

    reps = [points_to_teams[p][0] for p in ordered_points]
    for i in range(len(reps) - 1):
        lines.append(f'  {_nid(reps[i])} -> {_nid(reps[i + 1])} [style=invis constraint=true]')

    edge_constraint = "true"
    for m in matches:
        a, b = _nid(m.home), _nid(m.away)
        diff = m.differential
        label = f"{m.home_goals}-{m.away_goals}"
        lab = _dot_escape(label)
        common = f"constraint={edge_constraint}"
        if m.is_tie():
            lines.append(
                f'  {a} -> {b} [dir=none label="{lab}" color="{_TIE_COLOR}" '
                f'style=dashed penwidth={_penwidth(0)} {common}]'
            )
        elif m.home_goals > m.away_goals:
            lines.append(
                f'  {a} -> {b} [label="{lab}" color="{_WIN_COLOR}" '
                f'penwidth={_penwidth(diff)} {common}]'
            )
        else:
            lines.append(
                f'  {b} -> {a} [label="{lab}" color="{_WIN_COLOR}" '
                f'penwidth={_penwidth(diff)} {common}]'
            )

    lines.append("}")
    return "\n".join(lines)


def build_graphviz_digraph(
    matches: list[Match],
    badge_paths: dict[str, Path],
):
    """Build a graphviz.Digraph if the Python package is available."""
    graphviz = _maybe_import_graphviz()
    if graphviz is None:
        return None

    standings = compute_standings(matches)
    teams: set[str] = set()
    for m in matches:
        teams.add(m.home)
        teams.add(m.away)

    g = graphviz.Digraph("nwsl")
    g.attr("graph", rankdir="TB", splines="true", bgcolor="white", fontname="Helvetica", fontsize="10")
    g.attr("edge", fontname="Helvetica", fontsize="8")
    g.attr("node", fontname="Helvetica", fontsize="8")

    points_to_teams: dict[int, list[str]] = {}
    for r in standings:
        points_to_teams.setdefault(r.points, []).append(r.team)
    for pl in points_to_teams:
        points_to_teams[pl].sort()
    ordered_points = sorted(points_to_teams.keys(), reverse=True)

    for p in ordered_points:
        group = points_to_teams[p]
        with g.subgraph() as s:
            s.attr(rank="same")
            for team in group:
                nid = _nid(team)
                img = badge_paths.get(team)
                attrs = {
                    "shape": "none",
                    "fixedsize": "true",
                    "width": "0.9",
                    "height": "0.9",
                    "imagescale": "true",
                    "label": "",
                }
                if img:
                    attrs["image"] = str(img.resolve())
                s.node(nid, **attrs)

    reps = [points_to_teams[p][0] for p in ordered_points]
    for i in range(len(reps) - 1):
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
) -> Path:
    g = build_graphviz_digraph(matches, badge_paths)
    output_base = output_base.expanduser().resolve()
    output_base.parent.mkdir(parents=True, exist_ok=True)
    dot_path = output_base.with_suffix(".dot")
    if g is not None:
        dot_path.write_text(g.source, encoding="utf-8")
    else:
        dot_path.write_text(build_dot_source(matches, badge_paths), encoding="utf-8")

    engine = "dot"
    binary = shutil.which(engine)
    if not binary:
        raise FileNotFoundError(f"Graphviz {engine} binary not found on PATH")

    for fmt in formats:
        out = output_base.with_suffix(f".{fmt}")
        cmd = [binary, f"-T{fmt}", "-o", str(out), str(dot_path)]
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    return dot_path
