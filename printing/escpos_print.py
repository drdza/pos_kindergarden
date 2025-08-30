from escpos.printer import Network, Usb, Serial

def print_ticket(cfg, header, items, conn_type="network", host="192.168.0.100", port=9100,
                 usb_vendor=0x04b8, usb_product=0x0202, usb_in_ep=0x82, usb_out_ep=0x01,
                 serial_dev="/dev/ttyUSB0", serial_baud=19200, paper_width_mm=58):
    subtotal = sum([float(it["qty"]) * float(it["unit_price"]) for it in items])
    tax = sum([float(it["qty"]) * float(it["unit_price"]) * float(it["tax_rate"]) for it in items])
    total = subtotal + tax
    paper_chars = 32 if paper_width_mm <= 58 else 42

    if conn_type == "network":
        p = Network(host, port=port, timeout=10)
    elif conn_type == "usb":
        p = Usb(usb_vendor, usb_product, usb_in_ep, usb_out_ep)
    elif conn_type == "serial":
        p = Serial(devfile=serial_dev, baudrate=serial_baud)
    else:
        raise ValueError("conn_type inválido")

    p.set(align="center", text_type="B")
    p.textln(cfg["name"] + "\n")
    if cfg.get("address"):
        p.textln(cfg["address"] + "\n")
    p.textln(f"RFC: {cfg['rfc']}  Tel: {cfg['phone']}\n")
    p.textln("-"*paper_chars + "\n")

    p.set(align="left", text_type="NORMAL")
    p.textln(f"Folio: {header['folio']}")
    p.textln(f"Fecha/Hora: {header['created_at']}\n")
    p.textln("-"*paper_chars + "\n")

    for it in items:
        desc = str(it["description"])[:paper_chars]
        p.textln(desc + "\n")
        qty = float(it["qty"]); pu = float(it["unit_price"]); imp = qty*pu
        l = f"{qty:.2f} x {pu:,.2f}"; r = f"{imp:,.2f}"
        p.textln(l + " "*(paper_chars - len(l) - len(r)) + r + "\n")

    p.textln("-"*paper_chars + "\n")
    def pline(label, amount, bold=False):
        l = label; r = f"${amount:,.2f}"
        s = l + " "*(paper_chars - len(l) - len(r)) + r
        if bold: p.set(text_type="B")
        p.textln(s + "\n")
        if bold: p.set(text_type="NORMAL")
    pline("Subtotal:", subtotal)
    pline("IVA:", tax)
    pline("TOTAL:", total, bold=True)

    p.textln("\n")
    if cfg.get("thank_you"):
        p.set(align="center")
        p.textln(str(cfg["thank_you"]) + "\n")

    p.cut()
    try:
        p.close()
    except Exception:
        pass
