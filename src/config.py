#!/usr/bin/env python3
"""
Configuration module for AnkiDash.
"""

import os
import json

# __file__ is in src/, so the project root is one level up
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
LAST_VIEW_FILE = os.path.join(DATA_DIR, 'last_view.json')


def get_last_view():
    """Read the last selected deck and chart settings for startup."""
    try:
        with open(LAST_VIEW_FILE) as f:
            deck, time_range, xaxis_mode = json.load(f)[:3]
        if not all(isinstance(v, str) for v in (deck, time_range, xaxis_mode)):
            raise ValueError('Invalid saved view')
        return deck, time_range, xaxis_mode
    except (OSError, ValueError, TypeError, IndexError):
        return 'all', 'all', 'dates'


def get_db_path():
    """Get the path to the Anki database."""
    return os.path.join(DATA_DIR, 'anki.db')
