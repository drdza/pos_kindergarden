# repos/sales.py
from .base import tx, get_conn, one, many

def next_folio() -> str:
    # Prefijo F, 4 dígitos: F0001, F0002...
    with get_conn() as conn:
        row = one(conn.execute("SELECT folio FROM sales ORDER BY created_at DESC LIMIT 1"))
    if not row:
        return "F0001"
    last = row["folio"]
    prefix = "".join([c for c in last if not c.isdigit()]) or "F"
    num = int("".join([c for c in last if c.isdigit()]) or "0") + 1
    return f"{prefix}{num:04d}"

def create_sale(header: dict, items: list[dict], payments: list[dict] | None = None) -> str:
    """
    header: {customer_id?, seller_id?, customer, seller}
    items:  [{sku?, description_snapshot, qty, unit_price, discount, tax_rate}, ...]
    payments: [{method, amount, reference?}, ...] (opcional)
    """
    if not items:
        raise ValueError("La venta debe tener al menos un renglón")
    folio = next_folio()
    with tx() as conn:
        # Insert header; totales y payment_status los recalculan triggers
        conn.execute("""
            INSERT INTO sales(folio, customer_id, seller_id, customer, seller)
            VALUES(?,?,?,?,?)
        """, (folio, header.get("customer_id"), header.get("seller_id"),
              header["customer"], header["seller"]))
        # Insert items
        for it in items:
            # si viene sku, toma tax_rate por defecto del producto si no se especificó
            if it.get("sku") and "tax_rate" not in it:
                prod = one(conn.execute("SELECT tax_rate FROM products WHERE sku=?", (it["sku"],)))
                if prod: it["tax_rate"] = prod["tax_rate"]
            vals = (
                folio, it.get("sku"), it["description_snapshot"], float(it["qty"]),
                float(it["unit_price"]), float(it.get("discount", 0.0)),
                float(it.get("tax_rate", 0.0)),
                # line_total: puedes dejar 0 y permitir que el trigger/servicio lo actualice,
                # o calcularlo aquí:
                max(0.0, (it["qty"]*it["unit_price"] - it.get("discount", 0.0)) * (1 + it.get("tax_rate", 0.0)))
            )
            conn.execute("""
                INSERT INTO sale_items(folio, sku, description_snapshot, qty, unit_price, discount, tax_rate, line_total)
                VALUES(?,?,?,?,?,?,?,?)
            """, vals)
        # Insert payments (opcional)
        for p in payments or []:
            conn.execute("""
                INSERT INTO payments(folio, method, amount, reference) VALUES(?,?,?,?)
            """, (folio, p["method"], float(p["amount"]), p.get("reference")))
    return folio

def get_sale(folio: str) -> tuple[dict, list[dict], list[dict]]:
    with get_conn() as conn:
        sale = one(conn.execute("SELECT * FROM sales WHERE folio=?", (folio,)))
        items = many(conn.execute("SELECT * FROM sale_items WHERE folio=? ORDER BY id", (folio,)))
        pays  = many(conn.execute("SELECT * FROM payments WHERE folio=? ORDER BY id", (folio,)))
    return sale, items, pays
