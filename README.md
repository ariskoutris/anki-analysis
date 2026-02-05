# Anki Learning Dashboard

An interactive Plotly Dash dashboard for analysing Anki flashcard reviews. Built for decks using the **FSRS** (Free Spaced Repetition Scheduler) algorithm.

## What it does

The dashboard provides two tabs of interactive charts:

- **Study Sessions** -- daily review counts, success rate trends, review speed, time-per-card distribution, memory retention by interval, and a 60-day review load forecast.
- **Card Knowledge** -- memory state breakdown, retrievability/stability/difficulty distributions, scatter plots of key correlations, lapse analysis, and time-invested vs stability.

All charts update when you switch between backup snapshots or adjust filters (time range, retrievability, difficulty).

## Prerequisites

- Python 3.11+
- An FSRS-enabled Anki deck exported as an `.apkg` file

## Installation

```bash
pip install -r requirements.txt
```

## Extracting an Anki backup

Export your deck from Anki as a `.apkg` file and place it somewhere accessible. Then extract the database:

```bash
# Create a dated folder and unzip the .apkg into it
mkdir -p data/2026-02-05
unzip "Core 2K.apkg" -d data/2026-02-05

# Decompress the zstd-compressed database
python scripts/decompress_anki21b.py --date 2026-02-05
```

If you omit `--date`, the script auto-detects the latest `YYYY-MM-DD` folder under `data/`.

## Running the dashboard

```bash
./run_dashboard.sh
# or
python dashboard/app.py
```

Then open <http://127.0.0.1:8050> in your browser.

## FSRS metrics primer

| Metric | Meaning |
|--------|---------|
| **Stability** | Days until retrievability drops to 90%. Higher = stronger memory. |
| **Difficulty** | Intrinsic card difficulty on a 0--10 scale. Higher = harder. |
| **Retrievability** | Current probability of successful recall (0--100%). Calculated as `R = exp(ln(0.9) * elapsed / stability)`. |
| **Desired Retention** | Target success rate configured in Anki (typically 90%). |

## Project structure

```
anki-analysis/
├── dashboard/
│   ├── app.py            # Dash application
│   ├── data_loader.py    # SQL queries and data access
│   └── __init__.py
├── scripts/
│   └── decompress_anki21b.py   # .apkg → SQLite extractor
├── anki_config.py        # Active backup date management
├── run_dashboard.sh      # Convenience launcher
├── requirements.txt
└── data/                 # Backup snapshots (not tracked)
    └── YYYY-MM-DD/
        └── decompressed_anki21b.db
```
