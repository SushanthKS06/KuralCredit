from __future__ import annotations

from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from app.core.constants import DEFAULT_CURRENCY, SUPPORTED_CURRENCIES
from app.domain.exceptions import InvalidAmountError

MONEY_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value: str | int | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise InvalidAmountError("Boolean values are not valid amounts")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise InvalidAmountError(f"Invalid amount: {value!r}") from exc


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)


def validate_currency(currency: str) -> str:
    normalized = (currency or DEFAULT_CURRENCY).upper()
    if normalized not in SUPPORTED_CURRENCIES:
        raise InvalidAmountError(f"Unsupported currency: {currency}")
    return normalized


def sum_money(values: Iterable[Decimal]) -> Decimal:
    total = ZERO
    for value in values:
        total += quantize_money(to_decimal(value))
    return quantize_money(total)


def subtract_money(left: Decimal, right: Decimal) -> Decimal:
    return quantize_money(to_decimal(left) - to_decimal(right))


def percentage_difference(reference: Decimal, observed: Decimal) -> Decimal | None:
    reference = to_decimal(reference)
    observed = to_decimal(observed)
    if reference == 0:
        return None
    return ((observed - reference) / abs(reference) * Decimal("100")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def is_within_tolerance(reference: Decimal, observed: Decimal, tolerance_percent: Decimal) -> bool:
    difference = percentage_difference(reference, observed)
    if difference is None:
        return reference == observed
    return abs(difference) <= abs(to_decimal(tolerance_percent))


def format_indian_grouping(value: Decimal | str | int) -> str:
    amount = quantize_money(to_decimal(value))
    sign = "-" if amount < 0 else ""
    absolute = abs(amount)
    integer_part, _, decimal_part = f"{absolute:.2f}".partition(".")
    digits = integer_part
    if len(digits) <= 3:
        grouped = digits
    else:
        last_three = digits[-3:]
        remainder = digits[:-3]
        groups: list[str] = []
        while len(remainder) > 2:
            groups.insert(0, remainder[-2:])
            remainder = remainder[:-2]
        if remainder:
            groups.insert(0, remainder)
        grouped = ",".join(groups) + "," + last_three
    return f"{sign}{grouped}.{decimal_part}"


def format_inr(value: Decimal | str | int) -> str:
    return f"INR {format_indian_grouping(value)}"


def decimal_to_string(value: Decimal) -> str:
    return format(quantize_money(value), "f")
