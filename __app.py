import os, sqlite3
from contextlib import closing
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify

from escpos_print import print_ticket as escpos_print_ticket

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "pos.db")
INIT_SQL_PATH = os.path.join(BASE_DIR, "init_db.sql")

app = Flask(__name__)
app.secret_key = "cambia-esta-clave"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # Robustez ante cortes de energía y mejor concurrencia de lectura
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=FULL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def bootstrap():
    if not os.path.exists(DB_PATH):
        with open(INIT_SQL_PATH, "r", encoding="utf-8") as f:
            init = f.read()
        with closing(get_conn()) as conn:
            conn.executescript(init)
            conn.commit()

def next_folio(conn):
    row = conn.execute("SELECT folio FROM sales ORDER BY created_at DESC LIMIT 1").fetchone()
    if not row:
        return "F0001"
    last = row["folio"]
    prefix = "".join([c for c in last if not c.isdigit()]) or "F"
    num = int("".join([c for c in last if c.isdigit()]) or "0") + 1
    return f"{prefix}{num:04d}"

def load_cfg(conn):
    return conn.execute("SELECT * FROM business_config WHERE id=1").fetchone()

@app.route("/")
def home():
    return redirect(url_for("new_sale"))

@app.route("/config", methods=["GET", "POST"])
def config():
    with closing(get_conn()) as conn:
        cfg = load_cfg(conn)
        if request.method == "POST":
            name = request.form.get("name")
            rfc = request.form.get("rfc")
            address = request.form.get("address")
            phone = request.form.get("phone")
            thank_you = request.form.get("thank_you")
            tax_rate = float(request.form.get("tax_rate") or cfg["tax_rate"])
            conn.execute("""UPDATE business_config SET name=?, rfc=?, address=?, phone=?, thank_you=?, tax_rate=? WHERE id=1""",
                         (name, rfc, address, phone, thank_you, tax_rate))
            conn.commit()
            flash("Configuración guardada", "success")
            return redirect(url_for("config"))
        return render_template("config.html", cfg=cfg)

@app.route("/catalog", methods=["GET", "POST"])
def catalog():
    with closing(get_conn()) as conn:
        if request.method == "POST":
            sku = request.form.get("sku")
            description = request.form.get("description")
            price = float(request.form.get("price") or 0)
            kind = request.form.get("kind") or "Producto"
            tax_rate = float(request.form.get("tax_rate") or load_cfg(conn)["tax_rate"])
            if sku and description:
                conn.execute("""INSERT INTO products(sku, description, price, kind, tax_rate)
                                VALUES(?,?,?,?,?)
                                ON CONFLICT(sku) DO UPDATE SET description=excluded.description,
                                                               price=excluded.price,
                                                               kind=excluded.kind,
                                                               tax_rate=excluded.tax_rate""",
                             (sku, description, price, kind, tax_rate))
                conn.commit()
                flash(f"Guardado {sku}", "success")
            else:
                flash("SKU y Descripción son obligatorios", "danger")
        prods = conn.execute("SELECT * FROM products ORDER BY sku").fetchall()
        return render_template("catalog.html", prods=prods, cfg=load_cfg(conn))

@app.route("/catalog/delete/<sku>", methods=["POST"])
def catalog_delete(sku):
    with closing(get_conn()) as conn:
        conn.execute("DELETE FROM products WHERE sku=?", (sku,))
        conn.commit()
        flash(f"Eliminado {sku}", "warning")
    return redirect(url_for("catalog"))

