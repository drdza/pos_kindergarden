from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from pathlib import Path
from config import DB_PATH
from repos import products as products_repo
from repos import sellers as sellers_repo
from repos import base as db_base
from repos.sales import get_sale
from services.sales_service import alta_venta

def create_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    @app.get("/")
    def home():
        return redirect(url_for("new_sale"))

    # --------- Nueva Venta (formulario) ----------
    @app.get("/sales/new")
    def new_sale():
        # combos base (puedes paginarlos luego)
        with db_base.get_conn() as conn:
            customers = db_base.many(conn.execute(
                "SELECT id, enrollment, first_name || ' ' || IFNULL(second_name,'') AS name FROM customers WHERE active=1 ORDER BY second_name, first_name LIMIT 200"
            ))
        sellers = sellers_repo.list_active()
        return render_template("new_sale.html", customers=customers, sellers=sellers)

    # Buscar productos (HTMX autocomplete)
    @app.get("/api/products/search")
    def api_products_search():
        q = request.args.get("q", "").strip()
        print(q)
        if not q:
            return render_template("partials/_product_list.html", products=[])
        with db_base.get_conn() as conn:
            rows = db_base.many(conn.execute(
                "SELECT sku, description, price, tax_rate FROM products WHERE active=1 AND (sku LIKE ? OR description LIKE ?) ORDER BY description LIMIT 20",
                (f"%{q}%", f"%{q}%")
            ))
        return render_template("partials/_product_list.html", products=rows)

    # Crear venta
    @app.post("/sales")
    def create_sale():
        data = request.form        
        # Construir items desde el form (campos arrays)
        items = []
        skus = request.form.getlist("sku[]")
        descs = request.form.getlist("desc[]")
        qtys = request.form.getlist("qty[]")
        prices = request.form.getlist("price[]")
        taxes = request.form.getlist("tax[]")
        for i in range(len(descs)):
            if not descs[i] and not skus[i]:
                continue
            items.append({
                "sku": skus[i] or None,
                "descripcion": descs[i] or (skus[i] or ""),
                "qty": float(qtys[i] or 0),
                "unit_price": float(prices[i] or 0),
                "tax_rate": float(taxes[i] or 0),
            })

        if not items:
            abort(400, "No hay renglones")

        # Pago único (luego habilitamos split payments)
        payment_amount = float(data.get("payment_amount") or 0)
        payment_method = data.get("payment_method") or "cash"
        payments = [{"method": payment_method, "amount": payment_amount}]

        # Alumno / Vendedor
        customer_id = int(data["customer_id"]) if data.get("customer_id") else None
        seller_id = int(data["seller_id"]) if data.get("seller_id") else None
        customer_name = data.get("customer_name") or "Alumno"
        seller_name = data.get("seller_name") or "Mostrador"

        result = alta_venta(
            customer_name=customer_name,
            seller_name=seller_name,
            items_ui=items,
            customer_id=customer_id,
            seller_id=seller_id,
            payments=payments
        )
        # Redirige al ticket
        return redirect(url_for("ticket", sale_id=result["id"]))

    # Ticket
    @app.get("/sales/<int:sale_id>/ticket")
    def ticket(sale_id: int):
        sale, items, pays = get_sale(sale_id)
        print(sale)
        if not sale:
            abort(404)
        return render_template("ticket.html", sale=sale, items=items, pays=pays)

    return app

if __name__ == "__main__":
    app = create_app()
    # dev server
    app.run(host="0.0.0.0", port=8000, debug=True)
