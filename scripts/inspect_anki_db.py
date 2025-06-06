import sqlite3
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(script_dir)
db_path = os.path.join(project_dir, 'data', 'decompressed_anki21b.db')
print(f"Trying to connect to: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# List all tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

print(f"Tables in {os.path.basename(db_path)}:")
for table in tables:
    print(table[0])

# Get table schema information
print("\nTable Schema Information:")
for table_name in [table[0] for table in tables]:
    print(f"\nSchema for '{table_name}' table:")
    cursor.execute(f"PRAGMA table_info({table_name});")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col[1]} ({col[2]})")

# Example: Print the first 5 rows from the 'notes' table if it exists
if ('notes',) in tables:
    print("\nFirst 5 rows from 'notes' table:")
    cursor.execute("SELECT * FROM notes LIMIT 5;")
    notes_sample = cursor.fetchall()
    for row in notes_sample:
        print(row)
    
    # Count total notes
    cursor.execute("SELECT COUNT(*) FROM notes;")
    count = cursor.fetchone()[0]
    print(f"\nTotal notes count: {count}")

# Example: Print the first 5 rows from the 'cards' table if it exists
if ('cards',) in tables:
    print("\nFirst 5 rows from 'cards' table:")
    cursor.execute("SELECT * FROM cards LIMIT 5;")
    cards_sample = cursor.fetchall()
    for row in cards_sample:
        print(row)
    
    # Count total cards
    cursor.execute("SELECT COUNT(*) FROM cards;")
    count = cursor.fetchone()[0]
    print(f"\nTotal cards count: {count}")

# Check if col table exists and retrieve deck information
if ('col',) in tables:
    print("\nCollection Information:")
    cursor.execute("SELECT * FROM col;")
    col_data = cursor.fetchall()
    for row in col_data:
        print(row)

conn.close()
