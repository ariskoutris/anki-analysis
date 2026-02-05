#!/usr/bin/env python3
"""
Configuration module for managing active Anki backup date selection.
This allows the dashboard to switch between different backup snapshots.
"""

import os
from threading import Lock

# Thread-safe storage for the active date
_active_date = None
_lock = Lock()


def get_project_root():
    """Get the project root directory."""
    # __file__ is in src/, so we need to go up one level to get project root
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_available_dates():
    """
    Get a sorted list of available backup dates from the data directory.
    Returns a list of date strings in YYYY-MM-DD or YYYY-MM-DD-HH-MM-SS format (newest first).
    """
    data_dir = os.path.join(get_project_root(), 'data')
    dates = []

    if os.path.exists(data_dir):
        for name in os.listdir(data_dir):
            path = os.path.join(data_dir, name)
            # Check if it's a directory with date format YYYY-MM-DD or YYYY-MM-DD-HH-MM-SS
            if os.path.isdir(path):
                # Accept both formats: YYYY-MM-DD (10 chars) or YYYY-MM-DD-HH-MM-SS (19 chars)
                if len(name) == 10 and name.count('-') == 2:
                    # YYYY-MM-DD format
                    try:
                        parts = name.split('-')
                        if len(parts) == 3 and len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2:
                            dates.append(name)
                    except (ValueError, IndexError):
                        continue
                elif len(name) == 19 and name.count('-') == 5:
                    # YYYY-MM-DD-HH-MM-SS format
                    try:
                        parts = name.split('-')
                        if (len(parts) == 6 and len(parts[0]) == 4 and len(parts[1]) == 2 and 
                            len(parts[2]) == 2 and len(parts[3]) == 2 and len(parts[4]) == 2 and len(parts[5]) == 2):
                            dates.append(name)
                    except (ValueError, IndexError):
                        continue

    dates.sort(reverse=True)  # Newest first
    return dates


def set_active_date(date_str: str):
    """
    Set the active backup date to use for data loading.

    Args:
        date_str: Date string in YYYY-MM-DD format
    """
    global _active_date
    with _lock:
        _active_date = date_str


def get_active_date():
    """
    Get the currently active backup date.
    If none is set, returns the most recent available date.

    Returns:
        Date string in YYYY-MM-DD format or None if no dates available
    """
    global _active_date
    with _lock:
        if _active_date is None:
            # Initialize with the most recent date
            dates = get_available_dates()
            _active_date = dates[0] if dates else None
        return _active_date


def get_db_path(date_str: str = None):
    """
    Get the path to the decompressed Anki database for a specific date.

    Args:
        date_str: Optional date string. If None, uses the active date.

    Returns:
        Full path to the decompressed database file
    """
    if date_str is None:
        date_str = get_active_date()

    if date_str is None:
        raise ValueError("No backup date available")

    return os.path.join(get_project_root(), 'data', date_str, 'decompressed_anki21b.db')


def get_data_folder_path(date_str: str = None):
    """
    Get the path to the data folder for a specific date.

    Args:
        date_str: Optional date string. If None, uses the active date.

    Returns:
        Full path to the data folder
    """
    if date_str is None:
        date_str = get_active_date()

    if date_str is None:
        raise ValueError("No backup date available")

    return os.path.join(get_project_root(), 'data', date_str)
