# repos/products.py
from .base import get_conn, tx, one, many

def upsert(sku: str, description: str, price: float, tax_rate: float, kind: str = "Servicio",
           unit: str = "pz", cost: float = 0.0, category_id: int | None = None, active: int = 1):
    with tx() as conn:
        conn.execute("""
            INSERT INTO products(sku, description, price, tax_rate, kind, unit, cost, category_id, active)
            VALUES(?,?,?,?,?,?,?,?,?)
            ON CONFLICT(sku) DO UPDATE SET
              description=excluded.description, price=excluded.price, tax_rate=excluded.tax_rate,
              kind=excluded.kind, unit=excluded.unit, cost=excluded.cost,
              category_id=excluded.category_id, active=excluded.active
        """, (sku, description, price, tax_rate, kind, unit, cost, category_id, active))

def get(sku: str) -> dict | None:
    with get_conn() as conn:
        return one(conn.execute("SELECT * FROM products WHERE sku=?", (sku,)))

def list_active() -> list[dict]:
    with get_conn() as conn:
        return many(conn.execute("SELECT * FROM products WHERE active=1 ORDER BY description"))
