import sqlite3
from app.core.config import settings


def init_db():
    conn = sqlite3.connect(settings.DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicines (
        id TEXT PRIMARY KEY,
        code TEXT,
        name TEXT,
        gtin TEXT,
        serial_number TEXT,
        expiration_date TEXT,
        manufacturer TEXT,
        symptoms TEXT,
        added_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS image_sources (
        gtin TEXT PRIMARY KEY,
        source TEXT NOT NULL CHECK(source IN ('google', 'yandex'))
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicine_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            medicine_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('active', 'archive'))
        );
    """)

    # Добавление активных статусов по умолчанию
    cursor.execute("""
        INSERT INTO medicine_status (medicine_id, status)
        SELECT m.id, 'active'
        FROM medicines m
        LEFT JOIN medicine_status s ON m.id = s.medicine_id
        WHERE s.medicine_id IS NULL;
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS medicine_applications (
        medicine_id TEXT NOT NULL,
        application_id INTEGER NOT NULL,
        PRIMARY KEY (medicine_id, application_id),
        FOREIGN KEY (medicine_id) REFERENCES medicines(id) ON DELETE CASCADE,
        FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    conn.close()