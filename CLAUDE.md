# CLAUDE.md

## Project overview

Interactive Plotly Dash dashboard for analysing Anki flashcard reviews on FSRS-enabled decks. Auto-syncs from AnkiWeb on startup (once logged in); also supports manual sync and .apkg upload.

## File map

```
src/
  __init__.py
  app.py                    – Slim orchestrator: Dash init, layout, callback registration, entry point
  desktop.py                – Desktop entry point: pywebview window + Dash on a free port in a thread
  config.py                 – Project root + single DB path (data/anki.db)
  constants.py              – COLORS, DARK_CHART_LAYOUT, INDEX_STRING (HTML/CSS template)
  layout.py                 – create_stat_card, create_section_container, tab builders, create_main_layout
  assets/grid.js            – Chart grid move/resize (plain CSS grid, order + widths in localStorage)
  callbacks.py              – All @callback functions + parse_time_range
  charts_session.py         – 5 session chart functions + session-mode helpers
  charts_card.py            – 9 card/analytics chart functions (pure: DataFrame → Figure)
  upload_handler.py         – .apkg file upload processing
  anki_sync.py              – AnkiWeb login + full download → data/anki.db via the `anki` package (skipped when `sync_status` on the current anki.db reports no changes); sync key in data/ankiweb.json, last successful sync in data/last_sync.json (`get_last_sync_time()`)
  data_loader.py            – All SQL queries, FSRS calculations, DataFrame construction, summary stats
  fsrs_engine.py            – FSRS analytics on Anki's backend (`anki` package) (see below)
pyproject.toml              – Project metadata + dependencies (numpy, zstandard, pandas, dash, plotly, pywebview, anki); managed with uv
uv.lock                     – Pinned dependency lockfile
scripts/install-launcher.sh – Builds ~/Applications/AnkiDash.app (macOS) pointing at this checkout
assets/icon.png             – 1024px app icon (converted to .icns by the install script)
scripts/make-icon.py        – Renders assets/icon.png with AppKit
data/                       – Not tracked. Contains single anki.db snapshot
```

## Architecture

### Data flow

