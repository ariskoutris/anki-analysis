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
- An FSRS-enabled Anki deck (for data analysis)

## Installation

```bash
pip install -r requirements.txt
```

## Running the dashboard

```bash
./run.sh
# or
python -m src.app
```

Then open <http://127.0.0.1:8050> in your browser.

## Getting Your Data

There are two ways to load your Anki data into the dashboard:

### Option 1: Direct Sync (Recommended)

If you have Anki installed on the same system as the dashboard, you can sync directly:

1. **Close Anki** (important to avoid database conflicts)
2. Click the **"🔄 Sync from Anki"** button in the dashboard
3. The dashboard will automatically find and sync your Anki collection

The sync feature:
- Automatically detects your Anki installation (Windows, macOS, Linux)
- Finds all available profiles (defaults to the first one, usually "User 1")
- Safely checks if Anki is running before syncing
- Creates a dated backup snapshot in the dashboard

### Option 2: Manual Upload

If Anki is not installed locally or you prefer manual control:

1. In Anki: File → Export → Export collection (.apkg)
2. In the dashboard: Click **"📤 Upload New Backup"**
3. Select your `.apkg` file

Both methods create timestamped backup snapshots that you can switch between using the dropdown menu.

## FSRS metrics primer

| Metric | Meaning |
|--------|---------|
| **Stability** | Days until retrievability drops to 90%. Higher = stronger memory. |
| **Difficulty** | Intrinsic card difficulty on a 0--10 scale. Higher = harder. |
| **Retrievability** | Current probability of successful recall (0--100%). Calculated as `R = exp(ln(0.9) * elapsed / stability)`. |
| **Desired Retention** | Target success rate configured in Anki (typically 90%). |