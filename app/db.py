import os
import psycopg2
import psycopg2.extras
from datetime import date, timedelta


def _get_db_url():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return db_url


def get_conn():
    """Return a new database connection."""
    return psycopg2.connect(_get_db_url(), sslmode='require')


def init_db():
    """Create tables and indexes if they don't exist."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS food_logs (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                entry_date DATE NOT NULL,
                food TEXT NOT NULL,
                carbs NUMERIC NOT NULL,
                serving_qty NUMERIC,
                serving_unit TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_food_logs_user_date ON food_logs(user_id, entry_date);
            CREATE INDEX IF NOT EXISTS idx_food_logs_user_created ON food_logs(user_id, created_at DESC);
            """
        )
        conn.commit()


def insert_log(user_id: str, entry_date: date, food: str, carbs: float, serving_qty=None, serving_unit=None):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO food_logs (user_id, entry_date, food, carbs, serving_qty, serving_unit)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, entry_date, food, carbs, serving_qty, serving_unit)
        )
        conn.commit()


def fetch_logs_for_date(user_id: str, entry_date: date):
    with get_conn() as conn, conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute(
            """
            SELECT id, food, carbs, serving_qty, serving_unit, created_at
            FROM food_logs
            WHERE user_id = %s AND entry_date = %s
            ORDER BY created_at ASC
            """,
            (user_id, entry_date)
        )
        rows = cur.fetchall()
        return [dict(row) for row in rows]


def delete_latest_for_date(user_id: str, entry_date: date):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM food_logs
            WHERE id = (
                SELECT id FROM food_logs
                WHERE user_id = %s AND entry_date = %s
                ORDER BY created_at DESC
                LIMIT 1
            )
            RETURNING id;
            """,
            (user_id, entry_date)
        )
        deleted = cur.rowcount
        conn.commit()
        return deleted > 0


def delete_by_index(user_id: str, entry_date: date, index: int):
    """Delete item by zero-based index ordered by created_at ASC."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            DELETE FROM food_logs
            WHERE id = (
                SELECT id FROM food_logs
                WHERE user_id = %s AND entry_date = %s
                ORDER BY created_at ASC
                OFFSET %s LIMIT 1
            );
            """,
            (user_id, entry_date, index)
        )
        conn.commit()


def clear_day(user_id: str, entry_date: date):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM food_logs WHERE user_id = %s AND entry_date = %s",
            (user_id, entry_date)
        )
        conn.commit()


def list_dates(user_id: str):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT entry_date
            FROM food_logs
            WHERE user_id = %s
            ORDER BY entry_date DESC
            """,
            (user_id,)
        )
        return [r[0].isoformat() for r in cur.fetchall()]


def get_totals_for_dates(user_id: str, dates):
    if not dates:
        return {}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT entry_date, COALESCE(SUM(carbs), 0) AS total
            FROM food_logs
            WHERE user_id = %s AND entry_date = ANY(%s)
            GROUP BY entry_date
            """,
            (user_id, dates)
        )
        return {row[0].isoformat(): float(row[1]) for row in cur.fetchall()}


def get_top_foods(user_id: str, limit: int = 10):
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT food, COUNT(*) as cnt
            FROM food_logs
            WHERE user_id = %s
            GROUP BY food
            ORDER BY cnt DESC, food ASC
            LIMIT %s
            """,
            (user_id, limit)
        )
        return [row[0].title() for row in cur.fetchall()]
