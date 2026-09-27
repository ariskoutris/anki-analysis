#!/usr/bin/env python3
"""
Configuration module for AnkiDash.
"""

import os

# __file__ is in src/, so the project root is one level up
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


def get_db_path():
    """Get the path to the Anki database."""
    return os.path.join(DATA_DIR, 'anki.db')
