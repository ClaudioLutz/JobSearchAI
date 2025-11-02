"""Quick script to verify database schema."""
import sqlite3

conn = sqlite3.connect('instance/jobsearchai.db')
cursor = conn.cursor()

# Get tables
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

# Get indexes
cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'idx_%'")
indexes = [row[0] for row in cursor.fetchall()]
print('Indexes:', indexes)

# Verify table structures
for table in tables:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f'\n{table} columns: {len(columns)}')

conn.close()
print('\nSchema verification complete!')
