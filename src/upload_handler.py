"""
Upload handler for Anki backup files.
Handles .apkg extraction and .anki21b decompression.
"""

import io
import os
import sqlite3
import zipfile

import zstandard as zstd


def validate_database(db_path: str) -> tuple[bool, str]:
    """Check that the file is a SQLite database with Anki's cards and revlog tables."""
    try:
        with sqlite3.connect(db_path) as conn:
            tables = {name for (name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
    except sqlite3.Error as e:
        return False, f"Invalid SQLite database: {e}"
    missing = {'cards', 'revlog'} - tables
    if missing:
        return False, f"Missing required tables: {', '.join(sorted(missing))}"
    return True, f"Valid database with {len(tables)} tables"


def process_apkg_upload(file_contents: bytes, data_root: str) -> tuple[bool, str]:
    """
    Process uploaded .apkg file: decompress its collection.anki21b, validate,
    and swap it in as data/anki.db.

    Returns:
        (success: bool, message: str) - Processing result
    """
    os.makedirs(data_root, exist_ok=True)
    staging_path = os.path.join(data_root, '.anki.db.tmp')
    try:
        with zipfile.ZipFile(io.BytesIO(file_contents)) as zf, \
                zf.open('collection.anki21b') as src, open(staging_path, 'wb') as dst:
            zstd.ZstdDecompressor().copy_stream(src, dst)

        valid, validate_msg = validate_database(staging_path)
        if not valid:
            return False, f"Database validation failed: {validate_msg}"

        os.replace(staging_path, os.path.join(data_root, 'anki.db'))
        return True, "Successfully uploaded and processed backup"

    except zipfile.BadZipFile:
        return False, "Invalid or corrupted .apkg file"
    except KeyError:
        return False, "Missing required files: collection.anki21b"
    except zstd.ZstdError as e:
        return False, f"Decompression failed: {e}"
    except Exception as e:
        return False, f"Upload processing error: {e}"
    finally:
        if os.path.exists(staging_path):
            os.remove(staging_path)
