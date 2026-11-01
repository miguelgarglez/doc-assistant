import sqlite3
from typing import Any

from doc_assistant.domain.invoices.fields import FIELD_SPECS
from doc_assistant.domain.invoices.values import norm_key
from doc_assistant.infra.invoices.index import sync_derived
from doc_assistant.infra.storage.chunks import SCHEMA_VERSION, ensure_schema

FIELDS = {key: spec.label for key, spec in FIELD_SPECS.items()}


class InvoiceDB:
    def __init__(self, path: str = ":memory:") -> None:
        ensure_schema(path)
        self.con = sqlite3.connect(path)
        cols = ", ".join(f"{k} TEXT" for k in FIELDS)
        self.con.execute(
            f"CREATE TABLE IF NOT EXISTS facturas ({cols}, fichero TEXT, cuadra TEXT, motivo TEXT, PRIMARY KEY(numero))"
        )
        self.con.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        self.sync()

    def sync(self) -> dict[str, int]:
        """Idempotent migration of the derived query tables (see invoice_index)."""
        return sync_derived(self.con, list(FIELDS))

    def upsert(
        self,
        rec: dict[str, Any],
        fichero: str = "",
        cuadra: str = "",
        motivo: str | None = None,
        *,
        commit: bool = True,
    ) -> None:
        vals = [None if rec.get(k) in (None, "") else str(rec[k]) for k in FIELDS]
        q = ",".join("?" * (len(FIELDS) + 3))
        self.con.execute(
            f"INSERT OR REPLACE INTO facturas VALUES ({q})", [*vals, fichero, cuadra, motivo]
        )
        if commit:
            self.con.commit()
            self.sync()

    def rows(self) -> list[dict[str, Any]]:
        cur = self.con.execute("SELECT * FROM facturas ORDER BY numero")
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def get(self, numero: str) -> dict[str, Any] | None:
        want = norm_key(numero)
        rows = self.rows()
        exact = [row for row in rows if row["numero"] == numero]
        hits = exact or [row for row in rows if want and norm_key(row["numero"]) == want]
        return hits[0] if len(hits) == 1 else None
