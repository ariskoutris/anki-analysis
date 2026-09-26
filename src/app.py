#!/usr/bin/env python3
"""
Interactive Anki Learning Dashboard
Entry point: creates the Dash app, sets layout, and registers callbacks.
"""

import os
import dash

from .constants import INDEX_STRING
from .layout import create_main_layout
from .anki_sync import sync_from_anki
from .config import DATA_DIR

# ---------------------------------------------------------------------------
# 1. Auto-sync from Anki on startup
# ---------------------------------------------------------------------------
os.makedirs(DATA_DIR, exist_ok=True)

try:
    success, message = sync_from_anki(DATA_DIR)
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
    title="Anki Learning Dashboard",
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

# ---------------------------------------------------------------------------
# 5. Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True, port=int(os.environ.get('PORT', 8050)))
