# Anki Learning Dashboard

An interactive Plotly Dash dashboard for analysing Anki flashcard reviews. Built for decks using the **FSRS** (Free Spaced Repetition Scheduler) algorithm.

## What it does

The dashboard provides two tabs of interactive charts, organized into purpose-driven sections:

### Study Sessions Tab

| Section | Purpose | What You'll See |
|---------|---------|----------------|
| **Study Volume & Consistency** | Track daily habits | Daily reviews chart, hourly performance, streak & best study hour |
| **Learning Effectiveness** | Monitor recall quality | Success rate trends, review speed, memory decay curve |
| **Workload Forecast** | Plan ahead | 60-day load forecast with your capacity line, overdue count, peak day |

### Card Knowledge Tab

| Section | Purpose | What You'll See |
|---------|---------|----------------|
| **Current Knowledge State** | Quick health check | Memory state pie, retrievability distribution, health score |
| **Collection Maturity** | Deck composition | Stability/difficulty distributions, memory growth curve |
| **Problem Areas** | Fix issues | Lapse analysis, leech identification (cards wasting your time) |

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
│   ├── app.py            # Dash application entry point
│   ├── callbacks.py      # Callback functions for interactivity
│   ├── charts_session.py # Session tab chart builders
│   ├── charts_card.py    # Card tab chart builders
│   ├── constants.py      # Colors and styling
│   ├── data_loader.py    # SQL queries and data access
│   ├── layout.py         # UI layout components
│   ├── upload_handler.py # .apkg upload processing
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
