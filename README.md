# Anki Learning Dashboard

An interactive Plotly Dash dashboard for analysing Anki flashcard reviews. Built for decks using the **FSRS** (Free Spaced Repetition Scheduler) algorithm.

## What it does

The dashboard provides two tabs of interactive charts, organized into purpose-driven sections:

### Study Sessions Tab

| Section | Purpose | What You'll See |
|---------|---------|----------------|
| **Study Volume & Consistency** | Track daily habits | Daily reviews chart, hourly performance, streak & best study hour |
| **Learning Effectiveness** | Monitor recall quality | Success rate trends, review speed, memory decay curve |
| **Workload Forecast** | Plan ahead | 60-day load forecast, overdue count, peak day |

### Card Knowledge Tab

| Section | Purpose | What You'll See |
|---------|---------|----------------|
| **Current Knowledge State** | Quick health check | Memory state pie, retrievability distribution, health score |
| **Collection Maturity** | Deck composition | Stability/difficulty distributions, memory growth curve |
| **Problem Areas** | Fix issues | Lapse analysis, leech identification (cards wasting your time) |

All charts update when you adjust filters (time range, deck, retrievability, difficulty).

## Prerequisites

- Conda (Miniconda or Anaconda)
- An FSRS-enabled Anki deck (for data analysis)

## Quick setup

```bash
conda env create -f environment.yml
conda activate anki-db
```

## Running the dashboard

```bash
conda activate anki-db
python -m src.app
```

Then open <http://127.0.0.1:8050> in your browser.

## Getting Your Data

There are two ways to load your Anki data into the dashboard:

### Option 1: Direct Sync (Recommended)

If you have Anki installed on the same system as the dashboard, you can sync directly:

1. **Open Anki** and sync from AnkiWeb to get the latest data
2. **Close Anki** (required to avoid database conflicts)
3. Click the **Sync** button in the dashboard

The sync feature:
- Automatically detects your Anki installation (Windows, macOS, Linux)
- Finds all available profiles (defaults to the first one, usually "User 1")
- Warns you if Anki is still running
- Also runs automatically on dashboard startup

### Option 2: Manual Upload

If Anki is not installed locally or you prefer manual control:

1. In Anki: File → Export → Export collection (.apkg)
2. In the dashboard: Click **Upload** and select your `.apkg` file

## FSRS metrics primer

| Metric | Meaning |
|--------|---------|
| **Stability** | Days until retrievability drops to 90%. Higher = stronger memory. |
| **Difficulty** | Intrinsic card difficulty on a 0--10 scale. Higher = harder. |
| **Retrievability** | Current probability of successful recall (0--100%). Calculated as `R = exp(ln(0.9) * elapsed / stability)`. |
| **Desired Retention** | Target success rate configured in Anki (typically 90%). |
