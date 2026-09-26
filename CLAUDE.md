# CLAUDE.md

## Project overview

Interactive Plotly Dash dashboard for analysing Anki flashcard reviews on FSRS-enabled decks. Auto-syncs from local Anki on startup; also supports manual sync and .apkg upload.

## File map

```
src/
  __init__.py
  app.py                    – Slim orchestrator: Dash init, layout, callback registration, entry point
  desktop.py                – Desktop entry point: pywebview window + Dash on a free port in a thread
  config.py                 – Project root + single DB path (data/anki.db)
  constants.py              – COLORS, DARK_CHART_LAYOUT, INDEX_STRING (HTML/CSS template)
  layout.py                 – create_stat_card, create_section_container, tab builders, create_main_layout
  callbacks.py              – All @callback functions + parse_time_range
  charts_session.py         – 5 session chart functions + session-mode helpers
  charts_card.py            – 9 card/analytics chart functions (pure: DataFrame → Figure)
  upload_handler.py         – .apkg file upload processing
  anki_sync.py              – Sync from local Anki install → data/anki.db; records last successful sync in data/last_sync.json (`get_last_sync_time()`)
  data_loader.py            – All SQL queries, FSRS calculations, DataFrame construction, summary stats
  fsrs_engine.py            – FSRS history replay (py-fsrs) + advanced analytics (see below)
pyproject.toml              – Project metadata + dependencies (numpy, zstandard, pandas, dash, plotly, fsrs, pywebview); managed with uv
uv.lock                     – Pinned dependency lockfile
scripts/install-launcher.sh – Builds ~/Applications/Anki Dashboard.app (macOS) pointing at this checkout
assets/icon.png             – 1024px app icon (converted to .icns by the install script)
data/                       – Not tracked. Contains single anki.db snapshot
```

## Architecture

### Data flow

```
.apkg file → upload via UI → data/anki.db
   or
Anki install → auto-sync on startup → data/anki.db
                                   ↓
                            src/data_loader.py   (SQL → pandas DataFrames)
                                   ↓
                     src/charts_session.py / src/charts_card.py  (DataFrames → Plotly figures)
                                   ↓
                            src/callbacks.py     (orchestrates data → charts → layout)
                                   ↓
                              src/app.py          (Dash init + layout assembly)
```

### Module dependency graph (no cycles)

```
constants.py            (leaf – zero internal deps)
    ^
    |--- layout.py
    |--- charts_session.py  (+ data_loader)
    |--- charts_card.py
    |
    +--- callbacks.py   (+ layout, charts_session, charts_card, data_loader, upload_handler, anki_sync)
              ^
              |
           app.py       (+ constants, layout, anki_sync)
```

### config.py

Simple path helpers. Key exports:

- `DATA_DIR` – project `data/` directory (sync, upload and last-sync file all live here)
- `get_db_path()` – returns `data/anki.db` (single snapshot, no date selection)

### data_loader.py

Pure data layer. Every public function opens its own `sqlite3` connection via `connect_db()` → `get_db_path()`. No caching across requests (each callback gets fresh data).

**Session-level queries** (all accept `review_days`):
- `get_session_data()` – per-day session stats (cards, success rate, timing)
- `get_hourly_stats()` – aggregated by hour-of-day
- `get_daily_reviews()` – daily review counts

**Card-level queries:**
- `get_card_data()` – all review cards with FSRS params parsed from `cards.data` JSON (`s`, `d`, `lrt`). Computes retrievability in Python.

**Summaries:**
- `get_overview_stats()` – card/review counts, total hours, date range
- `get_memory_state_summary()` – retrievability distribution (critical/at-risk/moderate/good/excellent)
- `calculate_daily_load()` – Σ(1/stability) for review cards
- `get_future_load_forecast(days_ahead)` – due card counts per day

