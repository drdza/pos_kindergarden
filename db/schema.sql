PRAGMA foreign_keys = ON;

-- =========================================
-- TABLA: business_config
-- =========================================
CREATE TABLE IF NOT EXISTS business_config (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  name TEXT NOT NULL,
  rfc TEXT NOT NULL,
  address TEXT NOT NULL,
  phone TEXT NOT NULL,
  thank_you TEXT NOT NULL,
  tax_rate REAL NOT NULL DEFAULT 0.16,
  currency TEXT NOT NULL DEFAULT 'MXN'
);

-- =========================================
-- CATÁLOGOS: grades / groups / shifts
-- =========================================
CREATE TABLE IF NOT EXISTS grades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shifts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL
);


-- =========================================
-- TABLA: customers (alumnos)
-- =========================================
CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enrollment INTEGER NOT NULL UNIQUE,
  first_name TEXT NOT NULL,
  second_name TEXT,
  address TEXT,
  grade_id INTEGER REFERENCES grades(id),
  group_id INTEGER REFERENCES groups(id),
  shift_id INTEGER REFERENCES shifts(id),
  gender TEXT CHECK (gender IN ('M','F')),
  fullname_mom TEXT,
  fullname_dad TEXT,
  birth_date TEXT,
  curp TEXT UNIQUE,
  phone TEXT,
  mobile_phone TEXT,
  pay_reference TEXT,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TRIGGER IF NOT EXISTS trg_customers_updated
AFTER UPDATE ON customers
FOR EACH ROW BEGIN
  UPDATE customers
  SET updated_at = datetime('now','localtime')
  WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_customers_enrollment ON customers(enrollment);
CREATE INDEX IF NOT EXISTS idx_customers_nombre     ON customers(second_name, first_name);
CREATE INDEX IF NOT EXISTS idx_customers_salon      ON customers(grade_id, group_id, shift_id);

-- =========================================
-- TABLA: sellers (vendedores)
-- =========================================
CREATE TABLE IF NOT EXISTS sellers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_code TEXT NOT NULL UNIQUE,
  first_name TEXT NOT NULL,
  second_name TEXT,
  address TEXT,
  job_title TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TRIGGER IF NOT EXISTS trg_sellers_updated
AFTER UPDATE ON sellers
FOR EACH ROW BEGIN
  UPDATE sellers
  SET updated_at = datetime('now','localtime')
  WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_sellers_nombre ON sellers(second_name, first_name);

-- =========================================
-- CATÁLOGO: categories y products
-- =========================================
CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
  sku TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  price REAL NOT NULL CHECK (price >= 0),
  cost  REAL NOT NULL DEFAULT 0 CHECK (cost >= 0),
  unit  TEXT NOT NULL DEFAULT 'pz',
  kind  TEXT NOT NULL DEFAULT 'Servicio',
  tax_rate REAL NOT NULL DEFAULT 0.16,
  category_id INTEGER REFERENCES categories(id),
  active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_products_desc ON products(description);

-- =========================================
-- TABLA: sales
-- =========================================
CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  folio TEXT UNIQUE,
  customer_id INTEGER REFERENCES customers(id),
  seller_id   INTEGER REFERENCES sellers(id),
  customer TEXT NOT NULL,
  seller   TEXT NOT NULL,
  subtotal        REAL NOT NULL DEFAULT 0,
  discount_total  REAL NOT NULL DEFAULT 0,
  tax_total       REAL NOT NULL DEFAULT 0,
  total           REAL NOT NULL DEFAULT 0,
  status          TEXT NOT NULL DEFAULT 'paid',
  payment_status  TEXT NOT NULL DEFAULT 'unpaid',
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- Trigger: asigna folio automático
CREATE TRIGGER IF NOT EXISTS trg_sales_set_folio
AFTER INSERT ON sales
FOR EACH ROW
WHEN NEW.folio IS NULL
BEGIN
  UPDATE sales
  SET folio = 'F' || printf('%04d', NEW.id)
  WHERE id = NEW.id;
END;

CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_seller   ON sales(seller_id);
CREATE INDEX IF NOT EXISTS idx_sales_created  ON sales(created_at);

-- =========================================
-- TABLA: sale_items
-- =========================================
CREATE TABLE IF NOT EXISTS sale_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
  sku   TEXT REFERENCES products(sku),
  description_snapshot TEXT NOT NULL,
  qty        REAL NOT NULL CHECK (qty > 0),
  unit_price REAL NOT NULL CHECK (unit_price >= 0),
  discount   REAL NOT NULL DEFAULT 0 CHECK (discount >= 0),
  tax_rate   REAL NOT NULL DEFAULT 0.16,
  line_total REAL NOT NULL CHECK (line_total >= 0)
);

CREATE INDEX IF NOT EXISTS idx_sale_items_saleid ON sale_items(sale_id);

