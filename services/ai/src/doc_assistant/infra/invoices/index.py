"""Derived, query-ready view of the `facturas` table and entity resolution over it.

`facturas` stays the source of truth (upload and source removal write it). This module
keeps two derived tables in step with it, idempotently:
- `facturas_q`: normalised keys and typed values (dates ISO, amounts in cents), indexed.
- `partes_fts`: one row per (invoice, role) with the folded party name, FTS5 trigram.
`sync_derived` is the migration: safe to run on every open, on old or new databases,
and it never touches `facturas` or the chunk index (SCHEMA_VERSION is unchanged)."""

from __future__ import annotations

import hashlib
import re
import sqlite3
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from doc_assistant.domain.invoices.values import (
    LEGAL,
    STOP,
    cents,
    fold,
    norm_key,
    parse_date,
    tokens,
)

AMOUNT_COLS = {
    "base_imponible_total": "base_c",
    "cuota_iva_total": "iva_c",
    "irpf_importe": "irpf_c",
    "recargo_total": "recargo_c",
    "importe_total": "total_c",
    "irpf_tipo": "irpf_tipo_c",
}
DATE_COLS = {"fecha_emision": "fecha_emision_iso", "fecha_vencimiento": "fecha_vencimiento_iso"}
ROLES = ("emisor", "cliente")

# --- derived tables (the idempotent migration) ---------------------------------------

DERIVED_DDL = [
    """CREATE TABLE IF NOT EXISTS facturas_q (
        numero TEXT PRIMARY KEY, num_norm TEXT, emisor_fold TEXT, cliente_fold TEXT,
        nif_emisor_n TEXT, nif_cliente_n TEXT, fecha_emision_iso TEXT,
        fecha_vencimiento_iso TEXT, base_c INTEGER, iva_c INTEGER, irpf_c INTEGER,
        recargo_c INTEGER, total_c INTEGER, irpf_tipo_c INTEGER, src TEXT)""",
    "CREATE INDEX IF NOT EXISTS facturas_q_num ON facturas_q(num_norm)",
    "CREATE INDEX IF NOT EXISTS facturas_q_nif_e ON facturas_q(nif_emisor_n)",
    "CREATE INDEX IF NOT EXISTS facturas_q_nif_c ON facturas_q(nif_cliente_n)",
    "CREATE INDEX IF NOT EXISTS facturas_q_fecha ON facturas_q(fecha_emision_iso)",
    "CREATE INDEX IF NOT EXISTS facturas_q_total ON facturas_q(total_c)",
    "CREATE INDEX IF NOT EXISTS facturas_q_emisor ON facturas_q(emisor_fold)",
    "CREATE INDEX IF NOT EXISTS facturas_q_cliente ON facturas_q(cliente_fold)",
    """CREATE VIRTUAL TABLE IF NOT EXISTS partes_fts USING fts5(
        nombre_fold, numero UNINDEXED, rol UNINDEXED, nif_n UNINDEXED, nombre UNINDEXED,
        tokenize='trigram')""",
]


def _src_hash(row: dict[str, Any], fields: list[str]) -> str:
    return hashlib.sha1("\x1f".join(str(row.get(f)) for f in fields).encode()).hexdigest()


def derive(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "numero": row["numero"],
        "num_norm": norm_key(row["numero"]),
        "emisor_fold": fold(row.get("emisor")) or None,
        "cliente_fold": fold(row.get("cliente")) or None,
        "nif_emisor_n": norm_key(row.get("nif_emisor")) or None,
        "nif_cliente_n": norm_key(row.get("nif_cliente")) or None,
    }
    for f, col in DATE_COLS.items():
        out[col] = parse_date(row.get(f))
    for f, col in AMOUNT_COLS.items():
        out[col] = cents(row.get(f))
    return out


def sync_derived(con: sqlite3.Connection, fields: list[str]) -> dict[str, int]:
    """Bring facturas_q/partes_fts in line with facturas. Returns counts of changes."""
    for ddl in DERIVED_DDL:
        con.execute(ddl)
    cols = ", ".join(fields)
    base = {
        r[0]: dict(zip(fields, r))
        for r in con.execute(f"SELECT {cols} FROM facturas WHERE numero IS NOT NULL")
    }
    have = dict(con.execute("SELECT numero, src FROM facturas_q").fetchall())
    stale = [n for n in have if n not in base]
    todo = [n for n, row in base.items() if have.get(n) != _src_hash(row, fields)]
    for n in stale + todo:
        con.execute("DELETE FROM facturas_q WHERE numero = ?", (n,))
        con.execute("DELETE FROM partes_fts WHERE numero = ?", (n,))
    for n in todo:
        row = base[n]
        d = derive(row)
        d["src"] = _src_hash(row, fields)
        keys = list(d)
        con.execute(
            f"INSERT INTO facturas_q ({', '.join(keys)}) VALUES ({', '.join('?' * len(keys))})",
            [d[k] for k in keys],
        )
        for rol in ROLES:
            if row.get(rol) or row.get(f"nif_{rol}"):
                con.execute(
                    "INSERT INTO partes_fts (nombre_fold, numero, rol, nif_n, nombre) VALUES (?,?,?,?,?)",
                    (fold(row.get(rol)), n, rol, norm_key(row.get(f"nif_{rol}")), row.get(rol)),
                )
    if stale or todo:
        con.commit()
    return {"removed": len(stale), "updated": len(todo), "total": len(base)}