**Section summary functions:**
- `get_consistency_stats()` – streak tracking, study regularity
- `get_session_summary_stats()` – current streak + avg recall rate (stat strip)
- `get_workload_summary()` – due this week, overdue cards, peak day
**Key SQL conventions:**
- `r.type != 4` excludes manual reschedules
- `c.queue != -1` excludes suspended cards
- Review timestamps are `r.id/1000` (ms → seconds since epoch)
- Due dates for review cards: `collection_start + timedelta(days=c.due)`

### fsrs_engine.py

FSRS replay + advanced analytics layer (added 2026-07). Core idea: reconstruct
per-review memory states by replaying the entire revlog through **py-fsrs**
using each deck's own FSRS parameters, parsed from the `deck_config` protobuf
blobs (fields 6/5/3 = FSRS-6/5/4.5 packed floats; field 37 = desired retention;
17/19-param sets are migrated to 21 by appending `[0,0]` / `[0,0.5]`).
Deck→preset mapping comes from the `decks.kind` protobuf (field 1.1 = config id).

- `replay_reviews(deck_id)` – one row per genuine review (types 0-3, ease 1-4,
  card still in collection) with predicted retrievability + stability/difficulty
  before/after. Cached per (db mtime, deck_id). Validated against Anki's own
  `cards.data` snapshot: difficulty exact, stability median rel-err ~3%
  (residual = Anki day-cutoff rounding).
- `get_known_words_timeseries` – Σ retrievability over all seen cards per day
  (hero chart, full-width row)
- `get_calibration_data` / `get_calibration_summary` – predicted vs observed
  recall, equal-count bins, Wilson CIs; same-day reviews excluded
- `get_retention_workload_curve` – desired retention sweep → equilibrium
  reviews/day via I(R_d,S) = S/factor · (R_d^(1/decay) − 1)
- `get_fatigue_curve` – accuracy/answer-time vs within-session position
  (sessions split on >30 min gaps)
- `simulate_future` – Monte-Carlo forward FSRS simulation (Anki's FSRS
  Simulator). Seeds current card states, rolls the py-fsrs scheduler
  day-by-day with Anki's default rating distributions; returns per-day
  memorized (Σ retrievability) and reviews. No off-the-shelf simulator
  fit: py-fsrs has none (only a private torch-gated cost sim in
  Optimizer); fsrs-rs-python's simulate() is fresh-deck only (can't seed
  the current collection); fsrs-optimizer drags in torch. Powers the
  Forecast Simulator section (controls + 2 charts, below the grid).

FSRS-6 forgetting curve used throughout: `R(t) = (1 + factor·t/S)^decay`,
`decay = −w20`, `factor = 0.9^(1/decay) − 1`.

### constants.py

Shared styling constants used across all dashboard modules:
- `COLORS` dict – primary palette for charts
- `DARK_CHART_LAYOUT` / `DARK_CHART_AXIS` – shared Plotly dark theme
- `INDEX_STRING` – custom HTML/CSS template for `app.index_string`

### layout.py

Layout builders:
- `create_stat_card(value, label, color)` – reusable stat card component
- `create_section_container(title, description, content_id, summary_id)` – section wrapper with header and optional summary area
- `create_session_tab()` – session tab layout with 3 sections (volume, effectiveness, workload)
- `create_cards_tab()` – card tab layout with 3 sections (knowledge, maturity, problems)
- `create_main_layout()` – assembles the full page layout (top bar includes the `last-sync-indicator` span next to Sync/Upload)

### charts_session.py

Session chart builders (5 functions + 2 helpers):
- Helpers: `get_time_period_markers()`, `add_session_time_markers()`
- Charts: `create_daily_reviews_chart`, `create_hourly_chart`, `create_success_rate_chart`, `create_efficiency_chart`, `create_future_load_chart`

### charts_card.py

Card chart builders (4 pure functions – DataFrame in, Figure out):
- `create_memory_state_chart`, `create_retrievability_distribution_chart`, `create_stability_distribution_chart`, `create_difficulty_distribution_chart`

### callbacks.py

