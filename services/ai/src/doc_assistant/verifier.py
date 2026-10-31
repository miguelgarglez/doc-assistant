"""Local citation and quantity checks, not a semantic entailment verifier.

None is abstention. Units are compared literally after typography normalization,
without conversion. A lone separator followed by three digits denotes grouping
unless the integer part is zero. Negation and injection guards are heuristics.
"""

import re
import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
from typing import Any


@dataclass
class Result:
    ok: bool
    reason: str
    details: dict[str, Any] = field(default_factory=dict)


_TYPOGRAPHY = str.maketrans(
    {
        **dict.fromkeys("“”„‟«»", '"'),
        **dict.fromkeys("‘’‚‛", "'"),
        **dict.fromkeys("‐‑‒–—―−", "-"),
        "º": "°",
    }
)
_STOPWORDS = frozenset({"y", "con", "de", "el", "la"})
_TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)
_NEGATION = re.compile(r"\b(?:no|nunca|jamás|jamas|sin|tampoco|ni|not|never)\b")
_INJECTION = re.compile(
    r"\b(?:ignora(?:r)?|ignore|disregard|omite|olvida|forget)\b.{0,100}"
    r"\b(?:instrucciones|instructions|reglas|rules|prompt|anterior(?:es)?|previous)\b"
    r"|\b(?:responde|respond|answer|devuelve|return)\s+(?:solo\s+|only\s+)?[+-]?\d",
    re.IGNORECASE,
)
_NUMBER = (
    r"[+-]?(?:\d{1,3}(?: \d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)*|[.,]\d+)"
    r"(?:[eE][+-]?\d+)?"
)
_POWER = r"(?:[23]|\^[+-]?\d+)?"
_UNIT_FACTOR = rf"[a-zµμ]+{_POWER}"
# Only recognized symbols may extend a unit across a space. A general word
# pattern here would absorb the prose following a quantity, such as "W para".
_SPACE_FACTOR = (
    r"(?-i:(?:[YZEPTGMkhdcmunpfazyµμ]?(?:mol|cd|Hz|Pa|m|s|g|A|K|W|V|N|J|C|F|S|T|H|L|l)"
    r"|min|h|bar|rpm))" + _POWER + r"(?!\w)"
)
_QUANTITY = re.compile(
    rf"(?<![\w.,])(?P<first>{_NUMBER})"
    rf"(?:\s*(?:a|to|hasta|-)\s*(?P<last>{_NUMBER}))?"
    rf"\s*(?P<unit>[%‰]|°(?:\s?[CFK](?!\w))?|{_UNIT_FACTOR}"
    rf"(?:\s*[/·]\s*{_UNIT_FACTOR}|\s+{_SPACE_FACTOR})*)?",
    re.IGNORECASE,
)
# Words that begin prose after a number are not units. Other alphabetic labels
# are kept conservatively as units, including units outside the SI vocabulary.
_PROSE = frozenset(
    {
        "a",
        "al",
        "and",
        "con",
        "de",
        "del",
        "el",
        "en",
        "es",
        "hasta",
        "la",
        "las",
        "los",
        "o",
        "of",
        "para",
        "por",
        "que",
        "se",
        "sin",
        "the",
        "to",
        "un",
        "una",
        "y",
    }
)


def _normalize(text: str, *, lowercase: bool = True) -> str:
    # Convert º before NFKC, which otherwise turns it into the letter o.
    text = text.translate(_TYPOGRAPHY)
    text = unicodedata.normalize("NFKC", text).translate(_TYPOGRAPHY)
    if lowercase:
        text = text.lower()
    text = text.replace("\u00ad", "")
    text = re.sub(r"(?<=[^\W\d_])-[^\S\n]*\r?\n\s*(?=[^\W\d_])", "", text)
    return " ".join(text.split())


def _decimal(raw: str) -> Decimal:
    raw = raw.replace(" ", "")
    mantissa, separator, exponent = raw.lower().partition("e")
    raw = mantissa
    unsigned = raw.lstrip("+-")
    if "," in unsigned and "." in unsigned:
        decimal_mark = "," if unsigned.rfind(",") > unsigned.rfind(".") else "."
        grouping_mark = "." if decimal_mark == "," else ","
        integer, fraction = unsigned.rsplit(decimal_mark, 1)
        groups = integer.split(grouping_mark)
        if len(groups[0]) > 3 or any(len(group) != 3 for group in groups[1:]):
            raise InvalidOperation("invalid grouping")
        normalized = integer.replace(grouping_mark, "") + "." + fraction
    elif "," in unsigned or "." in unsigned:
        mark = "," if "," in unsigned else "."
        groups = unsigned.split(mark)
        if len(groups) == 2:
            grouped = len(groups[1]) == 3 and bool(groups[0].strip("0"))
            normalized = "".join(groups) if grouped else ".".join(groups)
        else:
            if len(groups[0]) > 3 or any(len(group) != 3 for group in groups[1:]):
                raise InvalidOperation("invalid grouping")
            normalized = "".join(groups)
    else:
        normalized = unsigned
    sign = "-" if raw.startswith("-") else ""
    scientific = separator + exponent if separator else ""
    return Decimal(sign + normalized + scientific)


def _quantities(text: str) -> set[tuple[Decimal, str]]:
    facts = set()
    for match in _QUANTITY.finditer(text):
        unit = re.sub(r"\s*([/·])\s*", r"\1", match.group("unit") or "")
        unit = re.sub(r"°\s+", "°", unit)
        unit = re.sub(r"\s+", "·", unit)
        if unit.lower() in _PROSE:
            unit = ""
        facts.add((_decimal(match.group("first")), unit))
        if match.group("last") is not None:
            facts.add((_decimal(match.group("last")), unit))
    return facts


