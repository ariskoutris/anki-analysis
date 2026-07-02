"""
Anki Sync Module
Handles direct synchronization with local Anki installation.
"""

import os
import platform
import shutil
import subprocess
import hashlib
from pathlib import Path
from typing import Tuple, List, Optional

from .upload_handler import (
    decompress_anki21b,
    validate_database,
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
        if system == "Darwin":
            # macOS: Anki may run as a .app bundle or as a Python process via aqt
            for pattern in ["Anki.app/Contents/MacOS", "aqt.run()"]:
                result = subprocess.run(
                    ["pgrep", "-f", pattern],
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    return True
            return False
        elif system == "Linux":
            result = subprocess.run(
                ["pgrep", "-xi", "anki"],
                capture_output=True,
                text=True
            )
            if not result.stdout.strip():
                result = subprocess.run(
                    ["pgrep", "-xi", "anki.bin"],
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


def _compute_file_sha256(file_path: Path, chunk_size: int = 1024 * 1024) -> Optional[str]:
    """Compute SHA256 hash for a file."""
    if not file_path.exists() or not file_path.is_file():
        return None

    hasher = hashlib.sha256()
    with file_path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def _files_identical(file_a: Path, file_b: Path) -> bool:
    """Check whether two files are byte-identical using SHA256."""
    hash_a = _compute_file_sha256(file_a)
    hash_b = _compute_file_sha256(file_b)
    return bool(hash_a and hash_b and hash_a == hash_b)


def sync_from_anki(profile_name: Optional[str], data_root: str) -> Tuple[bool, str]:
    """
    Sync Anki collection from local installation to data/anki.db.

    Args:
        profile_name: Name of Anki profile to sync (None for auto-detect)
        data_root: Root data directory for the dashboard

    Returns:
        (success: bool, message: str)
    """
    # Check if Anki is installed
    base_path = get_anki_base_path()
    if not base_path:
        return False, "Anki installation not found on this system"

    # Get available profiles
    profiles = get_anki_profiles()
    if not profiles:
        return False, f"No Anki profiles found in {base_path}"

    # Select profile
    if profile_name:
        # Find specific profile
        matching = [p for p in profiles if p[0] == profile_name]
        if not matching:
            available = ", ".join([p[0] for p in profiles])
            return False, f"Profile '{profile_name}' not found. Available: {available}"
        collection_path = matching[0][1]
        selected_profile = profile_name
    else:
        # No profile specified: use the first one detected
        selected_profile, collection_path = profiles[0]

    # Safety check: Warn if Anki is running
    if is_anki_running():
        return False, (
            "Anki appears to be running. Please close Anki before syncing "
            "to avoid database conflicts."
        )

    # Check for collection lock
    if check_collection_lock(collection_path):
        return False, (
            "Anki collection is locked. Please close Anki and try again."
        )

    data_path = Path(data_root)
    target_db = data_path / "anki.db"
    staging_db = data_path / ".anki.db.tmp"

    try:
        # Fast path: if source collection is unchanged, skip
        if target_db.exists() and collection_path.name == "collection.anki21b":
            # Compare source collection to a cached copy if present
            cached_source = data_path / ".collection.anki21b.cache"
            if cached_source.exists() and _files_identical(collection_path, cached_source):
                return True, f"No changes detected for Anki profile '{selected_profile}'."

        # Ensure data directory exists
        data_path.mkdir(parents=True, exist_ok=True)

        if collection_path.name == "collection.anki21b":
            # Copy source, decompress, validate
            temp_source = data_path / ".collection.anki21b.tmp"
            shutil.copy2(collection_path, temp_source)

            success, decompress_msg = decompress_anki21b(str(temp_source), str(staging_db))
            if not success:
                temp_source.unlink(missing_ok=True)
                staging_db.unlink(missing_ok=True)
                return False, f"Decompression failed: {decompress_msg}"

            valid, validate_msg = validate_database(str(staging_db))
            if not valid:
                temp_source.unlink(missing_ok=True)
                staging_db.unlink(missing_ok=True)
                return False, f"Database validation failed: {validate_msg}"

            # Swap into place atomically
            os.replace(str(staging_db), str(target_db))

            # Cache the source for fast-path comparison next time
            cached_source = data_path / ".collection.anki21b.cache"
            os.replace(str(temp_source), str(cached_source))
        else:
            # collection.anki2 — already a plain SQLite file
            shutil.copy2(collection_path, staging_db)

            valid, validate_msg = validate_database(str(staging_db))
            if not valid:
                staging_db.unlink(missing_ok=True)
                return False, f"Database validation failed: {validate_msg}"

            os.replace(str(staging_db), str(target_db))

        return True, f"Successfully synced Anki profile '{selected_profile}'"

    except PermissionError as e:
        staging_db.unlink(missing_ok=True)
        return False, f"Permission error: {str(e)}"
    except Exception as e:
        staging_db.unlink(missing_ok=True)
        return False, f"Sync error: {str(e)}"


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
