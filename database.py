import os
from typing import Optional

import psycopg
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(dotenv_path=ENV_PATH)

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "fortune_bot")
DB_USER = os.getenv("DB_USER", "fortune_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "fortune_password")


def get_connection():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def init_db():
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                name TEXT,
                birthdate TEXT,
                free_readings_used INTEGER DEFAULT 0,
                coins_balance INTEGER DEFAULT 0
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                package_name TEXT NOT NULL,
                coins_amount INTEGER NOT NULL,
                stars_amount INTEGER NOT NULL,
                telegram_payment_charge_id TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                service_type TEXT DEFAULT 'tarot',
                user_name TEXT,
                birthdate TEXT,
                question TEXT,
                cards TEXT,
                answer TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)

            cursor.execute("""
            CREATE TABLE IF NOT EXISTS chat_messages (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT NOT NULL,
                service_type TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """)
        conn.commit()


def get_user(telegram_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT telegram_id, name, birthdate, free_readings_used, coins_balance
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            return cursor.fetchone()


def create_or_update_user(telegram_id: int, name: str, birthdate: str):
    existing_user = get_user(telegram_id)

    with get_connection() as conn:
        with conn.cursor() as cursor:
            if existing_user:
                cursor.execute(
                    """
                    UPDATE users
                    SET name = %s, birthdate = %s
                    WHERE telegram_id = %s
                    """,
                    (name, birthdate, telegram_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO users (telegram_id, name, birthdate, free_readings_used, coins_balance)
                    VALUES (%s, %s, %s, 0, 0)
                    """,
                    (telegram_id, name, birthdate)
                )
        conn.commit()


def increment_free_readings(telegram_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET free_readings_used = free_readings_used + 1
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
        conn.commit()


def get_free_readings_used(telegram_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT free_readings_used
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            result = cursor.fetchone()
    return result[0] if result else 0


def get_coins_balance(telegram_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT coins_balance
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            result = cursor.fetchone()
    return result[0] if result else 0


def add_coins(telegram_id: int, amount: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET coins_balance = coins_balance + %s
                WHERE telegram_id = %s
                """,
                (amount, telegram_id)
            )
        conn.commit()


def spend_coin(telegram_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT coins_balance
                FROM users
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
            result = cursor.fetchone()

            if not result or result[0] <= 0:
                return False

            cursor.execute(
                """
                UPDATE users
                SET coins_balance = coins_balance - 1
                WHERE telegram_id = %s
                """,
                (telegram_id,)
            )
        conn.commit()
    return True


def save_payment(telegram_id: int, package_name: str, coins_amount: int, stars_amount: int, charge_id: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO payments (
                    telegram_id, package_name, coins_amount, stars_amount, telegram_payment_charge_id
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (telegram_id, package_name, coins_amount, stars_amount, charge_id)
            )
        conn.commit()


def save_reading(
    telegram_id: int,
    service_type: str,
    user_name: str,
    birthdate: str,
    question: str,
    cards: Optional[str],
    answer: str,
):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO readings (telegram_id, service_type, user_name, birthdate, question, cards, answer)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (telegram_id, service_type, user_name, birthdate, question, cards, answer)
            )
        conn.commit()


def get_user_readings(telegram_id: int, limit: int = 5):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT service_type, question, cards, created_at
                FROM readings
                WHERE telegram_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (telegram_id, limit)
            )
            return cursor.fetchall()


def save_message(telegram_id: int, service_type: str, role: str, content: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO chat_messages (telegram_id, service_type, role, content)
                VALUES (%s, %s, %s, %s)
                """,
                (telegram_id, service_type, role, content)
            )
        conn.commit()


def get_recent_messages(telegram_id: int, service_type: str, limit: int = 10):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, content
                FROM chat_messages
                WHERE telegram_id = %s AND service_type = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                (telegram_id, service_type, limit)
            )
            rows = cursor.fetchall()

    return list(reversed(rows))