import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "db")
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
                free_readings_used INTEGER DEFAULT 0
            )
            """)
        conn.commit()


def get_user(telegram_id: int):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT telegram_id, name, birthdate, free_readings_used
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
                    INSERT INTO users (telegram_id, name, birthdate, free_readings_used)
                    VALUES (%s, %s, %s, 0)
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

    if result:
        return result[0]
    return 0


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

    if result:
        return result[0]
    return 0


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