-- =========================================
-- TABLA: payments
-- =========================================
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL REFERENCES sales(id) ON DELETE CASCADE,
  method TEXT NOT NULL,
  amount REAL NOT NULL CHECK (amount >= 0),
  tendered REAL NULL,
  change REAL NULL,
  reference TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_payments_saleid ON payments(sale_id);

-- =========================================
-- VISTA: v_sales_calc (totales por venta)
-- =========================================
DROP VIEW IF EXISTS v_sales_calc;
CREATE VIEW v_sales_calc AS
SELECT
  s.id AS sale_id,
  COALESCE(SUM((si.qty*si.unit_price)),0) AS sub,
  COALESCE(SUM(si.discount),0) AS disc,
  COALESCE(SUM(((si.qty*si.unit_price)-si.discount)*si.tax_rate),0) AS iva,
  COALESCE(SUM(((si.qty*si.unit_price)-si.discount)
        + (((si.qty*si.unit_price)-si.discount)*si.tax_rate)),0) AS tot
FROM sales s
LEFT JOIN sale_items si ON si.sale_id = s.id
GROUP BY s.id;

-- =========================================
-- TRIGGERS: mantener totales en sales
-- =========================================
CREATE TRIGGER IF NOT EXISTS trg_items_ai AFTER INSERT ON sale_items
BEGIN
  UPDATE sales
  SET subtotal       = (SELECT sub  FROM v_sales_calc WHERE sale_id = NEW.sale_id),
      discount_total = (SELECT disc FROM v_sales_calc WHERE sale_id = NEW.sale_id),
      tax_total      = (SELECT iva  FROM v_sales_calc WHERE sale_id = NEW.sale_id),
      total          = (SELECT tot  FROM v_sales_calc WHERE sale_id = NEW.sale_id)
  WHERE id = NEW.sale_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_items_au AFTER UPDATE ON sale_items
BEGIN
  UPDATE sales
  SET subtotal       = (SELECT sub  FROM v_sales_calc WHERE sale_id = NEW.sale_id),
      discount_total = (SELECT disc FROM v_sales_calc WHERE sale_id = NEW.sale_id),
      tax_total      = (SELECT iva  FROM v_sales_calc WHERE sale_id = NEW.sale_id),
      total          = (SELECT tot  FROM v_sales_calc WHERE sale_id = NEW.sale_id)
  WHERE id = NEW.sale_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_items_ad AFTER DELETE ON sale_items
BEGIN
  UPDATE sales
  SET subtotal       = (SELECT sub  FROM v_sales_calc WHERE sale_id = OLD.sale_id),
      discount_total = (SELECT disc FROM v_sales_calc WHERE sale_id = OLD.sale_id),
      tax_total      = (SELECT iva  FROM v_sales_calc WHERE sale_id = OLD.sale_id),
      total          = (SELECT tot  FROM v_sales_calc WHERE sale_id = OLD.sale_id)
  WHERE id = OLD.sale_id;
END;

-- =========================================
-- VISTA: v_sales_paid (pagos por venta)
-- =========================================
DROP VIEW IF EXISTS v_sales_paid;
CREATE VIEW v_sales_paid AS
SELECT
  s.id AS sale_id,
  s.total AS total_doc,
  COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.sale_id = s.id),0) AS total_paid
FROM sales s;

-- =========================================
-- TRIGGERS: mantener payment_status en sales
-- =========================================
CREATE TRIGGER IF NOT EXISTS trg_pay_ai AFTER INSERT ON payments
BEGIN
  UPDATE sales
  SET payment_status = CASE
    WHEN (SELECT total_paid FROM v_sales_paid WHERE sale_id = NEW.sale_id) >= total THEN 'pagado'
    WHEN (SELECT total_paid FROM v_sales_paid WHERE sale_id = NEW.sale_id) > 0    THEN 'parcial'
    ELSE 'pendiente'
  END
  WHERE id = NEW.sale_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_pay_au AFTER UPDATE ON payments
BEGIN
  UPDATE sales
  SET payment_status = CASE
    WHEN (SELECT total_paid FROM v_sales_paid WHERE sale_id = NEW.sale_id) >= total THEN 'pagado'
    WHEN (SELECT total_paid FROM v_sales_paid WHERE sale_id = NEW.sale_id) > 0    THEN 'parcial'
    ELSE 'pendiente'
  END
  WHERE id = NEW.sale_id;
END;

CREATE TRIGGER IF NOT EXISTS trg_pay_ad AFTER DELETE ON payments
BEGIN
  UPDATE sales
  SET payment_status = CASE
    WHEN (SELECT total_paid FROM v_sales_paid WHERE sale_id = OLD.sale_id) >= total THEN 'pagado'
    WHEN (SELECT total_paid FROM v_sales_paid WHERE sale_id = OLD.sale_id) > 0    THEN 'parcial'
    ELSE 'pendiente'
  END
  WHERE id = OLD.sale_id;
END;
