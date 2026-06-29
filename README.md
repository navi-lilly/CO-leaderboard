# Olympic Medal Leaderboard

Generates a country medal leaderboard and bar charts from the Olympic medals dataset.

## Requirements

- Python 3.8+
- `pandas`
- `matplotlib`

```bash
pip install pandas matplotlib
```

## Usage

```bash
# Basic leaderboard (medal count + points)
python medal_report.py data/olympic_medals.csv

# With per-capita chart (requires population file)
python medal_report.py data/olympic_medals.csv data/population_reference.csv
```

## Output

- Console: top 8 countries ranked by total medals and by points (Gold=3, Silver=2, Bronze=1)
- `leaderboard.png`: bar charts saved to the working directory
  - Chart 1 — Top nations by total medals
  - Chart 2 — Top nations by total points
  - Chart 3 — Top nations by points per million people *(only when population file is provided)*

## Data files

| File | Description |
|------|-------------|
| `data/olympic_medals.csv` | One row per athlete per event. Required columns: `country_code`, `country_name`, `medal` |
| `data/population_reference.csv` | Country populations in millions. Required columns: `country_code`, `country_name`, `population_millions`. Currently covers 30 countries — add rows to expand coverage. |

## Scoring

| Medal | Points |
|-------|--------|
| Gold | 3 |
| Silver | 2 |
| Bronze | 1 |

The `medal` column is flexible — values like `"Gold"`, `"g"`, `"1"` are all accepted.
