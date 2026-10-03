#!/usr/bin/env python3
"""
AnkiDash: interactive Anki learning dashboard
Entry point: creates the Dash app, sets layout, and registers callbacks.
"""

import os
import threading
import time
import dash
from dash import dcc

from .constants import INDEX_STRING
from .layout import create_main_layout
from .anki_sync import sync_from_ankiweb
from .config import DATA_DIR, get_last_view
from .data_loader import data_version, get_deck_list

os.makedirs(DATA_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Create the Dash application
# ---------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    title="AnkiDash",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.index_string = INDEX_STRING

# Charts use only cartesian traces, so serve plotly.js's cartesian build
# (assets/plotly-cartesian.min.js, 1.4 MB) instead of Dash's full 4.7 MB one.
# dcc.Graph uses window.Plotly when it's already loaded. Keep the asset's
# version in step with `plotly.offline.get_plotlyjs_version()`.
dcc._js_dist[:] = [r for r in dcc._js_dist if r.get('namespace') != 'plotly']

# ---------------------------------------------------------------------------
# 2. Set layout
# ---------------------------------------------------------------------------
app.layout = create_main_layout

# ---------------------------------------------------------------------------
# 3. Register all callbacks (side-effect import)
# ---------------------------------------------------------------------------
from . import callbacks  # noqa: F401, E402


# ---------------------------------------------------------------------------
# 4. Warm-up + background sync
# ---------------------------------------------------------------------------
SYNC_INTERVAL = 30 * 60  # seconds


def _warm_up():
    """Compute the last-used view, so the page loads from the cache."""
    try:
        deck, time_range, xaxis_mode = get_last_view()
        if deck != 'all' and deck not in {str(d['id']) for d in get_deck_list()}:
            deck = 'all'
        callbacks.update_overview_container(0, '/', deck)
        callbacks.update_session_charts(time_range, xaxis_mode, 0, deck)
        callbacks._card_charts(deck, time_range, xaxis_mode)
    except Exception as e:
        print(f"  Cache warm-up skipped: {e}")


def _sync_forever():
    """
    Sync from AnkiWeb now and every SYNC_INTERVAL. The page shows the data
    already on disk meanwhile, and refreshes itself when a sync brings new
    data (see refresh_on_new_data in callbacks.py).
    """
    while True:
        before = data_version()
        try:
            success, message = sync_from_ankiweb(DATA_DIR)
            print(f"  Auto-sync{'' if success else ' skipped'}: {message}")
        except Exception as e:
            print(f"  Auto-sync failed: {e}")
        if data_version() != before:
            _warm_up()
        time.sleep(SYNC_INTERVAL)


_warm_up()
threading.Thread(target=_sync_forever, daemon=True).start()

# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 8050)))
