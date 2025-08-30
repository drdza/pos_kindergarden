-- =========================================
-- PRÁCTICAS/GLOBALES
-- =========================================
PRAGMA foreign_keys = ON;

-- =========================================
-- TABLA: business_config (parámetros del negocio)
-- =========================================
CREATE TABLE IF NOT EXISTS business_config (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  name TEXT NOT NULL,
  rfc TEXT NOT NULL,
  address TEXT NOT NULL,
  phone TEXT NOT NULL,
  thank_you TEXT NOT NULL,
  tax_rate REAL NOT NULL DEFAULT 0.16,   -- IVA por defecto para catálogo
  currency TEXT NOT NULL DEFAULT 'MXN'
);
INSERT OR IGNORE INTO business_config(id,name,rfc,address,phone,thank_you)
VALUES (1,'PREESCOLAR LIBERTAD Y CREATIVIDAD A.C.','XAXX010101000','Av. Ejemplo 123, CDMX','(55) 0000-0000','¡Gracias por su compra!');

-- =========================================
-- CATÁLOGOS: grados/grupos/turnos (opcionales, útiles para consistencia)
-- Si prefieres textos libres, puedes omitir estas 3 tablas y dejar checks en customers.
-- =========================================
CREATE TABLE IF NOT EXISTS grades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,  -- '1','2','3' (preescolar)
  name TEXT NOT NULL          -- '1°', '2°', '3°' (ajusta a tu taxonomía)
);
CREATE TABLE IF NOT EXISTS groups (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,  -- 'A','B','C','D'
  name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS shifts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,  -- 'MAT','VES'
  name TEXT NOT NULL          -- 'Matutino','Vespertino'
);


-- =========================================
-- TABLA: customers (alumnos)
-- Nota: se usan llaves a catálogos; si no quieres catálogos, reemplaza por TEXT con CHECK.
-- =========================================
CREATE TABLE IF NOT EXISTS customers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  enrollment TEXT NOT NULL UNIQUE,
  first_name TEXT NOT NULL,
  second_name TEXT NOT NULL,
  address TEXT,
  grade_id INTEGER REFERENCES grades(id), -- o texto con CHECK
  group_id INTEGER REFERENCES groups(id), -- o texto con CHECK
  shift_id INTEGER REFERENCES shifts(id), -- o texto con CHECK
  gender TEXT CHECK (gender IN ('M','F')), -- M: Masculino o F: Femenino

  fullname_mom TEXT,
  fullname_dad TEXT,

  birth_date DATE,       -- ISO: 'YYYY-MM-DD'
  curp TEXT UNIQUE,
  phone TEXT,
  mobile_phone TEXT,
  pay_reference TEXT,
  active INTEGER NOT NULL DEFAULT 1,  -- 1=activo, 0=inactivo

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
CREATE INDEX IF NOT EXISTS idx_customers_fullname   ON customers(second_name, first_name);
CREATE INDEX IF NOT EXISTS idx_customers_classroom  ON customers(grade_id, group_id, shift_id);

-- =========================================
-- TABLA: sellers (vendedores)
-- =========================================
CREATE TABLE IF NOT EXISTS sellers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  employee_code TEXT NOT NULL UNIQUE,
  first_name TEXT NOT NULL,
  second_name TEXT NOT NULL,
  address TEXT,
  job_tittle TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,  -- 1=activo, 0=inactivo

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

CREATE INDEX IF NOT EXISTS idx_sellers_fullname  ON sellers(second_name, first_name);
CREATE INDEX IF NOT EXISTS idx_sellers_jobtittle  ON sellers(job_tittle);

-- =========================================
-- CATÁLOGO: products
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
  unit  TEXT NOT NULL DEFAULT 'n_a',     -- pz, hr, kg, etc.
  kind  TEXT NOT NULL DEFAULT 'Servicio',  -- Producto/Servicio
  tax_rate REAL NOT NULL DEFAULT 0.16,
  category_id INTEGER REFERENCES categories(id),
  active INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_products_desc  ON products(description);
