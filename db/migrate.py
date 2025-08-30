from pathlib import Path
import sqlite3, hashlib
from contextlib import closing
from config import DB_PATH
from .init import get_connection, execute_script

MIGR_TABLE = """
CREATE TABLE IF NOT EXISTS _migrations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    checksum TEXT NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

def _checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def ensure_table(conn: sqlite3.Connection) -> None:
    conn.execute(MIGR_TABLE)
    conn.commit()

def applied(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT filename FROM _migrations").fetchall()
    return {r["filename"] for r in rows}

def apply_migrations(migrations_dir: Path) -> list[str]:
    migrations_dir.mkdir(exist_ok=True)
    files = sorted(p for p in migrations_dir.glob("*.sql"))
    done = []
    with get_connection() as conn:
        ensure_table(conn)
        already = applied(conn)
        for f in files:
            if f.name in already:
                continue
            sql = f.read_text(encoding="utf-8")
            execute_script(conn, sql)
            conn.execute("INSERT INTO _migrations(filename, checksum) VALUES(?, ?)", (f.name, _checksum(sql)))
            conn.commit()
            done.append(f.name)
    return done
