# repos/sellers.py
from .base import get_conn, tx, one, many

def upsert(codigo_empleado: str, nombre: str, apellido: str, domicilio: str, puesto: str, activo: int = 1):
    with tx() as conn:
        conn.execute("""
            INSERT INTO sellers(codigo_empleado, nombre, apellido, domicilio, puesto, activo)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(codigo_empleado) DO UPDATE SET
              nombre=excluded.nombre, apellido=excluded.apellido, domicilio=excluded.domicilio,
              puesto=excluded.puesto, activo=excluded.activo
        """, (codigo_empleado, nombre, apellido, domicilio, puesto, activo))

def list_active() -> list[dict]:
    with get_conn() as conn:
        return many(conn.execute("SELECT * FROM sellers WHERE activo=1 ORDER BY apellido, nombre"))
