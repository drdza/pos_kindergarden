from pathlib import Path
import sqlite3
from contextlib import closing
from typing import Iterable
from config import DB_PATH, PRAGMAS_STARTUP

def _apply_pragmas(conn: sqlite3.Connection) -> None:
    for q in PRAGMAS_STARTUP:
        conn.execute(q)

def execute_script(conn: sqlite3.Connection, sql: str) -> None:
    with closing(conn.cursor()) as cur:
        cur.executescript(sql)
    conn.commit()

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    _apply_pragmas(conn)
    return conn

def init_db(schema_file: Path) -> None:
    sql = schema_file.read_text(encoding="utf-8")
    with get_connection() as conn:
        execute_script(conn, sql)

def run_sql_files(files: Iterable[Path]) -> None:
    with get_connection() as conn:
        for f in files:
            sql = f.read_text(encoding="utf-8")
            execute_script(conn, sql)

# Helper para ubicar ruta del schema
def schema_path() -> Path:
    return Path(__file__).resolve().parent / "schema.sql"
