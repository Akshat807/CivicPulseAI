
import sqlite3
from pathlib import Path
from math import ceil
from datetime import date, timedelta


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "civicpulse.db"

ALLOWED_STATUSES = {"Submitted", "In Progress", "Resolved"}
ALLOWED_PRIORITIES = {"Critical", "High", "Medium", "Low"}
ALLOWED_CATEGORIES = {
    "Road Damage",
    "Water Issue",
    "Electrical Hazard",
    "Flooding",
    "Waste Management",
}


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def validate_coordinates(latitude, longitude):
    """Validate optional GPS coordinates. Return (latitude, longitude)."""
    if latitude in (None, "") or longitude in (None, ""):
        return None, None

    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return None, None

    if not (-90 <= latitude <= 90):
        return None, None

    if not (-180 <= longitude <= 180):
        return None, None

    return latitude, longitude


def initialize_database():
    """Create tables and safely migrate existing data."""
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

        connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'citizen',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)

        columns = connection.execute(
            "PRAGMA table_info(complaints)"
        ).fetchall()

        column_names = {column["name"] for column in columns}

        migrations = [
            (
                "user_id",
                "ALTER TABLE complaints ADD COLUMN user_id INTEGER "
                "REFERENCES users(id)",
            ),
            (
                "priority",
                "ALTER TABLE complaints ADD COLUMN priority "
                "TEXT NOT NULL DEFAULT 'Medium'",
            ),
            (
                "priority_score",
                "ALTER TABLE complaints ADD COLUMN priority_score "
                "INTEGER NOT NULL DEFAULT 40",
            ),
            (
                "priority_reason",
                """ALTER TABLE complaints ADD COLUMN priority_reason TEXT
                   NOT NULL DEFAULT
                   'Priority details unavailable for this existing complaint.'""",
            ),
            (
                "latitude",
                "ALTER TABLE complaints ADD COLUMN latitude REAL",
            ),
            (
                "longitude",
                "ALTER TABLE complaints ADD COLUMN longitude REAL",
            ),
            (
                "location_address",
                "ALTER TABLE complaints ADD COLUMN location_address "
                "TEXT NOT NULL DEFAULT ''",
            ),
            (
                "resolved_at",
                "ALTER TABLE complaints ADD COLUMN resolved_at TEXT",
            ),
        ]

        for column_name, sql in migrations:
            if column_name not in column_names:
                connection.execute(sql)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_user_id
            ON complaints(user_id)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_priority
            ON complaints(priority)
        """)

        connection.execute("""
            CREATE INDEX IF NOT EXISTS idx_complaints_coordinates
            ON complaints(latitude, longitude)
        """)

        connection.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_complaint(
    city,
    complaint,
    category,
    user_id=None,
    priority="Medium",
    priority_score=40,
    priority_reason="",
    latitude=None,
    longitude=None,
    location_address="",
):
    """Save a complaint with optional location data."""

    if priority not in ALLOWED_PRIORITIES:
        priority = "Medium"

    try:
        priority_score = max(0, min(int(priority_score), 100))
    except (TypeError, ValueError):
        priority_score = 40

    priority_reason = (priority_reason or "").strip()
    if not priority_reason:
        priority_reason = "Priority details unavailable."

    latitude, longitude = validate_coordinates(latitude, longitude)
    location_address = (location_address or "").strip()[:300]

    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO complaints (
                city,
                complaint,
                category,
                user_id,
                priority,
                priority_score,
                priority_reason,
                latitude,
                longitude,
                location_address
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city,
            complaint,
            category,
            user_id,
            priority,
            priority_score,
            priority_reason,
            latitude,
            longitude,
            location_address,
        ))

        return cursor.lastrowid


def get_complaints(limit=10):
    with get_connection() as connection:
        return connection.execute("""
            SELECT
                id, city, complaint, category, status, priority,
                priority_score, priority_reason, created_at,
                latitude, longitude, location_address, resolved_at
            FROM complaints
            ORDER BY id DESC
            LIMIT ?
        """, (limit,)).fetchall()


def get_filtered_complaints(
    search="",
    status="",
    category="",
    page=1,
    per_page=10,
    priority="",
):
    search = (search or "").strip()
    status = status if status in ALLOWED_STATUSES else ""
    category = category if category in ALLOWED_CATEGORIES else ""
    priority = priority if priority in ALLOWED_PRIORITIES else ""

    try:
        page = max(int(page or 1), 1)
    except (TypeError, ValueError):
        page = 1

    try:
        per_page = max(min(int(per_page or 10), 100), 1)
    except (TypeError, ValueError):
        per_page = 10

    conditions = []
    parameters = []

    if search:
        conditions.append("""
            (
                CAST(id AS TEXT) LIKE ?
                OR city LIKE ?
                OR complaint LIKE ?
                OR category LIKE ?
                OR priority LIKE ?
                OR priority_reason LIKE ?
                OR location_address LIKE ?
            )
        """)
        pattern = f"%{search}%"
        parameters.extend([pattern] * 7)

    if status:
        conditions.append("status = ?")
        parameters.append(status)

    if category:
        conditions.append("category = ?")
        parameters.append(category)

    if priority:
        conditions.append("priority = ?")
        parameters.append(priority)

    where_clause = (
        " WHERE " + " AND ".join(conditions)
        if conditions else ""
    )

    with get_connection() as connection:
        total = connection.execute(
            "SELECT COUNT(*) AS total FROM complaints" + where_clause,
            parameters,
        ).fetchone()["total"]

        total_pages = max(ceil(total / per_page), 1)
        page = min(page, total_pages)
        offset = (page - 1) * per_page

        complaints = connection.execute("""
            SELECT
                id, city, complaint, category, status, priority,
                priority_score, priority_reason, created_at,
                latitude, longitude, location_address, resolved_at
            FROM complaints
        """ + where_clause + """
            ORDER BY
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END,
                id DESC
            LIMIT ? OFFSET ?
        """, parameters + [per_page, offset]).fetchall()

    return {
        "complaints": complaints,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
    }


def get_complaints_by_user(user_id, limit=100):
    with get_connection() as connection:
        return connection.execute("""
            SELECT
                id, city, complaint, category, status, priority,
                priority_score, priority_reason, created_at,
                latitude, longitude, location_address, resolved_at
            FROM complaints
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()


