
import sqlite3
from pathlib import Path

# Keep the database beside this Python file
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "civicpulse.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                complaint TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Submitted',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_complaint(city, complaint, category):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO complaints (city, complaint, category)
            VALUES (?, ?, ?)
        """, (city, complaint, category))

        return cursor.lastrowid


def get_complaints(limit=10):
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, city, complaint, category, status, created_at
            FROM complaints
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()


# ------------------------------------
# ADMIN DASHBOARD FUNCTIONS
# ------------------------------------

def get_total_complaints():
    with get_connection() as connection:
        result = connection.execute("""
            SELECT COUNT(*) AS total
            FROM complaints
        """).fetchone()

        return result["total"]


def get_status_counts():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT status, COUNT(*) AS total
            FROM complaints
            GROUP BY status
            ORDER BY total DESC
        """).fetchall()

        return {row["status"]: row["total"] for row in rows}


def get_category_counts():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT category, COUNT(*) AS total
            FROM complaints
            GROUP BY category
            ORDER BY total DESC
        """).fetchall()

        return [
            {
                "category": row["category"],
                "total": row["total"]
            }
            for row in rows
        ]


if __name__ == "__main__":
    initialize_database()

    print("CivicPulse AI database initialized!")
    print("Database location:", DB_PATH)
    print("Total complaints:", get_total_complaints())
    print("Status counts:", get_status_counts())
    print("Category counts:", get_category_counts())
  
def update_complaint_status(complaint_id, status):
    allowed_statuses = {"Submitted", "In Progress", "Resolved"}

    if status not in allowed_statuses:
        return False

    with get_connection() as connection:
        cursor = connection.execute(
            """
            UPDATE complaints
            SET status = ?
            WHERE id = ?
            """,
            (status, complaint_id),
        )
        return cursor.rowcount > 0
 
def get_complaint_by_id(complaint_id):
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, city, complaint, category, status, created_at
            FROM complaints
            WHERE id = ?
            """,
            (complaint_id,),
        ).fetchone()

def initialize_admin_table():
    """Create the admins table if it does not already exist."""
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def create_admin(username, password_hash):
    """Save a new admin account with its password hash."""
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO admins (username, password_hash)
            VALUES (?, ?)
            """,
            (username, password_hash),
        )


def get_admin_by_username(username):
    """Find an admin account by username."""
    with get_connection() as connection:
        return connection.execute(
            """
            SELECT id, username, password_hash
            FROM admins
            WHERE username = ?
            """,
            (username,),
        ).fetchone()
