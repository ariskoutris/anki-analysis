#!/usr/bin/env python3
"""
Configuration module for the Anki dashboard.
"""

import os


def get_project_root():
    """Get the project root directory."""
    # __file__ is in src/, so we need to go up one level to get project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_db_path():
    """Get the path to the Anki database."""
    return os.path.join(get_project_root(), 'data', 'anki.db')
