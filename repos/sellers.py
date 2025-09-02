# repos/sellers.py
from .base import get_conn, tx, one, many

def upsert(employee_code: str, first_name: str, second_name: str, address: str, job_title: str, active: int = 1):
    with tx() as conn:
        conn.execute("""
            INSERT INTO sellers(employee_code, first_name, second_name, address, job_title, active)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(employee_code) DO UPDATE SET
              first_name=excluded.first_name, apelsecond_namelido=excluded.second_name, address=excluded.address,
              job_title=excluded.job_title, active=excluded.active
        """, (employee_code, first_name, second_name, address, job_title, active))

def list_active() -> list[dict]:
    with get_conn() as conn:
        return many(conn.execute("SELECT * FROM sellers WHERE active=1 ORDER BY first_name, second_name"))
