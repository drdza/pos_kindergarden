# repos/customers.py
from .base import get_conn, tx, one, many

def create(**fields):
    keys = ",".join(fields.keys())
    qs = ",".join(["?"]*len(fields))
    with tx() as conn:
        conn.execute(f"INSERT INTO customers({keys}) VALUES({qs})", tuple(fields.values()))

def get_by_matricula(matricula: str) -> dict | None:
    with get_conn() as conn:
        return one(conn.execute("SELECT * FROM customers WHERE matricula=?", (matricula,)))

def list_active() -> list[dict]:
    with get_conn() as conn:
        return many(conn.execute("SELECT id, enrollment, first_name || ' ' || IFNULL(second_name,'') AS name FROM customers WHERE active=1 ORDER BY enrollment"))

def list_by_salon(grade_id: int | None, group_id: int | None, shift_id: int | None) -> list[dict]:
    sql = "SELECT * FROM customers WHERE 1=1"
    params = []
    if grade_id: sql += " AND grade_id=?"; params.append(grade_id)
    if group_id: sql += " AND group_id=?"; params.append(group_id)
    if shift_id: sql += " AND shift_id=?"; params.append(shift_id)
    sql += " ORDER BY apellido, nombre"
    with get_conn() as conn:
        return many(conn.execute(sql, params))
