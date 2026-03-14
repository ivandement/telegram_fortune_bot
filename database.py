import sqlite3

DB_NAME = "fortune_bot.db"


def get_connection():
    return sqlite3.connect(DB_NAME)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER UNIQUE NOT NULL,
        name TEXT,
        birthdate TEXT,
        free_readings_used INTEGER DEFAULT 0
    )
    """)

    conn.commit()
    conn.close()


def get_user(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT telegram_id, name, birthdate, free_readings_used FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )
    user = cursor.fetchone()
    conn.close()
    return user


def create_or_update_user(telegram_id: int, name: str, birthdate: str):
    conn = get_connection()
    cursor = conn.cursor()

    existing_user = get_user(telegram_id)

    if existing_user:
        cursor.execute(
            """
            UPDATE users
            SET name = ?, birthdate = ?
            WHERE telegram_id = ?
            """,
            (name, birthdate, telegram_id)
        )
    else:
        cursor.execute(
            """
            INSERT INTO users (telegram_id, name, birthdate, free_readings_used)
            VALUES (?, ?, ?, 0)
            """,
            (telegram_id, name, birthdate)
        )

    conn.commit()
    conn.close()


def increment_free_readings(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE users
        SET free_readings_used = free_readings_used + 1
        WHERE telegram_id = ?
        """,
        (telegram_id,)
    )

    conn.commit()
    conn.close()


def get_free_readings_used(telegram_id: int) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT free_readings_used FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )
    result = cursor.fetchone()
    conn.close()

    if result:
        return result[0]
    return 0