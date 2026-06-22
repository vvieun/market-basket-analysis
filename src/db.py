import os

import psycopg2

# Defaults match docker-compose.yml. Override with DATABASE_URL if needed.
DSN = os.environ.get(
    "DATABASE_URL",
    "postgresql://analytics:analytics@localhost:5443/basket",
)


def connect():
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    return conn


def query(sql):
    """Run a SELECT and return (columns, rows)."""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            columns = [d[0] for d in cur.description]
            return columns, cur.fetchall()
    finally:
        conn.close()


def scalar(sql):
    _, rows = query(sql)
    return rows[0][0] if rows else None