All `@callback` functions + `parse_time_range` utility:

| Callback | Trigger | Output |
|----------|---------|--------|
| `update_overview_container` | `backup-refresh-token` / `url` | Overview stat cards |
| `load_ui_from_store` | `url` (page load) | Restores filter values from localStorage |
| `toggle_xaxis_mode` | x-axis buttons / `url` | Toggles dates ↔ sessions mode |
| `save_ui_to_store` | any filter change | Persists preferences to localStorage |
| `handle_backup_upload` | upload button | Processes .apkg uploads → data/anki.db |
| `handle_anki_sync` | sync button | Syncs from local Anki → data/anki.db |
| `update_last_sync_indicator` | `backup-refresh-token` / `url` | "Synced today HH:MM" / "Never synced" from data/last_sync.json (only successful Anki syncs, not uploads) |
| `auto_dismiss_upload_message` | interval | Hides upload status after 2s |
| `update_session_charts` | time-range / xaxis-mode / refresh-token | Rebuilds all 3 session sections (summaries + charts) |
| `update_card_charts` | retrievability / difficulty / refresh-token | Rebuilds all 3 card sections (summaries + charts) |

### app.py

Slim orchestrator:
1. Auto-sync from local Anki (silently skips on failure)
2. `app = dash.Dash(...)` + `app.index_string = INDEX_STRING`
3. `app.layout = create_main_layout()` (no arguments)
4. Side-effect import of `callbacks` (registers all `@callback` decorators)
5. `if __name__ == '__main__'` entry point

**Critical ordering:** auto-sync → app creation → layout → callback import (callbacks reference component IDs created in layout).

**Tab 1 – Study Sessions** (3 sections):

| Section | Summary Stats | Charts |
|---------|---------------|--------|
| Study Volume & Consistency | Avg daily reviews, current streak, best study hour | Daily reviews (area + 7-day MA), hourly performance (bar + success line) |
| Learning Effectiveness | Avg success rate, trend (↑↓→), avg session size | Recall rate over time, review speed, memory decay curve |
| Workload Forecast | Due this week, overdue cards, peak day | Future load forecast (bar + MA) |

**Tab 2 – Card Knowledge** (3 sections):

| Section | Summary Stats | Charts |
|---------|---------------|--------|
| Current Knowledge State | Health score, cards needing attention, median retrievability | Memory state pie, retrievability histogram |
| Collection Maturity | Avg stability, % mature cards, cards shown | Stability histogram, difficulty histogram, memory growth curve |
| Problem Areas | Leech count, total lapses, avg difficulty | Lapses bar chart, leech scatter (time wasted vs lapses) |

**Session mode:**
Charts support a date/session x-axis toggle. In session mode, sequential indices replace dates and year-boundary markers are drawn as vertical lines.

## Conventions

- FSRS params live in `cards.data` as JSON: `{"s": stability, "d": difficulty, "lrt": last_review_timestamp_sec, ...}`
- Retrievability formula: `R = exp(ln(0.9) * days_since_review / stability)`
- All SQL filters are built via `build_time_filter()` which returns a SQL fragment
- Charts use a shared `COLORS` dict and `DARK_CHART_LAYOUT` for consistent styling (defined in `constants.py`)
- All modules use relative imports (`from .constants import COLORS`); run via `uv run python -m src.app`

## Running

```bash
uv run python -m src.app      # dev server on http://127.0.0.1:8050 (debug + hot reload)
uv run python -m src.desktop  # native window, no debug; what the .app launcher runs
```

The `.app` launcher's `Contents/MacOS/launch` runs `uv sync` then `exec`s `.venv/bin/python -m src.desktop`
(exec, not `uv run`, so the Dock shows the bundle's name/icon). Output goes to
`~/Library/Logs/anki-dashboard.log`. First launch triggers a macOS privacy prompt for the repo's folder
(e.g. ~/Documents); until accepted, the launcher hangs silently on `uv sync`.
