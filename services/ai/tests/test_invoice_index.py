import sqlite3
from decimal import Decimal

import pytest

from doc_assistant.domain.invoices.values import fold, norm_key, parse_amount, parse_date_range
from doc_assistant.infra.storage.chunks import SCHEMA_VERSION
from doc_assistant.invoice_index import sync_derived
from doc_assistant.invoice_query import FIELDS
from doc_assistant.invoices import InvoiceDB


def test_fold_and_keys():
    assert fold("Lucía MARTÍN, Ortéga") == "lucia martin ortega"
    assert fold("Cafetería El Plaza, S.C.P.") == "cafeteria el plaza s c p"
    assert norm_key("12345678-k") == norm_key("12345678 K") == "12345678K"


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("1706.60", "1706.60"),
        ("1.706,60", "1706.60"),
        ("1,706.60", "1706.60"),
        ("1706,6", "1706.6"),
        ("1.650", "1650"),
        ("{1650}", "1650"),
        ("1650 €", "1650"),
        ("1650 euros", "1650"),
    ],
)
def test_amounts(raw, want):
    assert parse_amount(raw) == Decimal(want)


@pytest.mark.parametrize("raw", ["mucho", "1.2.3", "", None, "1,2,3"])
def test_bad_amounts(raw):
    assert parse_amount(raw) is None


@pytest.mark.parametrize(
    ("raw", "want"),
    [
        ("07 marzo 2026", ("2026-03-07", "2026-03-07")),
        ("7 de marzo de 2026", ("2026-03-07", "2026-03-07")),
        ("14/02/2026", ("2026-02-14", "2026-02-14")),
        ("2026-02-14", ("2026-02-14", "2026-02-14")),
        ("marzo de 2026", ("2026-03-01", "2026-03-31")),
        ("2026-02", ("2026-02-01", "2026-02-28")),
        ("12/2026", ("2026-12-01", "2026-12-31")),
        ("2026", ("2026-01-01", "2026-12-31")),
    ],
)
def test_dates(raw, want):
    assert parse_date_range(raw) == want


@pytest.mark.parametrize("raw", ["ayer", "31/02/2026", "marzo"])
def test_bad_dates(raw):
    assert parse_date_range(raw) is None


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
