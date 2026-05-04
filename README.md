# NWSL Graph

Generate a Graphviz graph of National Women’s Soccer League results: team badges as nodes, edge thickness by goal margin, and approximate standings-based layout.

## Setup

Use a virtual environment so `pip` is not blocked by PEP 668 (“externally-managed-environment”) on Debian/Ubuntu Python:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e .
```

If `python3 -m venv` fails, install venv support (e.g. `sudo apt install python3-venv` or `python3-full`).

This installs the lightweight Python `graphviz` helper package. You still need Graphviz installed so `dot` is on your `PATH` (e.g. `sudo apt install graphviz`).

## Usage

With the venv activated (see Setup), run:

```bash
nwsl-graph --season 2026 --output nwsl_2026 --format png,svg
```

Or without activating: `.venv/bin/nwsl-graph --season 2026 ...`

- `--json PATH` — use a saved ESPN scoreboard JSON instead of fetching.
- `--csv PATH` — columns: `home,away,home_goals,away_goals` (optional `date`).
- `--badge-dir DIR` — cache directory for badge images (default: `assets/badges`).

## License

See [LICENSE](LICENSE).
