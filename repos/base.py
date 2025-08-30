# repos/base.py
from contextlib import contextmanager
import sqlite3
from typing import Iterator, Any
from pathlib import Path
from config import DB_PATH, PRAGMAS_STARTUP

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    for q in PRAGMAS_STARTUP:
        conn.execute(q)
    return conn

@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    conn = get_conn()
    try:
        conn.execute("BEGIN IMMEDIATE")  # bloquea escritura y evita race en folios
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def one(cur: sqlite3.Cursor) -> dict | None:
    r = cur.fetchone()
    return dict(r) if r else None

def many(cur: sqlite3.Cursor) -> list[dict]:
    return [dict(r) for r in cur.fetchall()]
