# services/sales_service.py
from repos import sales as sales_repo

def alta_venta(
    customer_name: str,
    seller_name: str,
    items_ui: list[dict],
    customer_id: int | None = None,
    seller_id: int | None = None,
    payments: list[dict] | None = None,
) -> dict:
    """
    items_ui: [{sku?, descripcion, qty, unit_price, discount?, tax_rate?}, ...]
    return: {"id": sale_id, "folio": folio}
    """
    if not items_ui:
        raise ValueError("No hay renglones")

    items = []
    for it in items_ui:
        if not it.get("descripcion") and not it.get("sku"):
            raise ValueError("Cada renglón debe tener 'descripcion' o 'sku'")
        items.append({
            "sku": it.get("sku"),
            "description_snapshot": it.get("descripcion") or it["sku"],
            "unit_price": float(it["unit_price"]),
            "qty": float(it["qty"]),            
            "discount": float(it.get("discount", 0.0)),
            "tax_rate": float(it.get("tax_rate", 0.0)),
        })

    header = {
        "customer_id": customer_id,
        "seller_id": seller_id,
        "customer": customer_name,  # snapshot
        "seller": seller_name,      # snapshot
    }

    return sales_repo.create_sale(header, items, payments or [])
