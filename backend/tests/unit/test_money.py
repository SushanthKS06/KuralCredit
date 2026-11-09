from __future__ import annotations

from decimal import Decimal

import pytest

from app.domain.exceptions import InvalidAmountError
from app.domain.money import (
    format_indian_grouping,
    format_inr,
    is_within_tolerance,
    percentage_difference,
    quantize_money,
    to_decimal,
    validate_currency,
)


def test_decimal_conversion_and_rounding():
    assert to_decimal("1800000") == Decimal("1800000")
    assert to_decimal(1500) == Decimal("1500")
    assert quantize_money(Decimal("18.555")) == Decimal("18.56")
    with pytest.raises(InvalidAmountError):
        to_decimal("invalid-string")
    with pytest.raises(InvalidAmountError):
        to_decimal(True)


def test_indian_grouping():
    assert format_indian_grouping("1800000") == "18,00,000.00"
    assert format_indian_grouping("1650000") == "16,50,000.00"
    assert format_indian_grouping("12000000") == "1,20,00,000.00"
    assert format_indian_grouping("500") == "500.00"
    assert format_indian_grouping("-1800000") == "-18,00,000.00"
    assert format_inr("1800000") == "INR 18,00,000.00"


def test_percentage_difference_and_tolerance():
    # 18 lakh vs 16.5 lakh is -8.33%
    diff = percentage_difference(Decimal("1800000"), Decimal("1650000"))
    assert diff is not None
    assert diff == Decimal("-8.33")

    # Within 10% tolerance
    assert is_within_tolerance(Decimal("1800000"), Decimal("1650000"), Decimal("10")) is True
    # Outside 5% tolerance
    assert is_within_tolerance(Decimal("1800000"), Decimal("1650000"), Decimal("5")) is False


def test_currency_validation():
    assert validate_currency("INR") == "INR"
    assert validate_currency("inr") == "INR"
    with pytest.raises(InvalidAmountError):
        validate_currency("XYZ")
