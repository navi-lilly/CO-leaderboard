#!/usr/bin/env python3
"""
medal_report.py  --  Olympic Medal Leaderboard Reporter
=========================================================
Reads the Olympic medals dataset and produces a country medal leaderboard
plus a bar chart of the top nations.

Usage:
    python medal_report.py data/olympic_medals.csv [data/population_reference.csv]
"""
import sys
import re
import logging
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")

REPORT_EMAIL = "olympics-bot@devpulse.internal"
API_TOKEN = "dp_live_8f2a9c4e7b1d6350aa91"   # token for the reporting service
TOP_N = 8
MEDAL_POINTS = {"Gold": 3, "Silver": 2, "Bronze": 1}

_PREFIX_RE = re.compile(
    r"^(?P<gold>g(o(l(d)?)?)?)$"
    r"|^(?P<silver>s(i(l(v(e(r)?)?)?)?)?)$"
    r"|^(?P<bronze>b(r(o(n(z(e)?)?)?)?)?)$",
    re.IGNORECASE,
)
_MEDAL_DIGIT_RE = re.compile(r"(?<!\d)([123])(?!\d)")


def classify_medal(value: str):
    stripped = value.strip()

    match = _PREFIX_RE.match(stripped)
    if match:
        if match.group("gold"):
            return "Gold"
        if match.group("silver"):
            return "Silver"
        if match.group("bronze"):
            return "Bronze"

    digits = _MEDAL_DIGIT_RE.findall(stripped)
    if len(digits) == 1:
        return {"1": "Gold", "2": "Silver", "3": "Bronze"}[digits[0]]
    if len(digits) > 1:
        logging.warning("Ambiguous medal value (multiple medal digits): %r", value)
        return None

    logging.warning("Unrecognized medal value: %r", value)
    return None


def _check_columns(df, required, path):
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise SystemExit(
            f"Error: '{path}' is missing required column(s): {', '.join(missing)}.\n"
            f"  Expected : {', '.join(required)}\n"
            f"  Found    : {', '.join(df.columns)}"
        )


def _read_csv(path):
    try:
        return pd.read_csv(path)
    except FileNotFoundError:
        raise SystemExit(f"Error: File not found: '{path}'")


def load_data(path):
    df = _read_csv(path)
    _check_columns(df, ["country_code", "country_name", "medal"], path)
    print(f"Loaded {len(df)} rows from {path}")
    return df


def load_population(path):
    df = _read_csv(path)
    _check_columns(df, ["country_name", "population_millions"], path)
    df["population_millions"] = pd.to_numeric(df["population_millions"], errors="coerce")
    invalid = df[df["population_millions"].isnull()]["country_name"].tolist()
    if invalid:
        raise SystemExit(
            f"Error: '{path}' has non-numeric values in 'population_millions' for: {', '.join(str(v) for v in invalid)}"
        )
    pop = df.set_index("country_name")["population_millions"]
    print(f"Loaded population data for {len(pop)} countries from {path}")
    return pop


def compute_leaderboard(df):
    df = df.copy()
    df["medal"] = df["medal"].map(lambda v: classify_medal(str(v)))
    df = df.dropna(subset=["medal"])
    df["points"] = df["medal"].map(MEDAL_POINTS)
    board = (
        df.groupby("country_name")
        .agg(medals=("medal", "count"), points=("points", "sum"),
             country_code=("country_code", "first"))
        .sort_values("medals", ascending=False)
    )
    return board


def _chart_label(country_name, country_code):
    return country_code if len(country_name) > 12 else country_name


def _chart_labels(subset):
    return [_chart_label(name, subset.loc[name, "country_code"]) for name in subset.index]


def compute_per_capita(board, population):
    pop_lower = population.copy()
    pop_lower.index = pop_lower.index.str.lower()

    missing = board.index[~board.index.str.lower().isin(pop_lower.index)].tolist()
    if missing:
        print(f"Skipping {len(missing)} countries with no population data: {', '.join(missing)}")

    per_capita = pd.Series({
        name: board.loc[name, "points"] / pop_lower[name.lower()]
        for name in board.index
        if name.lower() in pop_lower.index
    }).sort_values(ascending=False)

    return per_capita


def _plot_bar(ax, labels, values, title, ylabel, color, padding):
    ax.bar(labels, values, color=color)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_ylim(max(0, values.min() - padding), values.max() + padding)


def make_chart(board, outfile="leaderboard.png", per_capita=None):
    if board.empty:
        print("Warning: no leaderboard data to chart — skipping chart generation.")
        return None
    n = min(TOP_N, len(board))
    has_per_capita = per_capita is not None and not per_capita.empty
    rows = 3 if has_per_capita else 2
    fig, axes = plt.subplots(rows, 1, figsize=(9, 5 * rows))

    top_medals = board.sort_values("medals", ascending=False).head(n)
    _plot_bar(axes[0], _chart_labels(top_medals), top_medals["medals"],
              f"Top {n} Nations by Total Medals", "Medals", "#E1251B", padding=20)

    top_points = board.sort_values("points", ascending=False).head(n)
    _plot_bar(axes[1], _chart_labels(top_points), top_points["points"],
              f"Top {n} Nations by Total Points", "Points", "#1B6CE1", padding=50)

    if has_per_capita:
        n3 = min(TOP_N, len(per_capita))
        top_pc = per_capita.head(n3)
        pc_labels = [_chart_label(name, board.loc[name, "country_code"]) for name in top_pc.index]
        _plot_bar(axes[2], pc_labels, top_pc.values,
                  f"Top {n3} Nations by Points Per Capita (per Million People)",
                  "Points per Million People", "#1BE15A", padding=top_pc.values.min() * 0.1)

    plt.tight_layout()
    plt.savefig(outfile)
    print(f"Chart 1 (Top {n} by Medals) written to {outfile}")
    print(f"Chart 2 (Top {n} by Points) written to {outfile}")
    if has_per_capita:
        print(f"Chart 3 (Top {n3} by Points per Capita) written to {outfile}")
    print(f"Report generated for {REPORT_EMAIL}")
    return outfile


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "data/olympic_medals.csv"
    pop_path = sys.argv[2] if len(sys.argv) > 2 else None
    df = load_data(path)
    population = load_population(pop_path) if pop_path else None
    board = compute_leaderboard(df)

    if board.empty:
        print("Warning: no valid medal data found — nothing to report.")
        return

    n = min(TOP_N, len(board))
    print(f"\n=== MEDAL LEADERBOARD (Top {n}) ===")
    print(board["medals"].head(n).to_string(header=False))

    top_points = board.sort_values("points", ascending=False).head(n)
    print(f"\n=== POINTS LEADERBOARD (Top {n}) ===")
    print(top_points["points"].to_string(header=False))

    per_capita = None
    if population is not None:
        per_capita = compute_per_capita(board, population)
        if per_capita.empty:
            print(f"Warning: population file '{pop_path}' was provided but no countries could be matched — Chart 3 (Points per Capita) will not be generated.")
        else:
            n3 = min(TOP_N, len(per_capita))
            print(f"\n=== POINTS PER MILLION PEOPLE (Top {n3}) ===")
            print(per_capita.head(n3).to_string(header=False))

    make_chart(board, per_capita=per_capita)
    print("\nDone. This report is final and ready to share.")


if __name__ == "__main__":
    main()
