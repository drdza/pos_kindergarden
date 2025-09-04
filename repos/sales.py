# repos/sales.py
from .base import tx, get_conn, one, many


def create_sale(header: dict, items: list[dict], payments: list[dict]) -> dict:
    """
    header: {customer_id?, seller_id?, customer, seller}
    items:  [{sku?, description_snapshot, qty, unit_price, discount, tax_rate}, ...]
    payments: [{method, amount, reference?}, ...]
    return: {"id": sale_id, "folio": folio}
    """
    if not items:
        raise ValueError("La venta debe tener al menos un renglón")

    with tx() as conn:
        # 1) Insert header (SIN folio: trigger lo asigna después)
        cur = conn.execute("""
            INSERT INTO sales (customer_id, seller_id, customer, seller)
            VALUES (?, ?, ?, ?)
        """, (header.get("customer_id"), header.get("seller_id"),
              header["customer"], header["seller"]))
        sale_id = cur.lastrowid

        # 2) Insert items (sale_id)
        for it in items:
            if it.get("sku") and "tax_rate" not in it:
                prod = one(conn.execute("SELECT tax_rate FROM products WHERE sku=?", (it["sku"],)))
                if prod:
                    it["tax_rate"] = prod["tax_rate"]
            line_total = max(0.0, (it["qty"] * it["unit_price"] - it.get("discount", 0.0)) * (1 + it.get("tax_rate", 0.0)))
            conn.execute("""
                INSERT INTO sale_items
                (sale_id, sku, description_snapshot, qty, unit_price, discount, tax_rate, line_total)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (sale_id, it.get("sku"), it["description_snapshot"], float(it["qty"]),
                  float(it["unit_price"]), float(it.get("discount", 0.0)),
                  float(it.get("tax_rate", 0.0)), line_total))

        # 3) Insert payments (sale_id)
        for p in payments:
            conn.execute("""
                INSERT INTO payments (sale_id, method, amount, reference, tendered, change)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                sale_id, 
                p.get("method"), 
                float(p.get("amount") or 0), 
                p.get("reference"), 
                p.get("tendered"), 
                p.get("change")
            ))

        # 4) Obtener folio que generó el trigger
        folio_row = one(conn.execute("SELECT folio FROM sales WHERE id=?", (sale_id,)))
        folio = folio_row["folio"] if folio_row else None

    return {"id": sale_id, "folio": folio}

def get_sale(sale_id: int) -> tuple[dict, list[dict], list[dict]]:
    with get_conn() as conn:
        sale = one(conn.execute("SELECT * FROM sales WHERE id=?", (sale_id,)))
        items = many(conn.execute("SELECT * FROM sale_items WHERE sale_id=? ORDER BY id", (sale_id,)))
        pays  = many(conn.execute("SELECT * FROM payments WHERE sale_id=? ORDER BY id", (sale_id,)))
    return sale, items, pays


def get_sale(id_sale: int) -> tuple[dict, list[dict], list[dict]]:
    with get_conn() as conn:
        sale = one(conn.execute("SELECT * FROM sales WHERE id=?", (id_sale,)))
        items = many(conn.execute("SELECT * FROM sale_items WHERE sale_id=? ORDER BY id", (id_sale,)))
        pays  = many(conn.execute("SELECT * FROM payments WHERE sale_id=? ORDER BY id", (id_sale,)))
    return sale, items, pays
