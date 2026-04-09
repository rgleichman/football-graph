# NWSL Graph

Generate a Graphviz graph of National Women’s Soccer League results: team badges as nodes, edge thickness by goal margin, and approximate standings-based layout.

## Setup

```bash
pip install -e .
```

This installs the lightweight Python `graphviz` helper package. You still need Graphviz installed so `dot` and `neato` are on your `PATH` (e.g. `apt install graphviz`).

## Usage

```bash
nwsl-graph --season 2026 --output nwsl_2026 --format png,svg
```

- `--json PATH` — use a saved ESPN scoreboard JSON instead of fetching.
- `--csv PATH` — columns: `home,away,home_goals,away_goals` (optional `date`).
- `--layout neato` (default) or `dot` — standings ordering is applied in both modes.
- `--badge-dir DIR` — cache directory for badge images (default: `assets/badges`).

## License

See [LICENSE](LICENSE).
