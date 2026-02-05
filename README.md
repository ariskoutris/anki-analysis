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

## Running the dashboard

```bash
./run.sh
# or
python -m src.app
```

Then open <http://127.0.0.1:8050> in your browser.

## FSRS metrics primer

| Metric | Meaning |
|--------|---------|
| **Stability** | Days until retrievability drops to 90%. Higher = stronger memory. |
| **Difficulty** | Intrinsic card difficulty on a 0--10 scale. Higher = harder. |
| **Retrievability** | Current probability of successful recall (0--100%). Calculated as `R = exp(ln(0.9) * elapsed / stability)`. |
| **Desired Retention** | Target success rate configured in Anki (typically 90%). |