def get_total_complaints():
    with get_connection() as connection:
        return connection.execute(
            "SELECT COUNT(*) AS total FROM complaints"
        ).fetchone()["total"]


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
            {"category": row["category"], "total": row["total"]}
            for row in rows
        ]


def get_priority_counts():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT priority, COUNT(*) AS total
            FROM complaints
            GROUP BY priority
        """).fetchall()

        return {row["priority"]: row["total"] for row in rows}


def update_complaint_status(complaint_id, status):
    """Update status and record the actual resolution timestamp."""
    if status not in ALLOWED_STATUSES:
        return False

    with get_connection() as connection:
        if status == "Resolved":
            cursor = connection.execute("""
                UPDATE complaints
                SET status = ?,
                    resolved_at = CASE
                        WHEN status = 'Resolved' AND resolved_at IS NOT NULL
                            THEN resolved_at
                        ELSE CURRENT_TIMESTAMP
                    END
                WHERE id = ?
            """, (status, complaint_id))
        else:
            cursor = connection.execute("""
                UPDATE complaints
                SET status = ?, resolved_at = NULL
                WHERE id = ?
            """, (status, complaint_id))

        return cursor.rowcount > 0


def get_resolution_analytics():
    """Calculate resolution time from real recorded timestamps only."""
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                COUNT(*) AS resolved_with_timestamps,
                AVG(
                    (julianday(resolved_at) - julianday(created_at)) * 1440.0
                ) AS average_minutes
            FROM complaints
            WHERE status = 'Resolved'
              AND resolved_at IS NOT NULL
              AND created_at IS NOT NULL
              AND julianday(resolved_at) IS NOT NULL
              AND julianday(created_at) IS NOT NULL
        """).fetchone()

    average_minutes = row["average_minutes"]

    if average_minutes is not None:
        average_minutes = max(0.0, float(average_minutes))

    average_hours = (
        average_minutes / 60.0
        if average_minutes is not None else None
    )

    return {
        "resolved_with_timestamps": row["resolved_with_timestamps"],
        "average_minutes": average_minutes,
        "average_hours": average_hours,
    }


def get_complaint_by_id(complaint_id):
    with get_connection() as connection:
        return connection.execute("""
            SELECT
                id, city, complaint, category, status, priority,
                priority_score, priority_reason, created_at,
                latitude, longitude, location_address, resolved_at
            FROM complaints
            WHERE id = ?
        """, (complaint_id,)).fetchone()


def get_map_complaints():
    """Return complaints with coordinates for the admin map."""
    with get_connection() as connection:
        return connection.execute("""
            SELECT
                id, city, category, status, priority,
                priority_score, latitude, longitude,
                location_address, created_at, resolved_at
            FROM complaints
            ORDER BY id DESC
        """).fetchall()


def initialize_admin_table():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def create_admin(username, password_hash):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO admins (username, password_hash)
            VALUES (?, ?)
        """, (username, password_hash))


def get_admin_by_username(username):
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, username, password_hash
            FROM admins
            WHERE username = ?
        """, (username,)).fetchone()


def create_citizen(name, email, password_hash):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO users (name, email, password_hash, role)
            VALUES (?, ?, ?, 'citizen')
        """, (name, email, password_hash))

        return cursor.lastrowid


def get_citizen_by_email(email):
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, name, email, password_hash, role, created_at
            FROM users
            WHERE email = ? AND role = 'citizen'
        """, (email,)).fetchone()


def get_citizen_by_id(user_id):
    with get_connection() as connection:
        return connection.execute("""
            SELECT id, name, email, role, created_at
            FROM users
            WHERE id = ? AND role = 'citizen'
        """, (user_id,)).fetchone()


def get_daily_complaint_counts(days=7):
    """Return daily complaint counts for the last N calendar days."""
    try:
        days = max(1, min(int(days), 90))
    except (TypeError, ValueError):
        days = 7

    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                date(created_at) AS complaint_date,
                COUNT(*) AS total
            FROM complaints
            WHERE date(created_at) >= date('now', ?)
              AND date(created_at) <= date('now')
            GROUP BY date(created_at)
            ORDER BY complaint_date ASC
        """, (f"-{days - 1} days",)).fetchall()

    counts = {
        row["complaint_date"]: row["total"]
        for row in rows
    }

    today = date.today()
    result = []

    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        result.append({
            "date": day.isoformat(),
            "total": counts.get(day.isoformat(), 0),
        })

    return result


if __name__ == "__main__":
    initialize_database()
    print("CivicPulse AI database initialized!")
    print("Database location:", DB_PATH)
    print("Total complaints:", get_total_complaints())
    print("Status counts:", get_status_counts())
    print("Category counts:", get_category_counts())
    print("Priority counts:", get_priority_counts())
    print("Resolution analytics:", get_resolution_analytics())
