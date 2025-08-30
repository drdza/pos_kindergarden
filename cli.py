# cli.py
from datetime import datetime
import typer, shutil
from pathlib import Path
import sqlite3
from config import DB_PATH
from db.init import init_db, schema_path, get_connection
from db.migrate import apply_migrations
from typing import Optional

app = typer.Typer(help="Herramientas de base de datos (SQLite)")

@app.command("init-db")
def init_db_cmd():
    """Crea/reescribe la estructura base desde db/schema.sql"""
    typer.echo(f"DB: {DB_PATH}")
    init_db(schema_path())
    typer.secho("OK: esquema inicial aplicado.", fg=typer.colors.GREEN)

@app.command("migrate")
def migrate_cmd():
    """Aplica migraciones en db/migrations/*.sql"""
    done = apply_migrations(Path("db") / "migrations")
    if done:
        for f in done: typer.echo(f"aplicada: {f}")
    else:
        typer.echo("No hay migraciones pendientes.")

@app.command("seed")
def seed_cmd(seed_file: Path = typer.Option(Path("db")/"seed.sql")):
    """Ejecuta datos semilla"""
    if not seed_file.exists():
        typer.echo("Seed no encontrado.")
        raise typer.Exit(code=1)
    sql = seed_file.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(sql)
        conn.commit()
    typer.secho("OK: seed aplicado.", fg=typer.colors.GREEN)

@app.command("integrity-check")
def integrity_check():
    """PRAGMA integrity_check"""
    with get_connection() as conn:
        res = conn.execute("PRAGMA integrity_check;").fetchone()[0]
    typer.secho(f"integrity_check: {res}", fg=typer.colors.GREEN)

@app.command("vacuum")
def vacuum():
    """Compacción y mantenimiento"""
    with get_connection() as conn:
        conn.execute("VACUUM;")
        conn.commit()
    typer.secho("OK: VACUUM.", fg=typer.colors.GREEN)

@app.command("backup")
def backup(dst: Optional[Path] = typer.Option(  # <-- Optional[Path]
    None,
    help="Ruta del archivo destino. Si se omite, se crea data/backup_YYYY-MM-DD.db",
)):
    """Copia en caliente usando backup API de sqlite3"""

    if dst is None:
        dst = Path("data") / f"backup_{datetime.now():%Y-%m-%d}.db"

    dst.parent.mkdir(exist_ok=True)
    
    with get_connection() as src_conn, sqlite3.connect(dst) as dst_conn:
        src_conn.backup(dst_conn)
    typer.secho(f"Backup creado en: {dst}", fg=typer.colors.GREEN)


@app.command("testing")
def test_flow():
    from services.sales_service import alta_venta
    folio = alta_venta(
        customer_name="Juan Pérez",
        seller_name="Caja Mostrador",
        items_ui=[
        {"sku":"P001", "descripcion":"Café Americano 12oz", "qty":1, "unit_price":25.0, "tax_rate":0.16},
        {"descripcion":"Servicio especial", "qty":1, "unit_price":50.0, "tax_rate":0.0}
        ],
        payments=[{"method":"cash", "amount":75.0}]
    )
    print("Folio:", folio)


if __name__ == "__main__":
    app()