CREATE INDEX IF NOT EXISTS idx_products_cat   ON products(category_id);

-- =========================================
-- VENTAS: encabezado y renglones
-- Se guardan IDs (FK) y “snapshots” de nombres para estabilidad del ticket histórico.
-- Además se almacenan totales para reportes rápidos.
-- =========================================
CREATE TABLE IF NOT EXISTS sales (
  folio TEXT PRIMARY KEY,

  -- referencias (opcionales pero recomendadas)
  customer_id INTEGER REFERENCES customers(id),
  seller_id   INTEGER REFERENCES sellers(id),

  -- snapshots para ticket/histórico inmutable
  customer TEXT NOT NULL,     -- nombre completo del alumno al momento
  seller   TEXT NOT NULL,     -- nombre completo del vendedor al momento

  -- totales de la venta
  subtotal        REAL NOT NULL DEFAULT 0 CHECK (subtotal >= 0),
  discount_total  REAL NOT NULL DEFAULT 0 CHECK (discount_total >= 0),
  tax_total       REAL NOT NULL DEFAULT 0 CHECK (tax_total >= 0),
  total           REAL NOT NULL DEFAULT 0 CHECK (total >= 0),

  -- estados
  status          TEXT NOT NULL DEFAULT 'paid',          -- open|paid|void|refund
  payment_status  TEXT NOT NULL DEFAULT 'paid',          -- unpaid|partial|paid

  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_sales_customer ON sales(customer_id);
CREATE INDEX IF NOT EXISTS idx_sales_seller   ON sales(seller_id);
CREATE INDEX IF NOT EXISTS idx_sales_created  ON sales(created_at);

CREATE TABLE IF NOT EXISTS sale_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  folio TEXT NOT NULL REFERENCES sales(folio) ON DELETE CASCADE,
  sku   TEXT REFERENCES products(sku),

  -- snapshot por línea
  description_snapshot TEXT NOT NULL,

  qty        REAL NOT NULL CHECK (qty > 0),
  unit_price REAL NOT NULL CHECK (unit_price >= 0),
  discount   REAL NOT NULL DEFAULT 0 CHECK (discount >= 0),
  tax_rate   REAL NOT NULL DEFAULT 0.16,

  -- total de la línea (con impuesto)
  line_total REAL NOT NULL CHECK (line_total >= 0)
);

CREATE INDEX IF NOT EXISTS idx_sale_items_folio ON sale_items(folio);

-- =========================================
-- PAGOS (permite split cash+tarjeta, etc.)
-- =========================================
CREATE TABLE IF NOT EXISTS payments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  folio  TEXT NOT NULL REFERENCES sales(folio) ON DELETE CASCADE,
  method TEXT NOT NULL,   -- cash|card|transfer|other (o catálogo si lo deseas)
  amount REAL NOT NULL CHECK (amount >= 0),
  reference TEXT,         -- autorización, últimos 4, folio, etc.
  created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_payments_folio ON payments(folio);

-- =========================================
-- TRIGGERS: mantenimiento de totales en sales
-- (1) al INSERT/UPDATE/DELETE en sale_items -> recalcula totales de la venta
-- (2) al INSERT/UPDATE/DELETE en payments   -> actualiza payment_status (paid/partial/unpaid)
-- Nota: cálculo simple de IVA: ( (qty*unit_price - discount) * tax_rate )
-- =========================================

-- Helper: recalcular totales de una venta
CREATE TABLE IF NOT EXISTS _calc_guard (dummy INTEGER);
DROP VIEW IF EXISTS v_sales_calc;
CREATE VIEW v_sales_calc AS
SELECT
  s.folio,
  COALESCE(SUM((si.qty*si.unit_price)          ),0) AS sub,
  COALESCE(SUM( si.discount                     ),0) AS disc,
  COALESCE(SUM(((si.qty*si.unit_price)-si.discount)*si.tax_rate),0) AS iva,
  COALESCE(SUM( ( (si.qty*si.unit_price)-si.discount ) + (((si.qty*si.unit_price)-si.discount)*si.tax_rate) ),0) AS tot
