import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        [
            "enero",
            "febrero",
            "marzo",
            "abril",
            "mayo",
            "junio",
            "julio",
            "agosto",
            "septiembre",
            "octubre",
            "noviembre",
            "diciembre",
        ]
    )
}
MONTHS["setiembre"] = 9

# Words that never identify a party: question filler, invoice vocabulary, legal forms.
STOP = {
    "a",
    "al",
    "ante",
    "cual",
    "cuales",
    "cuanto",
    "cuanta",
    "cuantos",
    "cuantas",
    "como",
    "de",
    "del",
    "el",
    "la",
    "las",
    "lo",
    "los",
    "en",
    "es",
    "son",
    "y",
    "o",
    "u",
    "con",
    "sin",
    "por",
    "para",
    "que",
    "quien",
    "cuyo",
    "cuya",
    "cuyos",
    "cuyas",
    "me",
    "mi",
    "le",
    "les",
    "se",
    "su",
    "sus",
    "un",
    "una",
    "unos",
    "unas",
    "hay",
    "tiene",
    "tienen",
    "tengo",
    "ha",
    "han",
    "he",
    "dame",
    "dime",
    "muestra",
    "muestrame",
    "lista",
    "listar",
    "ver",
    "quiero",
    "saber",
    "hola",
    "favor",
    "sobre",
    "entre",
    "mas",
    "menos",
    "total",
    "totales",
    "importe",
    "importes",
    "precio",
    "final",
    "base",
    "imponible",
    "iva",
    "irpf",
    "retencion",
    "recargo",
    "cuota",
    "iban",
    "nif",
    "cif",
    "dni",
    "fecha",
    "fechas",
    "emision",
    "vencimiento",
    "numero",
    "factura",
    "facturas",
    "fra",
    "fras",
    "emisor",
    "emisora",
    "emitida",
    "emitidas",
    "emitido",
    "emitidos",
    "emite",
    "emiten",
    "cliente",
    "clientes",
    "recibida",
    "recibidas",
    "pagar",
    "pagarle",
    "pago",
    "cobra",
    "cobrar",
    "cobro",
    "suma",
    "sumar",
    "euros",
    "euro",
    "eur",
    "valor",
    "datos",
    "dato",
    "todas",
    "todos",
    "toda",
    "todo",
    "esta",
    "este",
    "estas",
    "estos",
    "ese",
    "esa",
    "sl",
    "sa",
    "slu",
    "scp",
    "sc",
    "cb",
    "sll",
    "sociedad",
    "limitada",
    "anonima",
}
LEGAL = {"sl", "sa", "slu", "scp", "sc", "cb", "sll", "s", "l", "p", "c", "u"}

NIF_RE = re.compile(r"\b(?:[A-Za-z][- ]?\d{7,8}[- ]?[A-Za-z0-9]?|\d{8}[- ]?[A-Za-z])\b")


def fold(s: str | None) -> str:
    """Accent- and case-insensitive, punctuation as spaces."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).casefold()
    return " ".join(re.sub(r"[^0-9a-z]+", " ", s).split())


def norm_key(s: str | None) -> str:
    """Invoice numbers and NIFs: alphanumerics only, upper case."""
    return "".join(ch for ch in fold(s).upper() if ch.isalnum())


def tokens(s: str | None) -> list[str]:
    return [t for t in fold(s).split() if len(t) >= 3 and t not in STOP]


def parse_amount(value: Any) -> Decimal | None:
    """'1.650,00 €', '1,650.00', '1650.5', '{1650}', '1650 euros' -> Decimal."""
    if value is None:
        return None
    raw = re.sub(r"(?i)euros?|eur|€|[{}\s%]", "", str(value))
    if not re.fullmatch(r"[+-]?[\d.,]*\d", raw or "x"):
        return None
    if "," in raw and "." in raw:
        dec = "," if raw.rfind(",") > raw.rfind(".") else "."
        raw = raw.replace("." if dec == "," else ",", "").replace(",", ".")
    elif "," in raw:
        if raw.count(",") > 1:
            return None
        raw = raw.replace(",", ".")
    elif raw.count(".") > 1 or re.fullmatch(r"[+-]?\d{1,3}\.\d{3}", raw):
        if not re.fullmatch(r"[+-]?\d{1,3}(?:\.\d{3})+", raw):
            return None
        raw = raw.replace(".", "")
    try:
        return Decimal(raw)
    except InvalidOperation:
        return None


def cents(value: Any) -> int | None:
    d = parse_amount(value)
    return None if d is None else int((d * 100).to_integral_value())


def _mk(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def parse_date_range(value: Any) -> tuple[str, str] | None:
    """A day or a month in common Spanish forms -> (first ISO day, last ISO day)."""
    s = fold(str(value)) if value is not None else ""
    if not s:
        return None
    parts = [p for p in s.split() if p != "de"]
    nums = [int(p) for p in parts if p.isdigit()]
    month = next((MONTHS[p] for p in parts if p in MONTHS), None)
    day: date | None = None
    if month is not None:
        years = [n for n in nums if n > 31]
        days = [n for n in nums if n <= 31]
        if len(years) != 1:
            return None
        if days:
            day = _mk(years[0], month, days[0])
        else:
            return _month(years[0], month)
    elif len(nums) == 3:
        a, b, c = nums
        day = _mk(a, b, c) if a > 31 else _mk(c if c > 99 else 2000 + c, b, a)
    elif len(nums) == 2:
        a, b = nums
        if a > 31 and 1 <= b <= 12:
            return _month(a, b)
        if b > 31 and 1 <= a <= 12:
            return _month(b, a)
        return None
    elif len(nums) == 1 and nums[0] > 1900:
        return (f"{nums[0]:04d}-01-01", f"{nums[0]:04d}-12-31")
    if day is None:
        return None
    return (day.isoformat(), day.isoformat())


def _month(y: int, m: int) -> tuple[str, str] | None:
    if not 1 <= m <= 12:
        return None
    nxt = date(y + (m == 12), m % 12 + 1, 1)
    last = date.fromordinal(nxt.toordinal() - 1)
    return (date(y, m, 1).isoformat(), last.isoformat())


def parse_date(value: Any) -> str | None:
    r = parse_date_range(value)
    return r[0] if r and r[0] == r[1] else None
