"""Postgres connection pool helper (fallbacks to psycopg2 when DATABASE_URL set)."""
import os
from contextlib import contextmanager
try:
    import psycopg2
    from psycopg2 import pool
except ImportError:
    psycopg2 = None
    pool = None

DB_URL = os.getenv('DATABASE_URL', 'postgresql://observer:password@localhost:5432/observer')

db_pool = None
if psycopg2 and pool:
    try:
        db_pool = pool.SimpleConnectionPool(1, 5, DB_URL)
    except Exception:
        db_pool = None


def get_db():
    """Return a raw psycopg2 connection from pool, or raise if unavailable."""
    if not db_pool:
        raise RuntimeError('Postgres pool not initialized')
    return db_pool.getconn()


def release_db(conn):
    """Return a connection to the pool."""
    if db_pool and conn:
        db_pool.putconn(conn)


@contextmanager
def db_context():
    """Context manager that yields a DB connection and returns it to the pool."""
    conn = None
    try:
        conn = get_db()
        yield conn
    finally:
        if conn:
            release_db(conn)
