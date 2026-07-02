#!/usr/bin/env python3
"""
Interactive Anki Learning Dashboard
Entry point: creates the Dash app, sets layout, and registers callbacks.
"""

import os
import subprocess
import sys
import dash

from .constants import INDEX_STRING
from .layout import create_main_layout
from .anki_sync import sync_from_anki

# ---------------------------------------------------------------------------
# 1. Auto-sync from Anki on startup
# ---------------------------------------------------------------------------
data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
os.makedirs(data_dir, exist_ok=True)

try:
    success, message = sync_from_anki(None, data_dir)
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
    PORT = int(os.environ.get('PORT', 8050))

    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true':
        print("\n" + "=" * 60)
        print("  Anki Learning Dashboard")
        print("=" * 60)
        print("\n  Starting server...")
        print(f"  Open http://127.0.0.1:{PORT} in your browser\n")
        print("=" * 60 + "\n")

    try:
        app.run(debug=True, port=PORT)
    except OSError as e:
        if "Address already in use" in str(e) or e.errno == 48:
            print(f"\n  Port {PORT} is already in use.")
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{PORT}", "-sTCP:LISTEN", "-Pn"],
                    capture_output=True, text=True
                )
                if result.stdout.strip():
                    print(f"\n{result.stdout}")
                    print(f"  Kill it with:  kill $(lsof -ti :{PORT})")
            except FileNotFoundError:
                pass
            sys.exit(1)
        raise
