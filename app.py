from flask import Flask, render_template, request, redirect, url_for, jsonify, abort
from pathlib import Path
from config import DB_PATH
from repos import products, sellers, customers
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
        _products = products.list_active()
        _customers = customers.list_active()
        _sellers = sellers.list_active()
        return render_template("new_sale.html", customers=_customers, sellers=_sellers, products=_products)

    # Buscar productos (HTMX autocomplete)
    @app.get("/api/products/search")
    def api_products_search():
        txt = request.args.get("txt", "").strip()
        print(txt)
        if not txt:
            return render_template("partials/_product_list.html", products=[])
        with db_base.get_conn() as conn:
            rows = db_base.many(conn.execute(
                "SELECT sku, description, price, tax_rate FROM products WHERE active=1 AND (sku LIKE ? OR description LIKE ?) ORDER BY description LIMIT 20",
                (f"%{txt}%", f"%{txt}%")
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
                "unit_price": float(prices[i] or 0),
                "qty": float(qtys[i] or 0),                
                "tax_rate": float(taxes[i] or 0),
            })

        if not items:
            abort(400, "No hay renglones")

        # Método y montos de pago desde el form
        method = (request.form.get("payment_method") or "").strip().upper() 
        amount = request.form.get("payment_amount")  # monto aplicado a la venta
        tendered = request.form.get("payment_tendered")  # lo que entregó el cliente (efectivo)        
        
        # Multiples métodos de pago
        payments = []
        try:
            amount_val = float(amount) if amount not in (None, "",) else 0.0
        except ValueError:
            amount_val = 0.0

        try:
            tendered_val = float(tendered) if tendered not in (None, "",) else 0.0
        except ValueError:
            tendered_val = 0.0

        if amount_val > 0:
            change_val = 0.0
            # Calcula cambio sólo si hay tendered informado y el método es efectivo
            if tendered_val > 0 and method in ("CASH", "EFECTIVO"):
                change_val = round(tendered_val - amount_val, 2)

            payments.append({
                "method": method or "CASH",
                "amount": amount_val,
                "tendered": tendered_val or None,
                "change": change_val if tendered_val > 0 else None,
            })

        # # Pago único (luego habilitamos split payments)
        # payment_amount = float(data.get("payment_amount") or 0)
        # payment_method = data.get("payment_method") or "cash"
        # payments = [{"method": payment_method, "amount": payment_amount}]

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
    

    # ===== Listado de ventas (con filtro de estado) =====
    @app.get("/sales")
    def list_sales():
        status = (request.args.get("status") or "open").lower()
        print(f"Status: {status}")
        
        # Consulta base común
        base_query = """
            SELECT s.id, s.folio, s.created_at, s.customer, s.seller,
                s.subtotal, s.tax_total, s.total, s.payment_status,
                COALESCE((SELECT SUM(amount) FROM payments p WHERE p.sale_id = s.id), 0) AS paid
            FROM sales s
        """
        
        # Determinar la condición WHERE según el estado
        if status == "open":
            where_condition = "WHERE UPPER(s.payment_status) IN ('PENDIENTE','PARCIAL')"
        elif status == "paid":
            where_condition = "WHERE UPPER(s.payment_status) IN ('PAGADO')"
        elif status == "all":
            where_condition = ""
        else:
            abort(400, "Filtro de estado inválido")
        
        # Ordenamiento común
        order_by = "ORDER BY s.id DESC"
        
        # Construir la consulta completa
        full_query = f"{base_query} {where_condition} {order_by}"

        with db_base.get_conn() as conn:
            rows = db_base.many(conn.execute(full_query))

        return render_template("sales_list.html", sales=rows, current_filter=status)




    return app

if __name__ == "__main__":
    app = create_app()
    # dev server
    app.run(host="0.0.0.0", port=8000, debug=True)
