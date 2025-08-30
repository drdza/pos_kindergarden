-- Categorías
INSERT OR IGNORE INTO categories(name) VALUES ('Comedor'), ('Colegiatura'), ('Uniformes'), ('Material'), ('Servicio escolar');

-- Vendedores
INSERT OR IGNORE INTO sellers(employee_code, first_name, second_name, job_tittle)
VALUES ('EMP-0001', 'Caja', 'Mostrador', 'Cajero');

--  Catálogos
INSERT OR IGNORE INTO grades(code,name) VALUES ('1','1°'),('2','2°'),('3','3°');
INSERT OR IGNORE INTO groups(code,name) VALUES ('A','A'),('B','B');
INSERT OR IGNORE INTO shifts(code,name) VALUES ('MAT','Matutino'),('VES','Vespertino');

-- Productos
INSERT OR IGNORE INTO products(sku, description, price, cost, kind, tax_rate, category_id, active)
VALUES ('P-001', 'Servicio de comedor', 300.00, 0.0, 'Servicio', 0.0, 1, 1);