"""
AnkiWeb Sync Module
Downloads the full collection from AnkiWeb into data/anki.db.

Login happens once with email + password; only the returned sync key is kept
(data/ankiweb.json). Every sync is a one-way full download, so nothing is ever
sent back to AnkiWeb.
"""

import json
import os
import sqlite3
import tempfile
import time
from pathlib import Path
from typing import Tuple, Optional

from anki.collection import Collection
from anki.errors import SyncError, SyncErrorKind
from anki.sync_pb2 import SyncAuth

from .upload_handler import validate_database

LAST_SYNC_FILE = "last_sync.json"
AUTH_FILE = "ankiweb.json"


def is_logged_in(data_root: str) -> bool:
    return (Path(data_root) / AUTH_FILE).exists()


def login(data_root: str, email: str, password: str) -> None:
    """Exchange AnkiWeb credentials for a sync key and store the key. Raises SyncError."""
    with tempfile.TemporaryDirectory() as tmp:
        col = Collection(os.path.join(tmp, "collection.anki2"))
        try:
            auth = col.sync_login(email, password, None)
        finally:
            col.close()
    auth_path = Path(data_root) / AUTH_FILE
    auth_path.touch(mode=0o600)
    auth_path.write_text(json.dumps({"hkey": auth.hkey}))


def logout(data_root: str) -> None:
    (Path(data_root) / AUTH_FILE).unlink(missing_ok=True)


def get_last_sync_time(data_root: str) -> Optional[float]:
    """
    Read the timestamp of the last successful AnkiWeb sync.

    Returns:
        Seconds since epoch, or None if no sync has been recorded
    """
    try:
        with open(Path(data_root) / LAST_SYNC_FILE) as f:
            return float(json.load(f)["timestamp"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def sync_from_ankiweb(data_root: str) -> Tuple[bool, str]:
    """
    Download the collection from AnkiWeb into data/anki.db and record the time
    of every successful sync in data/last_sync.json.

    Returns:
        (success: bool, message: str)
    """
    if not is_logged_in(data_root):
        return False, "Log in to AnkiWeb to sync"

    auth = SyncAuth(hkey=json.loads((Path(data_root) / AUTH_FILE).read_text())["hkey"])
    try:
        with tempfile.TemporaryDirectory(dir=data_root) as tmp:
            staging_db = os.path.join(tmp, "collection.anki2")
            col = Collection(staging_db)
            try:
                # Each account lives on its own sync server; the status call reports which
                status = col.sync_status(auth)
                if status.HasField("new_endpoint"):
                    auth.endpoint = status.new_endpoint
                col.close_for_full_sync()
                col.full_upload_or_download(auth=auth, server_usn=None, upload=False)
            finally:
                col.close()

            # Anki leaves the file in WAL mode; a stale anki.db-wal next to the
            # swapped-in file could otherwise be replayed onto it
            with sqlite3.connect(staging_db) as conn:
                conn.execute("PRAGMA journal_mode=DELETE")
            conn.close()

            valid, validate_msg = validate_database(staging_db)
            if not valid:
                return False, f"Downloaded collection is invalid: {validate_msg}"
            os.replace(staging_db, Path(data_root) / "anki.db")
    except SyncError as e:
        if e.kind == SyncErrorKind.AUTH:
            logout(data_root)
            return False, "AnkiWeb login expired. Log in again."
        return False, f"AnkiWeb sync failed: {e}"
    except Exception as e:
        return False, f"AnkiWeb sync failed: {e}"

    # Best-effort: failing to record the time must not fail the sync
    try:
        (Path(data_root) / LAST_SYNC_FILE).write_text(json.dumps({"timestamp": time.time()}))
    except OSError:
        pass
    return True, "Synced from AnkiWeb"