def _bounded(text: str, start: int, end: int) -> bool:
    return not (
        start > 0
        and text[start - 1].isalnum()
        and text[start].isalnum()
        or end < len(text)
        and text[end - 1].isalnum()
        and text[end].isalnum()
    )


def _negation_omitted(text: str, start: int) -> bool:
    # Refuse a quote that starts after a negation in the same clause. This is
    # deliberately conservative, and cannot determine the negation's scope.
    prefix = re.split(r"[.!?;:\n]", text[:start])[-1]
    return _NEGATION.search(prefix) is not None


def _citation_mode(text: str, quote: str, almost_literal: bool) -> str | None:
    start = text.find(quote)
    while start != -1:
        end = start + len(quote)
        if _bounded(text, start, end) and not _negation_omitted(text, start):
            return "literal"
        start = text.find(quote, start + 1)
    if not almost_literal:
        return None

    tokens = list(_TOKEN.finditer(text))
    wanted = _TOKEN.findall(quote)
    width = len(wanted)
    for offset in range(len(tokens) - width + 1):
        window = tokens[offset : offset + width]
        actual = [token.group() for token in window]
        edits = [
            op
            for op in SequenceMatcher(None, actual, wanted, autojunk=False).get_opcodes()
            if op[0] != "equal"
        ]
        if len(edits) != 1:
            continue
        tag, i, j, k, l = edits[0]
        if (
            tag == "replace"
            and j - i == l - k == 1
            and actual[i] in _STOPWORDS
            and wanted[k] in _STOPWORDS
            and not _negation_omitted(text, window[0].start())
        ):
            return "almost_literal"
    return None


def _safe_support(text: str) -> str:
    # Split only sentence punctuation followed by whitespace, keeping decimal
    # separators intact. Drop the complete sentence containing an instruction.
    sentences = re.split(r"(?<=[.!?;])\s+|\n+", text)
    return " ".join(sentence for sentence in sentences if not _INJECTION.search(sentence))


def verify(
    answer: str | None,
    citations: list[Any],
    retrieved: dict[Any, Any],
    *,
    almost_literal: bool = False,
) -> Result:
    """Validate citations and numeric support in their complete retrieved chunks.

    A successful result checks form, numeric membership and limited guards.
    It does not establish semantic truth, fact attribution, or range ordering.
    ``details['citation_modes']`` follows the order of validated citations.
    """
    details: dict[str, Any] = {"citation_modes": []}

    def reject(reason: str) -> Result:
        return Result(False, reason, details)

    if answer is not None and (not isinstance(answer, str) or not answer.strip()):
        return reject("answer must be a nonempty string or None")
    if not isinstance(citations, list) or not isinstance(retrieved, dict):
        return reject("citations must be a list and retrieved a dictionary")
    if not isinstance(almost_literal, bool):
        return reject("almost_literal must be boolean")
    if answer is not None and not citations:
        return reject("answer requires citations")

    support = set()
    for index, citation in enumerate(citations):
        if not isinstance(citation, dict):
            return reject(f"malformed citation {index}")
        if "chunk_id" not in citation or "quote" not in citation:
            return reject(f"missing citation fields in citation {index}")
        chunk_id, quote = citation.get("chunk_id"), citation.get("quote")
        try:
            present = chunk_id in retrieved
        except TypeError:
            return reject(f"unhashable chunk_id in citation {index}")
        if not present:
            return reject(f"chunk_id not retrieved in citation {index}: {chunk_id!r}")
        if not isinstance(quote, str) or not quote.strip():
            return reject(f"quote must be nonempty in citation {index}")
        chunk = retrieved[chunk_id]
        if not isinstance(chunk, str):
            return reject(f"retrieved chunk is not text in citation {index}")
        text, quote = _normalize(chunk), _normalize(quote)
        if not quote:
            return reject(f"normalized quote is empty in citation {index}")
        if _INJECTION.search(quote):
            return reject(f"instruction-like quote in citation {index}")
        mode = _citation_mode(text, quote, almost_literal)
        if mode is None:
            return reject(f"quote missing, altered, or omits negation in citation {index}")
        details["citation_modes"].append(mode)
        try:
            numeric_text = _normalize(chunk, lowercase=False)
            support.update(_quantities(_safe_support(numeric_text)))
        except InvalidOperation:
            return reject(f"ambiguous numeric format in citation {index}")

    if answer is None:
        return Result(True, "abstention", details)
    try:
        required = _quantities(_normalize(answer, lowercase=False))
    except InvalidOperation:
        return reject("invalid numeric format in answer")
    for value, unit in sorted(required, key=lambda item: (item[0], item[1])):
        if not unit and any(v == value for v, _ in support):
            # A bare number in the answer ("87", "5000") is supported when the
            # cited chunk prints that value with any unit. A unit in the answer
            # must still match exactly, so "18 m" vs "18 mm" stays rejected.
            continue
        if (value, unit) not in support:
            details["unsupported_quantity"] = {"value": str(value), "unit": unit}
            return reject(f"unsupported quantity: {value} {unit}".rstrip())
    return Result(True, "verified", details)


def quantities_supported(text: str, chunks: list[str]) -> bool:
    """True when every quantity in `text` also appears in one of `chunks`.

    Same rule as `verify` for answers: a bare number matches a value printed with any
    unit, a number with a unit must match that unit exactly.
    """
    try:
        required = _quantities(_normalize(text, lowercase=False))
        support: set[tuple[Decimal, str]] = set()
        for chunk in chunks:
            support.update(_quantities(_safe_support(_normalize(chunk, lowercase=False))))
    except InvalidOperation:
        return False
    return all(
        (value, unit) in support or (not unit and any(v == value for v, _ in support))
        for value, unit in required
    )
