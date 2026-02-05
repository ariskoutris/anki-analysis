"""
Anki Sync Module
Handles direct synchronization with local Anki installation.
"""

import os
import platform
import shutil
import sqlite3
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Tuple, List, Optional

from .upload_handler import (
    decompress_anki21b,
    validate_database,
    generate_unique_date_folder,
)


def get_anki_base_path() -> Optional[Path]:
    """
    Get the base Anki2 directory based on the operating system.
    
    Returns:
        Path to Anki2 directory or None if not found
    """
    system = platform.system()
    home = Path.home()
    
    if system == "Linux":
        path = home / ".local" / "share" / "Anki2"
    elif system == "Darwin":  # macOS
        path = home / "Library" / "Application Support" / "Anki2"
    elif system == "Windows":
        appdata = os.environ.get("APPDATA")
        if not appdata:
            return None
        path = Path(appdata) / "Anki2"
    else:
        return None
    
    return path if path.exists() else None


def get_anki_profiles() -> List[Tuple[str, Path]]:
    """
    Get all Anki profiles (users) with their collection paths.
    
    Returns:
        List of tuples: (profile_name, collection_path)
    """
    base_path = get_anki_base_path()
    if not base_path:
        return []
    
    profiles = []
    try:
        for item in base_path.iterdir():
            if not item.is_dir():
                continue
            
            # Check for both collection formats:
            # - collection.anki21b (newer compressed format)
            # - collection.anki2 (older SQLite format)
            collection_anki21b = item / "collection.anki21b"
            collection_anki2 = item / "collection.anki2"
            
            if collection_anki21b.exists():
                profiles.append((item.name, collection_anki21b))
            elif collection_anki2.exists():
                profiles.append((item.name, collection_anki2))
    except (PermissionError, OSError):
        return []
    
    return profiles


def is_anki_running() -> bool:
    """
    Check if Anki is currently running to avoid database conflicts.
    
    Returns:
        True if Anki appears to be running, False otherwise
    """
    system = platform.system()
    
    try:
        if system in ("Linux", "Darwin"):
            # Check for anki process more specifically
            # Look for the actual Anki executable, not just any process with "anki" in the path
            result = subprocess.run(
                ["pgrep", "-i", "^anki$"],
                capture_output=True,
                text=True
            )
            # Also check for anki.bin (Linux package name)
            if not result.stdout.strip():
                result = subprocess.run(
                    ["pgrep", "-i", "^anki.bin$"],
                    capture_output=True,
                    text=True
                )
            return bool(result.stdout.strip())
        elif system == "Windows":
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq anki.exe"],
                capture_output=True,
                text=True
            )
            return "anki.exe" in result.stdout.lower()
    except (FileNotFoundError, subprocess.SubprocessError):
        # If we can't check, assume it's not running
        pass
    
    return False


def check_collection_lock(collection_path: Path) -> bool:
    """
    Check if the Anki collection has an active lock file.
    
    Args:
        collection_path: Path to collection.anki21b
        
    Returns:
        True if locked (Anki is using it), False otherwise
    """
    # Anki typically creates collection.anki21b.lock or similar
    lock_patterns = [
        collection_path.parent / f"{collection_path.name}.lock",
        collection_path.parent / ".lock",
    ]
    
    for lock_file in lock_patterns:
        if lock_file.exists():
            return True
    
    return False


def sync_from_anki(profile_name: Optional[str], data_root: str) -> Tuple[bool, str, Optional[str]]:
    """
    Sync Anki collection from local installation to dashboard data folder.
    
    Args:
        profile_name: Name of Anki profile to sync (None for auto-detect)
        data_root: Root data directory for the dashboard
        
    Returns:
        (success: bool, message: str, folder_name: Optional[str])
    """
    # Check if Anki is installed
    base_path = get_anki_base_path()
    if not base_path:
        return False, "Anki installation not found on this system", None
    
    # Get available profiles
    profiles = get_anki_profiles()
    if not profiles:
        return False, f"No Anki profiles found in {base_path}", None
    
    # Select profile
    if profile_name:
        # Find specific profile
        matching = [p for p in profiles if p[0] == profile_name]
        if not matching:
            available = ", ".join([p[0] for p in profiles])
            return False, f"Profile '{profile_name}' not found. Available: {available}", None
        collection_path = matching[0][1]
        selected_profile = profile_name
    else:
        # Use first profile (usually "User 1")
        selected_profile, collection_path = profiles[0]
    
    # Safety check: Warn if Anki is running
    if is_anki_running():
        return False, (
            "Anki appears to be running. Please close Anki before syncing "
            "to avoid database conflicts."
        ), None
    
    # Check for collection lock
    if check_collection_lock(collection_path):
        return False, (
            "Anki collection is locked. Please close Anki and try again."
        ), None
    
    try:
        # Generate unique folder name for this sync
        folder_name = generate_unique_date_folder(data_root)
        target_folder = os.path.join(data_root, folder_name)
        os.makedirs(target_folder, exist_ok=True)
        
        output_db = os.path.join(target_folder, "decompressed_anki21b.db")
        
        # Handle both collection formats
        if collection_path.name == "collection.anki21b":
            # Compressed format - needs decompression
            target_anki21b = os.path.join(target_folder, "collection.anki21b")
            shutil.copy2(collection_path, target_anki21b)
            
            # Decompress to SQLite database
            success, decompress_msg = decompress_anki21b(target_anki21b, output_db)
            
            if not success:
                # Clean up on failure
                shutil.rmtree(target_folder, ignore_errors=True)
                return False, f"Decompression failed: {decompress_msg}", None
        else:
            # collection.anki2 - already SQLite, just copy
            shutil.copy2(collection_path, output_db)
        
        # Validate database
        valid, validate_msg = validate_database(output_db)
        if not valid:
            # Clean up on failure
            shutil.rmtree(target_folder, ignore_errors=True)
            return False, f"Database validation failed: {validate_msg}", None
        
        success_message = (
            f"Successfully synced from Anki profile '{selected_profile}' "
            f"to backup {folder_name}"
        )
        return True, success_message, folder_name
        
    except PermissionError as e:
        return False, f"Permission error: {str(e)}", None
    except Exception as e:
        return False, f"Sync error: {str(e)}", None


def get_sync_info() -> dict:
    """
    Get information about Anki sync availability.
    
    Returns:
        Dictionary with sync status information
    """
    base_path = get_anki_base_path()
    profiles = get_anki_profiles()
    anki_running = is_anki_running()
    
    return {
        "anki_installed": base_path is not None,
        "anki_path": str(base_path) if base_path else None,
        "profiles_found": len(profiles),
        "profiles": [p[0] for p in profiles],
        "anki_running": anki_running,
        "can_sync": len(profiles) > 0 and not anki_running,
    }
