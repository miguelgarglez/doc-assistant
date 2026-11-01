import sqlite3
from typing import Any

from doc_assistant.application.invoices.types import Plan, Selection
from doc_assistant.domain.invoices.fields import FIELD_SPECS
from doc_assistant.domain.invoices.query_types import AMOUNT_COLS, DATE_COLS, Party
from doc_assistant.infra.invoices import index

FIELDS = {key: spec.label for key, spec in FIELD_SPECS.items()}
OPS = {">": ">", "<": "<", ">=": ">=", "<=": "<=", "=": "="}


class SqliteInvoiceReader:
    def __init__(self, con: sqlite3.Connection) -> None:
        self.con = con

    def resolve_nif(self, text: str) -> dict[str, Party]:
        return index.resolve_nif(self.con, text)

    def resolve_number(self, text: str) -> list[str]:
        return index.resolve_number(self.con, text)

    def resolve_party(self, text: str) -> list[Party]:
        return index.resolve_party(self.con, text)

    def party_tokens(self) -> set[str]:
        return index.party_tokens(self.con)

    def rows(self, numeros: list[str]) -> list[dict[str, Any]]:
        if not numeros:
            return []
        cur = self.con.execute(
            f"SELECT f.*, q.fecha_emision_iso FROM facturas f JOIN facturas_q q USING(numero) "
            f"WHERE numero IN ({','.join('?' * len(numeros))}) "
            "ORDER BY q.fecha_emision_iso, numero",
            numeros,
        )
        names = [d[0] for d in cur.description]
        return [dict(zip(names, r)) for r in cur.fetchall()]

    def matching_numbers(
        self, plan: Plan, sel: Selection, trace: dict[str, Any] | None = None
    ) -> list[str]:
        """Builds the WHERE from whitelisted columns only; every value is a parameter."""
        where, params = [], []
        if sel.numeros is not None:
            if not sel.numeros:
                return []
            where.append(f"q.numero IN ({','.join('?' * len(sel.numeros))})")
            params += sel.numeros
        allowed = set(AMOUNT_COLS.values()) | set(DATE_COLS.values())
        for col, op, val in plan.filtros:
            assert col in allowed and op in OPS
            where.append(f"q.{col} {OPS[op]} ?")
            params.append(val)
        date = "substr(q.fecha_emision_iso, 6)" if plan.sin_anio else "q.fecha_emision_iso"
        cut = 5 if plan.sin_anio else 0
        if plan.desde:
            where.append(f"{date} >= ?")
            params.append(plan.desde[cut:])
        if plan.hasta:
            where.append(f"{date} <= ?")
            params.append(plan.hasta[cut:])
        for c in plan.tiene:
            assert c in FIELDS
            col = f"q.{AMOUNT_COLS[c]}" if c in AMOUNT_COLS else f"f.{c}"
            where.append(
                f"{col} IS NOT NULL" + (" AND " + col + " != 0" if c in AMOUNT_COLS else "")
            )
        sql = (
            "SELECT q.numero FROM facturas_q q JOIN facturas f USING(numero)"
            + (" WHERE " + " AND ".join(where) if where else "")
            + " ORDER BY q.fecha_emision_iso, q.numero"
        )
        if trace is not None:
            trace["sql"] = sql
            trace["params"] = params.copy()
        return [r[0] for r in self.con.execute(sql, params)]