FROM sales s
LEFT JOIN sale_items si ON si.folio = s.folio
GROUP BY s.folio;

-- AFTER triggers en sale_items
CREATE TRIGGER IF NOT EXISTS trg_items_ai AFTER INSERT ON sale_items
BEGIN
  UPDATE sales
  SET subtotal       = (SELECT sub  FROM v_sales_calc WHERE folio = NEW.folio),
      discount_total = (SELECT disc FROM v_sales_calc WHERE folio = NEW.folio),
      tax_total      = (SELECT iva  FROM v_sales_calc WHERE folio = NEW.folio),
      total          = (SELECT tot  FROM v_sales_calc WHERE folio = NEW.folio)
  WHERE folio = NEW.folio;
END;

CREATE TRIGGER IF NOT EXISTS trg_items_au AFTER UPDATE ON sale_items
BEGIN
  UPDATE sales
  SET subtotal       = (SELECT sub  FROM v_sales_calc WHERE folio = NEW.folio),
      discount_total = (SELECT disc FROM v_sales_calc WHERE folio = NEW.folio),
      tax_total      = (SELECT iva  FROM v_sales_calc WHERE folio = NEW.folio),
      total          = (SELECT tot  FROM v_sales_calc WHERE folio = NEW.folio)
  WHERE folio = NEW.folio;
END;

CREATE TRIGGER IF NOT EXISTS trg_items_ad AFTER DELETE ON sale_items
BEGIN
  UPDATE sales
  SET subtotal       = (SELECT sub  FROM v_sales_calc WHERE folio = OLD.folio),
      discount_total = (SELECT disc FROM v_sales_calc WHERE folio = OLD.folio),
      tax_total      = (SELECT iva  FROM v_sales_calc WHERE folio = OLD.folio),
      total          = (SELECT tot  FROM v_sales_calc WHERE folio = OLD.folio)
  WHERE folio = OLD.folio;
END;

-- Payment status por suma de pagos
DROP VIEW IF EXISTS v_sales_paid;
CREATE VIEW v_sales_paid AS
SELECT
  s.folio,
  s.total AS total_doc,
  COALESCE((SELECT SUM(p.amount) FROM payments p WHERE p.folio = s.folio),0) AS total_paid
FROM sales s;

CREATE TRIGGER IF NOT EXISTS trg_pay_ai AFTER INSERT ON payments
BEGIN
  UPDATE sales
  SET payment_status = CASE
    WHEN (SELECT total_paid FROM v_sales_paid WHERE folio = NEW.folio) >= total THEN 'paid'
    WHEN (SELECT total_paid FROM v_sales_paid WHERE folio = NEW.folio) > 0    THEN 'partial'
    ELSE 'unpaid'
  END
  WHERE folio = NEW.folio;
END;

CREATE TRIGGER IF NOT EXISTS trg_pay_au AFTER UPDATE ON payments
BEGIN
  UPDATE sales
  SET payment_status = CASE
    WHEN (SELECT total_paid FROM v_sales_paid WHERE folio = NEW.folio) >= total THEN 'paid'
    WHEN (SELECT total_paid FROM v_sales_paid WHERE folio = NEW.folio) > 0    THEN 'partial'
    ELSE 'unpaid'
  END
  WHERE folio = NEW.folio;
END;

CREATE TRIGGER IF NOT EXISTS trg_pay_ad AFTER DELETE ON payments
BEGIN
  UPDATE sales
  SET payment_status = CASE
    WHEN (SELECT total_paid FROM v_sales_paid WHERE folio = OLD.folio) >= total THEN 'paid'
    WHEN (SELECT total_paid FROM v_sales_paid WHERE folio = OLD.folio) > 0    THEN 'partial'
    ELSE 'unpaid'
  END
  WHERE folio = OLD.folio;
END;
