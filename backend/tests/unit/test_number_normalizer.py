from __future__ import annotations

from decimal import Decimal

from app.domain.number_normalizer import find_amounts, normalize_amount


def test_amount_normalization():
    assert normalize_amount("18 lakh") == Decimal("1800000.00")
    assert normalize_amount("18 lakhs") == Decimal("1800000.00")
    assert normalize_amount("18 lac") == Decimal("1800000.00")
    assert normalize_amount("1.5 crore") == Decimal("15000000.00")
    assert normalize_amount("2 cr") == Decimal("20000000.00")
    assert normalize_amount("16 lakh 50 thousand") == Decimal("1650000.00")
    assert normalize_amount("Rs. 18,00,000") == Decimal("1800000.00")
    assert normalize_amount("₹ 34,00,000.00") == Decimal("3400000.00")
    assert normalize_amount("(40,000)") == Decimal("-40000.00")
    assert normalize_amount("invalid") is None


def test_find_amounts_in_text():
    text = "Sales were 18 lakh and GST turnover was 16.5 lakh."
    found = find_amounts(text)
    assert len(found) >= 2
    raw_str, amount = found[0]
    assert amount == Decimal("1800000.00")
