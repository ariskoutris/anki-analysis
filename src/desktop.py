#!/usr/bin/env python3
"""
Desktop entry point: runs the dashboard inside a native window (pywebview).

The window opens immediately on a loading screen; the Dash app is imported
(which triggers the Anki auto-sync) and served on a free local port in a
background thread. Closing the window exits the process and the server with it.

Run with:  uv run python -m src.desktop
"""

import html
import logging
import socket
import threading
import time
import traceback

import webview

from .constants import COLORS

TITLE = "Anki Learning Dashboard"

LOADING_HTML = f"""
<html><body style="margin:0;height:100vh;display:flex;flex-direction:column;
  align-items:center;justify-content:center;background:{COLORS['bg_canvas']};
  color:{COLORS['text_secondary']};font:14px -apple-system,sans-serif">
  <div style="width:28px;height:28px;border:3px solid {COLORS['border']};
    border-top-color:{COLORS['primary']};border-radius:50%;
    animation:spin .8s linear infinite"></div>
  <p style="margin-top:18px">Syncing from Anki and loading dashboard…</p>
  <style>@keyframes spin {{ to {{ transform: rotate(360deg) }} }}</style>
</body></html>
"""


def _free_port():
    """Ask the OS for an unused port so we never clash with a dev server on 8050."""
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _wait_for_server(port, timeout=60):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


def _start_dashboard(window):
    """Runs on pywebview's worker thread once the window is up."""
    try:
        from .app import app  # slow: auto-sync + data layer imports

        # Per-request access logs would grow the launcher's log file forever
        logging.getLogger('werkzeug').setLevel(logging.WARNING)
        port = _free_port()
        threading.Thread(
            target=lambda: app.run(debug=False, port=port),
            daemon=True,
        ).start()

        if not _wait_for_server(port):
            raise RuntimeError(f"Dashboard server did not start on port {port}")
        window.load_url(f"http://127.0.0.1:{port}")
    except Exception:
        traceback.print_exc()
        window.load_html(
            f"<pre style='color:{COLORS['danger']};background:{COLORS['bg_canvas']};"
            f"padding:24px;margin:0;min-height:100vh'>"
            f"Failed to start dashboard:\n\n{html.escape(traceback.format_exc())}</pre>"
        )


def main():
    window = webview.create_window(
        TITLE,
        html=LOADING_HTML,
        width=1440,
        height=900,
        min_size=(900, 600),
        background_color=COLORS['bg_canvas'],
    )
    webview.start(_start_dashboard, window)


if __name__ == '__main__':
    main()
