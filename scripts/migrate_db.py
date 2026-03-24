"""Database migration script — add Oura fields to wellness table.

Run this once to update existing databases with new Oura Ring fields.
"""

import sqlite3
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from engine import database


def migrate():
    """Add new columns to wellness table if they don't exist."""
    with database.get_db() as conn:
        # Check current columns
        cursor = conn.execute("PRAGMA table_info(wellness)")
        existing_cols = {row[1] for row in cursor.fetchall()}
        
        # Columns to add
        new_columns = {
            "body_temp_deviation": "REAL",
            "source": "TEXT DEFAULT 'intervals.icu'",
        }
        
        added = []
        for col, dtype in new_columns.items():
            if col not in existing_cols:
                conn.execute(f"ALTER TABLE wellness ADD COLUMN {col} {dtype}")
                added.append(col)
                print(f"✓ Added column: {col}")
        
        if added:
            print(f"\nMigration complete. Added {len(added)} new column(s).")
        else:
            print("\nNo migration needed. All columns already exist.")
        
        # Show current schema
        print("\nCurrent wellness table schema:")
        cursor = conn.execute("PRAGMA table_info(wellness)")
        for row in cursor.fetchall():
            print(f"  - {row[1]}: {row[2]}")


if __name__ == "__main__":
    migrate()