@app.route("/sales/new", methods=["GET", "POST"])
def new_sale():
    with closing(get_conn()) as conn:
        if request.method == "POST":
            seller = request.form.get("seller") or "Mostrador"
            customer = request.form.get("customer") or "Cliente Mostrador"
            items = []
            for i in range(1, 21):
                sku = request.form.get(f"sku_{i}")
                qty = request.form.get(f"qty_{i}")
                price = request.form.get(f"price_{i}")
                if sku and qty:
                    qty = float(qty)
                    if qty <= 0: 
                        continue
                    if not price or float(price) <= 0:
                        prod = conn.execute("SELECT price, tax_rate FROM products WHERE sku=?", (sku,)).fetchone()
                        if not prod:
                            flash(f"SKU {sku} no existe", "danger")
                            return redirect(url_for("new_sale"))
                        price = float(prod["price"])
                        tax_rate = float(prod["tax_rate"])
                    else:
                        prod = conn.execute("SELECT tax_rate FROM products WHERE sku=?", (sku,)).fetchone()
                        tax_rate = float(prod["tax_rate"]) if prod else load_cfg(conn)["tax_rate"]
                    items.append((sku, qty, float(price), float(tax_rate)))
            if not items:
                flash("Agrega al menos un producto", "danger")
                return redirect(url_for("new_sale"))

            folio = next_folio(conn)
            conn.execute("INSERT INTO sales(folio, seller, customer) VALUES(?,?,?)", (folio, seller, customer))
            for (sku, qty, unit_price, tax_rate) in items:
                conn.execute("""INSERT INTO sale_items(folio, sku, qty, unit_price, tax_rate)
                                VALUES(?,?,?,?,?)""", (folio, sku, qty, unit_price, tax_rate))
            conn.commit()
            flash(f"Venta guardada con folio {folio}", "success")
            return redirect(url_for("ticket", folio=folio))

        prods = conn.execute("SELECT * FROM products ORDER BY description").fetchall()
        return render_template("sale_new.html", prods=prods, cfg=load_cfg(conn))

@app.route("/ticket/<folio>")
def ticket(folio):
    with closing(get_conn()) as conn:
        cfg = load_cfg(conn)
        header = conn.execute("SELECT folio, seller, customer, strftime('%Y-%m-%d %H:%M', created_at) as created_at FROM sales WHERE folio=?", (folio,)).fetchone()
        if not header:
            flash("Folio no encontrado", "danger")
            return redirect(url_for("new_sale"))
        items = conn.execute("""SELECT si.qty, si.unit_price, si.tax_rate, p.description
                                FROM sale_items si JOIN products p ON p.sku=si.sku
                                WHERE folio=?""", (folio,)).fetchall()
        subtotal = sum([float(it["qty"])*float(it["unit_price"]) for it in items])
        tax = sum([float(it["qty"])*float(it["unit_price"])*float(it["tax_rate"]) for it in items])
        total = subtotal + tax
        return render_template("ticket.html", cfg=cfg, header=header, items=items, subtotal=subtotal, tax=tax, total=total)

@app.route("/ticket/<folio>/print", methods=["POST"])
def ticket_print(folio):
    conn_type = request.form.get("conn_type", "network")
    host = request.form.get("host", "192.168.0.100")
    port = int(request.form.get("port", "9100") or 9100)
    usb_vendor = request.form.get("usb_vendor", "0x04b8")
    usb_product = request.form.get("usb_product", "0x0202")
    serial_dev = request.form.get("serial_dev", "/dev/ttyUSB0")
    serial_baud = int(request.form.get("serial_baud", "19200"))
    paper = int(request.form.get("paper", "58"))

    with closing(get_conn()) as conn:
        cfg = dict(load_cfg(conn))
        header = conn.execute("SELECT folio, seller, customer, strftime('%Y-%m-%d %H:%M', created_at) as created_at FROM sales WHERE folio=?", (folio,)).fetchone()
        if not header:
            return jsonify({"ok": False, "msg": "Folio no encontrado"}), 404
        items = conn.execute("""SELECT si.qty, si.unit_price, si.tax_rate, p.description
                                FROM sale_items si JOIN products p ON p.sku=si.sku
                                WHERE folio=?""", (folio,)).fetchall()

        try:
            if conn_type == "network":
                escpos_print_ticket(cfg, header, items, conn_type="network", host=host, port=port, paper_width_mm=paper)
            elif conn_type == "usb":
                ev = int(usb_vendor, 16); ep = int(usb_product, 16)
                escpos_print_ticket(cfg, header, items, conn_type="usb", usb_vendor=ev, usb_product=ep, paper_width_mm=paper)
            else:
                escpos_print_ticket(cfg, header, items, conn_type="serial", serial_dev=serial_dev, serial_baud=serial_baud, paper_width_mm=paper)
            return jsonify({"ok": True, "msg": "Ticket enviado a la impresora"})
        except Exception as e:
            return jsonify({"ok": False, "msg": str(e)}), 500

if __name__ == "__main__":
    bootstrap()
    # Desarrollo
    app.run(debug=True, host="0.0.0.0", port=8000)
    # Producción  (descomenta estas dos líneas y comenta la de arriba)
    # from waitress import serve
    # serve(app, host="0.0.0.0", port=8000)
