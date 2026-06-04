import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "wardrobe.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS clothing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            color TEXT,
            warmth_level INTEGER DEFAULT 2,
            waterproof INTEGER DEFAULT 0,
            formal_level INTEGER DEFAULT 1,
            notes TEXT,
            image_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS favorite_outfits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            outfit_text TEXT NOT NULL,
            weather_summary TEXT,
            calendar_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add image_path column safely if old DB exists
    try:
        cur.execute("ALTER TABLE clothing_items ADD COLUMN image_path TEXT")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def add_clothing_item(
    name,
    category,
    color="",
    warmth_level=2,
    waterproof=0,
    formal_level=1,
    notes="",
    image_path=""
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO clothing_items
        (name, category, color, warmth_level, waterproof, formal_level, notes, image_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        category,
        color,
        warmth_level,
        waterproof,
        formal_level,
        notes,
        image_path
    ))

    conn.commit()
    item_id = cur.lastrowid
    conn.close()

    return item_id


def get_clothing_items():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM clothing_items
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def delete_clothing_item(item_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM clothing_items WHERE id = ?", (item_id,))
    deleted = cur.rowcount > 0

    conn.commit()
    conn.close()

    return deleted


def save_favorite_outfit(
    title,
    outfit_text,
    weather_summary="",
    calendar_summary=""
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO favorite_outfits
        (title, outfit_text, weather_summary, calendar_summary)
        VALUES (?, ?, ?, ?)
    """, (
        title,
        outfit_text,
        weather_summary,
        calendar_summary
    ))

    conn.commit()
    favorite_id = cur.lastrowid
    conn.close()

    return favorite_id


def get_favorite_outfits():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM favorite_outfits
        ORDER BY id DESC
    """)

    rows = cur.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def delete_favorite_outfit(outfit_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM favorite_outfits WHERE id = ?", (outfit_id,))
    deleted = cur.rowcount > 0

    conn.commit()
    conn.close()

    return deleted