import os
import json
import time
import sqlite3

try:
    import zstandard as zstd
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_dir = os.path.dirname(script_dir)
    file_path = os.path.join(project_dir, 'data', 'Core_2K_unzipped', 'collection.anki21b')
    
    print(f"Attempting to decompress: {file_path}")
    
    # Read the compressed data
    with open(file_path, 'rb') as f:
        compressed_data = f.read()
    
    # Initialize the decompressor with a max output size to prevent memory issues
    dctx = zstd.ZstdDecompressor()
    
    # Decompress the data with a timeout
    start_time = time.time()
    try:
        # Use a streaming decompressor to handle potentially large files
        output_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')
        with open(output_path, 'wb') as fout:
            with dctx.stream_reader(compressed_data) as reader:
                while True:
                    chunk = reader.read(16384)  # 16KB chunks
                    if not chunk:
                        break
                    fout.write(chunk)
                    
                    # Check for timeout
                    if time.time() - start_time > 30:  # 30 second timeout
                        print("Decompression taking too long, might be stuck.")
                        break
        
        print(f"Decompression complete. Saved to: {output_path}")
        
        # Try to open as SQLite database
        try:
            conn = sqlite3.connect(output_path)
            cursor = conn.cursor()
            
            # Get table names
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            if tables:
                print("This appears to be a SQLite database with the following tables:")
                for table in tables:
                    print(f"- {table[0]}")
                    
                    # Get row count for each table
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table[0]};")
                        count = cursor.fetchone()[0]
                        print(f"  * {count} rows")
                    except sqlite3.Error:
                        print("  * Could not count rows")
            else:
                print("No tables found in the SQLite database.")
            
            conn.close()
            
        except sqlite3.Error as e:
            print(f"Not a valid SQLite database: {e}")
            
            # Try to interpret as JSON or plain text
            with open(output_path, 'rb') as f:
                data = f.read()
                
            try:
                json_data = json.loads(data)
                print("Data appears to be JSON. First 500 characters:")
                print(json.dumps(json_data, indent=2)[:500])
            except:
                print("Data is not valid JSON. First 500 bytes:")
                try:
                    print(data[:500].decode('utf-8'))
                except:
                    print("Could not decode as UTF-8. Showing hex:")
                    print(data[:100].hex())
            
    except Exception as e:
        print(f"Error during decompression: {e}")

except ImportError:
    print("zstandard module not found. Please install it with: pip install zstandard")
