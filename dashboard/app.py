#!/usr/bin/env python3
"""
Interactive Anki Learning Dashboard
Entry point: creates the Dash app, sets layout, and registers callbacks.
"""

import os
import sys

# Ensure project root is importable for anki_config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import dash
from anki_config import get_active_date, get_available_dates as get_config_available_dates

from .constants import INDEX_STRING
from .layout import create_main_layout

# ---------------------------------------------------------------------------
# 1. Create the Dash application
# ---------------------------------------------------------------------------
app = dash.Dash(
    __name__,
    title="Anki Learning Dashboard",
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)
app.index_string = INDEX_STRING

# ---------------------------------------------------------------------------
# 2. Compute initial state and set layout
# ---------------------------------------------------------------------------
DATE_OPTIONS = [{'label': d, 'value': d} for d in get_config_available_dates()]
ACTIVE_DATE = get_active_date()

app.layout = create_main_layout(DATE_OPTIONS, ACTIVE_DATE)

# ---------------------------------------------------------------------------
# 3. Register all callbacks (side-effect import)
# ---------------------------------------------------------------------------
from . import callbacks  # noqa: F401, E402

# ---------------------------------------------------------------------------
# 4. Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("\n" + "=" * 60)
        print("  Anki Learning Dashboard")
        print("=" * 60)
        print("\n  Starting server...")
        print("  Open http://127.0.0.1:8050 in your browser\n")
        print("=" * 60 + "\n")

    app.run(debug=True, port=8050)