# --- resolution -------------------------------------------------------------------


@dataclass
class Party:
    """One real-world party: same NIF, or same folded name when there is no NIF."""

    key: str
    nombre: str
    nif: str
    roles: dict[str, set[str]] = field(default_factory=dict)  # rol -> numeros
    matched: int = 0
    exact: int = 0
    score: float = 0.0
    full: bool = False

    def numeros(self, rol: str | None) -> set[str]:
        if rol:
            return set(self.roles.get(rol, set()))
        return set().union(*self.roles.values()) if self.roles else set()


def _ratio(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if len(a) >= 4 and b.startswith(a):
        return 0.9
    return SequenceMatcher(None, a, b).ratio()


def _parties(con: sqlite3.Connection, where: str, params: list[Any]) -> dict[str, Party]:
    out: dict[str, Party] = {}
    for nombre_fold, numero, rol, nif_n, nombre in con.execute(
        f"SELECT nombre_fold, numero, rol, nif_n, nombre FROM partes_fts WHERE {where}", params
    ):
        key = nif_n or ("name:" + nombre_fold)
        p = out.setdefault(key, Party(key=key, nombre=nombre or "", nif=nif_n or ""))
        p.roles.setdefault(rol, set()).add(numero)
    return out


def resolve_nif(con: sqlite3.Connection, text: str) -> dict[str, Party]:
    n = norm_key(text)
    return _parties(con, "nif_n = ?", [n]) if n else {}


def resolve_party(con: sqlite3.Connection, text: str, threshold: float = 0.8) -> list[Party]:
    """Fuzzy, accent-insensitive party lookup. Returns the best tier of candidates:
    one Party when it is clear, several when the text is ambiguous, none when absent."""
    q = tokens(text)
    if not q:
        return []
    grams = {t[i : i + 3] for t in q for i in range(len(t) - 2)}
    match = " OR ".join('"' + g.replace('"', "") + '"' for g in grams)
    cands = _parties(
        con,
        "rowid IN (SELECT rowid FROM partes_fts WHERE partes_fts MATCH ? ORDER BY rank LIMIT 400)",
        [match],
    )
    folded_q = " ".join(q)
    scored: list[Party] = []
    for p in cands.values():
        names = [t for t in fold(p.nombre).split() if t not in LEGAL and len(t) >= 3]
        if not names:
            continue
        best = [max(_ratio(t, n) for n in names) for t in q]
        hits = [b for b in best if b >= threshold]
        if not hits:
            continue
        p.matched, p.exact = len(hits), sum(1 for b in hits if b == 1.0)
        p.score = sum(hits) / len(q)
        p.full = " ".join(names) == folded_q
        scored.append(p)
    if not scored:
        return []
    full = [p for p in scored if p.full]
    if full:
        return full
    rank = max((p.matched, p.exact) for p in scored)
    top = [p for p in scored if (p.matched, p.exact) == rank]
    if len(top) > 1:
        best_score = max(p.score for p in top)
        clear = [p for p in top if p.score >= best_score - 0.05]
        if len(clear) < len(top):
            top = clear
    return sorted(top, key=lambda p: (-p.score, p.nombre))


def party_tokens(con: sqlite3.Connection) -> set[str]:
    out: set[str] = set()
    for (nf,) in con.execute("SELECT DISTINCT nombre_fold FROM partes_fts"):
        out.update(
            t for t in (nf or "").split() if len(t) >= 3 and t not in LEGAL and t not in STOP
        )
    return out


def resolve_number(con: sqlite3.Connection, text: str) -> list[str]:
    """Exact, then normalised, then a trailing run of the number's groups
    ('0042', '2026 0042' -> FAC-2026-0042). Several results mean ambiguity."""
    if not text:
        return []
    exact = [r[0] for r in con.execute("SELECT numero FROM facturas_q WHERE numero = ?", (text,))]
    if exact:
        return exact
    n = norm_key(text)
    if not n:
        return []
    same = [r[0] for r in con.execute("SELECT numero FROM facturas_q WHERE num_norm = ?", (n,))]
    if same or len(n) < 4:
        return same
    out = []
    for numero, num_norm in con.execute(
        "SELECT numero, num_norm FROM facturas_q WHERE num_norm LIKE ?", ("%" + n,)
    ):
        groups = [norm_key(g) for g in re.split(r"[^0-9A-Za-z]+", fold(numero)) if g]
        cuts = {len("".join(groups[i:])) for i in range(len(groups))}
        if len(n) in cuts:
            out.append(numero)
    if out:
        return sorted(out)
    # leading zeros dropped ('FAC-2026-42'): compare digit groups by value, tail-aligned
    want = _loose_groups(text)
    if len(want) < 2 and not (want and len(want[0]) >= 3):
        return []
    hits = []
    for (numero,) in con.execute("SELECT numero FROM facturas_q"):
        have = _loose_groups(numero)
        if len(have) >= len(want) and have[-len(want) :] == want:
            hits.append(numero)
    return sorted(hits)


def _loose_groups(s: str) -> list[str]:
    groups = re.findall(r"[a-z]+|\d+", fold(s))
    return [g.lstrip("0") or "0" if g.isdigit() else g for g in groups]
