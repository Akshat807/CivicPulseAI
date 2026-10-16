
import sqlite3
from pathlib import Path

# Use the existing database in the project folder.
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "civicpulse.db"


def migrate_database():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}\n"
            "Make sure you are running this inside CivicPulseAI."
        )

    connection = sqlite3.connect(DB_PATH)

    try:
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create the users table without changing existing users/data.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL COLLATE NOCASE UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen'
                    CHECK (role IN ('citizen', 'admin')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Safely add user_id only if it does not already exist.
        cursor.execute("PRAGMA table_info(complaints)")
        complaint_columns = {
            row[1] for row in cursor.fetchall()
        }

        if not complaint_columns:
            raise RuntimeError(
                "The complaints table was not found. "
                "Check your existing database schema before migrating."
            )

        if "user_id" not in complaint_columns:
            cursor.execute("""
                ALTER TABLE complaints
                ADD COLUMN user_id INTEGER REFERENCES users(id)
            """)
            print("Added user_id to complaints.")

        else:
            print("user_id already exists; no change needed.")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_user_id
            ON complaints(user_id)
        """)

        connection.commit()
        print("Migration completed successfully.")
        print("Existing complaint records were preserved.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    migrate_database()
