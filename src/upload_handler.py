"""
Upload handler for Anki backup files.
Handles .apkg extraction and .anki21b decompression.
"""

import os
import time
import sqlite3
import zipfile
import tempfile
import shutil
from datetime import datetime

try:
    import zstandard as zstd
    ZSTD_AVAILABLE = True
except ImportError:
    ZSTD_AVAILABLE = False


def decompress_anki21b(source_path: str, output_path: str) -> tuple[bool, str]:
    """
    Decompress a .anki21b file to SQLite database.

    Args:
        source_path: Path to collection.anki21b file
        output_path: Path where decompressed_anki21b.db will be saved

    Returns:
        (success: bool, message: str) - Success status and descriptive message
    """
    if not ZSTD_AVAILABLE:
        return False, "zstandard library not installed. Run: pip install zstandard"

    if not os.path.exists(source_path):
        return False, f"Source file not found: {source_path}"

    try:
        # Read compressed data
        with open(source_path, 'rb') as f:
            compressed_data = f.read()

        # Initialize decompressor
        dctx = zstd.ZstdDecompressor()

        # Decompress with timeout
        start_time = time.time()
        with open(output_path, 'wb') as fout:
            with dctx.stream_reader(compressed_data) as reader:
                while True:
                    chunk = reader.read(16384)  # 16KB chunks
                    if not chunk:
                        break
                    fout.write(chunk)

                    # 30 second timeout
                    if time.time() - start_time > 30:
                        return False, "Decompression timeout (>30s)"

        return True, f"Successfully decompressed to {output_path}"

    except zstd.ZstdError as e:
        return False, f"Decompression failed: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error during decompression: {str(e)}"


def validate_database(db_path: str) -> tuple[bool, str]:
    """
    Validate that the decompressed file is a valid SQLite database with expected tables.

    Args:
        db_path: Path to the database file

    Returns:
        (success: bool, message: str) - Validation result
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Get table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]

        # Check for required tables
        required_tables = ['cards', 'revlog']
        missing_tables = [t for t in required_tables if t not in tables]

        conn.close()

        if missing_tables:
            return False, f"Missing required tables: {', '.join(missing_tables)}"

        return True, f"Valid database with {len(tables)} tables"

    except sqlite3.Error as e:
        return False, f"Invalid SQLite database: {str(e)}"
    except Exception as e:
        return False, f"Database validation error: {str(e)}"


def validate_apkg_contents(extracted_dir: str) -> tuple[bool, str]:
    """
    Validate that extracted .apkg contains required files.

    Args:
        extracted_dir: Directory where .apkg was extracted

    Returns:
        (success: bool, message: str) - Validation result
    """
    required_files = ['collection.anki21b']
    missing_files = []

    for filename in required_files:
        file_path = os.path.join(extracted_dir, filename)
        if not os.path.exists(file_path):
            missing_files.append(filename)

    if missing_files:
        return False, f"Missing required files: {', '.join(missing_files)}"

    return True, "All required files present"


def generate_unique_date_folder(data_dir: str) -> str:
    """
    Generate a unique date-based folder name, adding timestamp if date already exists.

    Args:
        data_dir: Base data directory

    Returns:
        Unique folder name (YYYY-MM-DD or YYYY-MM-DD-HH-MM-SS)
    """
    base_folder = datetime.now().strftime('%Y-%m-%d')
    folder_path = os.path.join(data_dir, base_folder)

    if not os.path.exists(folder_path):
        return base_folder

    # Folder exists, add timestamp
    timestamp = datetime.now().strftime('%H-%M-%S')
    return f'{base_folder}-{timestamp}'


def process_apkg_upload(file_contents: bytes, data_root: str) -> tuple[bool, str, str]:
    """
    Process uploaded .apkg file: extract, decompress, validate.

    Args:
        file_contents: Raw bytes of uploaded .apkg file
        data_root: Root data directory (e.g., 'data/')

    Returns:
        (success: bool, message: str, folder_name: str) - Processing result and folder name
    """
    temp_dir = None
    folder_name = None

    try:
        # Create temporary directory for extraction
        temp_dir = tempfile.mkdtemp()

        # Write uploaded file to temp location
        temp_apkg_path = os.path.join(temp_dir, 'upload.apkg')
        with open(temp_apkg_path, 'wb') as f:
            f.write(file_contents)

        # Extract ZIP
        try:
            with zipfile.ZipFile(temp_apkg_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
        except zipfile.BadZipFile:
            return False, "Invalid or corrupted .apkg file", None

        # Validate contents
        valid, msg = validate_apkg_contents(temp_dir)
        if not valid:
            return False, msg, None

        # Generate unique folder name
        folder_name = generate_unique_date_folder(data_root)
        target_folder = os.path.join(data_root, folder_name)

        # Create target folder
        os.makedirs(target_folder, exist_ok=True)

        # Move files to target folder
        files_to_move = ['collection.anki21b', 'collection.anki2', 'media', 'meta']
        for item in files_to_move:
            source = os.path.join(temp_dir, item)
            if os.path.exists(source):
                target = os.path.join(target_folder, item)
                if os.path.isdir(source):
                    shutil.copytree(source, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(source, target)

        # Decompress collection.anki21b
        source_anki21b = os.path.join(target_folder, 'collection.anki21b')
        output_db = os.path.join(target_folder, 'decompressed_anki21b.db')

        success, decompress_msg = decompress_anki21b(source_anki21b, output_db)
        if not success:
            # Clean up failed upload
            shutil.rmtree(target_folder, ignore_errors=True)
            return False, f"Decompression failed: {decompress_msg}", None

        # Validate database
        valid, validate_msg = validate_database(output_db)
        if not valid:
            # Clean up failed upload
            shutil.rmtree(target_folder, ignore_errors=True)
            return False, f"Database validation failed: {validate_msg}", None

        return True, f"Successfully uploaded backup as {folder_name}", folder_name

    except PermissionError as e:
        return False, f"Permission error: {str(e)}", None
    except Exception as e:
        return False, f"Upload processing error: {str(e)}", None
    finally:
        # Clean up temporary directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
