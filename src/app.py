#!/usr/bin/env python3
"""
AnkiDash: interactive Anki learning dashboard
Entry point: creates the Dash app, sets layout, and registers callbacks.
"""

import json
import os
import dash

from .constants import INDEX_STRING
from .layout import create_main_layout
from .anki_sync import sync_from_ankiweb
from .config import DATA_DIR

# ---------------------------------------------------------------------------
# 1. Auto-sync from AnkiWeb on startup
# ---------------------------------------------------------------------------
os.makedirs(DATA_DIR, exist_ok=True)

try:
    success, message = sync_from_ankiweb(DATA_DIR)
    if success:
        print(f"  Auto-sync: {message}")
    else:
        print(f"  Auto-sync skipped: {message}")
except Exception as e:
    print(f"  Auto-sync failed: {e}")

# ---------------------------------------------------------------------------
# 2. Create the Dash application
# ---------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    title="AnkiDash",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.index_string = INDEX_STRING

# ---------------------------------------------------------------------------
# 3. Set layout
# ---------------------------------------------------------------------------
app.layout = create_main_layout()

# ---------------------------------------------------------------------------
# 4. Register all callbacks (side-effect import)
# ---------------------------------------------------------------------------
from . import callbacks  # noqa: F401, E402

# Warm the data caches for the last-used view, so the first page load is instant
try:
    try:
        with open(callbacks.LAST_VIEW_FILE) as f:
            deck, time_range, xaxis_mode, load_basis = json.load(f)
    except (OSError, ValueError):
        deck, time_range, xaxis_mode, load_basis = 'all', 'all', 'dates', 'interval'
    callbacks.update_overview_container(0, '/', deck, load_basis)
    callbacks.update_session_charts(time_range, xaxis_mode, 0, deck)
    callbacks.update_card_charts(0, deck, time_range, xaxis_mode, load_basis)
except Exception as e:
    print(f"  Cache warm-up skipped: {e}")

# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 8050)))
