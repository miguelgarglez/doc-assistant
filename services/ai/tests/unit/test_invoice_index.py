from decimal import Decimal

import pytest

from doc_assistant.domain.invoices.values import fold, norm_key, parse_amount, parse_date_range


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
