import sqlite3

from doc_assistant.application.invoices.query import FIELDS
from doc_assistant.infra.invoices.index import sync_derived
from doc_assistant.infra.invoices.sqlite import InvoiceDB
from doc_assistant.infra.storage.chunks import SCHEMA_VERSION


def test_migration_from_v012_table_is_idempotent(tmp_path):
    """A database written before the derived index exists gets it on open; reruns are no-ops,
    edits and deletions in `facturas` propagate, and `facturas` itself is never rewritten."""
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    cols = ", ".join(f"{k} TEXT" for k in FIELDS)
    con.execute(
        f"CREATE TABLE facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
    )
    con.execute(
        "INSERT INTO facturas (numero, emisor, importe_total, fecha_emision) VALUES ('A-1', 'Ana Ruiz', '1.200,50', '07 marzo 2026')"
    )
    con.execute(
        "INSERT INTO facturas (numero, emisor, importe_total) VALUES ('A-2', 'Bea Gil', '10')"
    )
    con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    con.commit()
    before = con.execute("SELECT * FROM facturas ORDER BY numero").fetchall()
    con.close()

    db = InvoiceDB(str(path))
    assert db.sync() == {"removed": 0, "updated": 0, "total": 2}
    row = db.con.execute(
        "SELECT total_c, fecha_emision_iso, emisor_fold FROM facturas_q WHERE numero='A-1'"
    ).fetchone()
    assert row == (120050, "2026-03-07", "ana ruiz")
    assert db.con.execute("SELECT * FROM facturas ORDER BY numero").fetchall() == before

    db.con.execute("UPDATE facturas SET importe_total = '99' WHERE numero = 'A-1'")
    db.con.execute("DELETE FROM facturas WHERE numero = 'A-2'")
    db.con.commit()
    assert sync_derived(db.con, list(FIELDS)) == {"removed": 1, "updated": 1, "total": 1}
    assert db.con.execute("SELECT total_c FROM facturas_q").fetchall() == [(9900,)]
    assert db.con.execute("SELECT count(*) FROM partes_fts").fetchone() == (1,)
    assert sync_derived(db.con, list(FIELDS))["updated"] == 0