```
.apkg file → upload via UI → data/anki.db
   or
AnkiWeb → auto-sync on startup / Sync button → data/anki.db
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

Data layer. Plain SQL goes through `connect_db()` (sqlite3); anything Anki computes (FSRS retrievability, future-due counts, rollover, deck names) goes through `open_collection()`, which opens data/anki.db as an Anki `Collection` under a lock (the backend raises DBError on concurrent opens; Dash runs callbacks in parallel). `deck_search(deck_id)` is the Anki-search twin of `build_deck_filter`. Every function a callback calls is wrapped in `@per_db`: an `lru_cache` keyed on (anki.db inode, current hour). Sync and upload `os.replace` the file, so the inode changes; mtime can't be used because Anki writes to the file itself on first use after a download. Cached DataFrames are shared, so never mutate them in place.

**Session-level queries** (all accept `review_days`):
- `get_session_data()` – per-day session stats (cards, success rate, timing)
- `get_hourly_stats()` – aggregated by hour-of-day
- `get_daily_reviews()` – daily review counts

**Card-level queries:**
- `get_card_data()` – learning/review cards: stability, difficulty, retrievability via Anki's SQL functions (`extract_fsrs_variable`, `extract_fsrs_retrievability`; values rounded back from float32)

**Summaries:**
- `get_overview_stats()` – review cards, review count, total hours, days studied
- `calculate_daily_load()` – Σ(1/stored interval) for review cards; an estimated scheduled review rate
- `get_future_load_forecast(days_ahead)` – due counts per day from Anki's `graphs().future_due` (day 0 = Anki's today)

**Section summary functions:**
- `get_current_streak()` – consecutive study days (Anki rollover hour)
- `get_session_summary_stats()` – current streak + avg recall rate (stat strip)
- `get_workload_summary()` – due this week (today included), overdue cards, both from `future_due`
**Key SQL conventions:**
- `r.type != 4` excludes manual reschedules
- `c.queue != -1` excludes suspended cards
- Review timestamps are `r.id/1000` (ms → seconds since epoch)
- Due dates for review cards: `collection_start + timedelta(days=c.due)`

### fsrs_engine.py

FSRS analytics layer. Memory states, presets, the simulator and the workload
estimate all come from Anki's own backend via the `anki` package, so they match
what Anki schedules with. `open_collection()` (in data_loader) opens data/anki.db as an Anki `Collection`;
plain sqlite3 reads keep working alongside it.

- `get_deck_fsrs_configs()` – deck_id → decay/desired retention/daily
  limits from `col.decks.config_dict_for_deck_id` (17/19-param sets migrated
  to 21 by appending `[0,0]` / `[0,0.5]`). "All decks" uses the preset of the
  deck with the most review cards (`_main_config`).
- `replay_reviews(deck_id)` – one row per genuine review (types 0-3, ease 1-4,
  card still in collection) with predicted retrievability + stability after,
  from `col.card_stats_data(cid).revlog[*].memory_state`
  (exact match to `cards.data`). Cached via `per_db`.
- `get_known_words_timeseries` – Σ retrievability over all seen cards per day
  (hero chart, full-width row)
- `get_calibration_data` / `get_calibration_summary` – predicted vs observed
  recall, equal-count bins, Wilson CIs; same-day reviews excluded
- `get_retention_workload_curve` – Anki's `get_retention_workload` (deck
  options' "help me decide"): review time cost at 70–99% retention incl.
  relearning, shown relative to the current setting (1×)
- `get_true_retention` – Anki's true retention (Stats screen) for week/month/year via `graphs()`;
  30-day value in the stat strip, week/month/year in its tooltip
- `get_fatigue_curve` – accuracy/answer-time vs within-session position
  (sessions split on >30 min gaps)
- `simulate_future` – Anki's FSRS simulator (`simulate_fsrs_review`),
  seeded with the deck's current cards and preset; returns per-day memorized
  (Σ retrievability) and reviews. Powers the Forecast Simulator section
  (controls + 2 charts, below the grid).

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
- `_segmented(id, options)` – top-bar toggle (Range, X-axis, Load): `dcc.RadioItems` styled by the `.segmented` CSS class, value remembered via Dash `persistence` (deck dropdown too); no callbacks needed
- `create_main_layout()` – assembles the full page layout (top bar includes the `last-sync-indicator` span next to Sync/Upload, plus the hidden `ankiweb-login` panel)

### charts_session.py

Session chart builders (5 functions + helpers):
- Helpers: `get_time_period_markers()`, `add_session_time_markers()`, `_session_scatter_chart()` (shared by daily reviews / recall rate / review speed)
- Charts: `create_daily_reviews_chart`, `create_hourly_chart`, `create_success_rate_chart`, `create_efficiency_chart`, `create_future_load_chart`

### charts_card.py

Card chart builders (4 pure functions – DataFrame in, Figure out):
- `create_memory_state_chart`, `create_retrievability_distribution_chart`, `create_stability_distribution_chart`, `create_difficulty_distribution_chart`

### callbacks.py

All `@callback` functions + `parse_time_range` utility. The chart callbacks' figures are cached with `per_db` too (`update_card_charts` writes data/last_view.json, then calls the cached `_card_charts`):

| Callback | Trigger | Output |
|----------|---------|--------|
| `update_overview_container` | `backup-refresh-token` / `url` | Overview stat cards |
| `handle_backup_upload` | upload button | Processes .apkg uploads → data/anki.db |
| `handle_anki_sync` | sync button | Syncs from AnkiWeb → data/anki.db; toggles the login panel when not logged in |
| `handle_ankiweb_login` | login button / Enter in password | Stores AnkiWeb sync key, then syncs |
| `update_last_sync_indicator` | `backup-refresh-token` / `url` | "Synced today HH:MM" / "Never synced" from data/last_sync.json (only successful Anki syncs, not uploads) |
| `auto_dismiss_upload_message` | interval | Hides upload status after 2s |
| `update_session_charts` | time-range / xaxis-mode / refresh-token | Rebuilds all 3 session sections (summaries + charts) |
| `update_card_charts` | retrievability / difficulty / refresh-token | Rebuilds all 3 card sections (summaries + charts) |

### app.py

Slim orchestrator:
1. Auto-sync from AnkiWeb (skips when not logged in or offline)
2. `app = dash.Dash(...)` + `app.index_string = INDEX_STRING`
3. `app.layout = create_main_layout()` (no arguments)
4. Side-effect import of `callbacks` (registers all `@callback` decorators)
5. Cache warm-up: calls the overview/session/card callbacks for the last-used view (data/last_view.json, written by `update_card_charts`), so the first page load hits the cache
6. `if __name__ == '__main__'` entry point

**Critical ordering:** auto-sync → app creation → layout → callback import → warm-up (callbacks reference component IDs created in layout).

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
- Retrievability: Anki's own `extract_fsrs_retrievability` (card snapshot) / FSRS-6 curve with each deck's decay (replay)
- All SQL filters are built via `build_time_filter()` which returns a SQL fragment
- Date x-values reach the browser as epoch ms on `type='date'` axes (`_dates_as_ms` in callbacks.py, applied to every chart callback's figures), so Plotly skips parsing date strings
- Charts use a shared `COLORS` dict and `DARK_CHART_LAYOUT` for consistent styling (defined in `constants.py`)
- All modules use relative imports (`from .constants import COLORS`); run via `uv run python -m src.app`

## Running

```bash
uv run python -m src.app      # dev server on http://127.0.0.1:8050 (debug + hot reload)
uv run python -m src.desktop  # native window, no debug; what the .app launcher runs
```

The `.app` launcher's `Contents/MacOS/launch` runs `uv sync` then `exec`s `.venv/bin/python -m src.desktop`
(exec, not `uv run`, so the Dock shows the bundle's name/icon). Output goes to
`~/Library/Logs/ankidash.log`. First launch triggers a macOS privacy prompt for the repo's folder
(e.g. ~/Documents); until accepted, the launcher hangs silently on `uv sync`.
