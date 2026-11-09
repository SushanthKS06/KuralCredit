from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from app.domain.money import quantize_money

SCALE_WORDS: dict[str, Decimal] = {
    "hundred": Decimal("100"),
    "thousand": Decimal("1000"),
    "k": Decimal("1000"),
    "lakh": Decimal("100000"),
    "lakhs": Decimal("100000"),
    "lac": Decimal("100000"),
    "lacs": Decimal("100000"),
    "crore": Decimal("10000000"),
    "crores": Decimal("10000000"),
    "cr": Decimal("10000000"),
}

ONES: dict[str, int] = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
}
TENS: dict[str, int] = {
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
}

CURRENCY_NOISE = re.compile(
    r"(?:₹|rs\.?|inr|rupees?|indian rupees?|/-)",
    re.IGNORECASE,
)
NUMBER_TOKEN = re.compile(
    r"(?P<sign>-)?(?P<number>\d[\d,]*(?:\.\d+)?)\s*(?P<scale>lakhs?|lacs?|crores?|cr|thousand|k)?\b",
    re.IGNORECASE,
)
WORD_AMOUNT = re.compile(
    r"\b((?:(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
    r"thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|"
    r"forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|lakhs?|lacs?|crores?|"
    r"and)\s*)+)\b",
    re.IGNORECASE,
)
COMPOSITE_AMOUNT = re.compile(
    r"(?P<major>\d[\d,]*(?:\.\d+)?)\s*(?P<major_scale>crores?|cr|lakhs?|lacs?)\s+"
    r"(?P<minor>\d[\d,]*(?:\.\d+)?)\s*(?P<minor_scale>crores?|cr|lakhs?|lacs?|thousand|k)\b",
    re.IGNORECASE,
)
SCALE_RANK = {
    "thousand": 1,
    "k": 1,
    "lakh": 2,
    "lakhs": 2,
    "lac": 2,
    "lacs": 2,
    "crore": 3,
    "crores": 3,
    "cr": 3,
}


def _valid_grouping(digits: str) -> bool:
    if "," not in digits:
        return True
    integer_part, _, _ = digits.partition(".")
    groups = integer_part.split(",")
    if not groups or not groups[-1].isdigit() or len(groups[-1]) != 3:
        return False
    middle = groups[1:-1]
    if middle and any(len(group) != 2 for group in middle):
        western = all(len(group) == 3 for group in groups[1:])
        if not western:
            return False
    return all(group.isdigit() and len(group) > 0 for group in groups)


def _apply_scale(number: Decimal, scale: str | None) -> Decimal:
    if not scale:
        return number
    multiplier = SCALE_WORDS.get(scale.lower())
    if multiplier is None:
        return number
    return number * multiplier


def _parse_word_amount(text: str) -> Decimal | None:
    tokens = [token for token in re.split(r"\s+", text.strip().lower()) if token and token != "and"]
    if not tokens:
        return None
    total = Decimal("0")
    current = Decimal("0")
    saw_number = False
    for token in tokens:
        if token in ONES:
            current += ONES[token]
            saw_number = True
        elif token in TENS:
            current += TENS[token]
            saw_number = True
        elif token == "hundred":
            current = (current or Decimal("1")) * 100
            saw_number = True
        elif token in SCALE_WORDS:
            total += (current or Decimal("1")) * SCALE_WORDS[token]
            current = Decimal("0")
            saw_number = True
        else:
            return None
    if not saw_number:
        return None
    return quantize_money(total + current)


def normalize_amount(text: str) -> Decimal | None:
    if not text or not text.strip():
        return None
    candidate = text.strip()
    negative = False
    if candidate.startswith("(") and candidate.endswith(")"):
        negative = True
        candidate = candidate[1:-1]
    cleaned = CURRENCY_NOISE.sub(" ", candidate)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    match = NUMBER_TOKEN.fullmatch(cleaned)
    if match:
        digits = match.group("number")
        if not _valid_grouping(digits):
            return None
        try:
            number = Decimal(digits.replace(",", ""))
        except InvalidOperation:
            return None
        value = quantize_money(_apply_scale(number, match.group("scale")))
        if match.group("sign"):
            negative = True
        return -value if negative else value

    word_match = WORD_AMOUNT.fullmatch(cleaned)
    if word_match:
        value = _parse_word_amount(word_match.group(1))
        if value is not None:
            return -value if negative else value

    found = find_amounts(candidate)
    distinct = {value for _, value in found}
    if len(distinct) == 1:
        value = next(iter(distinct))
        return -value if negative else value
    return None


def find_amounts(text: str) -> list[tuple[str, Decimal]]:
    if not text:
        return []
    results: list[tuple[str, Decimal]] = []
    cleaned = CURRENCY_NOISE.sub(" ", text)
    composite_spans: list[tuple[int, int]] = []
    for match in COMPOSITE_AMOUNT.finditer(cleaned):
        major_scale = match.group("major_scale").lower()
        minor_scale = match.group("minor_scale").lower()
        if SCALE_RANK.get(major_scale, 0) <= SCALE_RANK.get(minor_scale, 0):
            continue
        major_digits = match.group("major")
        minor_digits = match.group("minor")
        if not _valid_grouping(major_digits) or not _valid_grouping(minor_digits):
            continue
        try:
            major = Decimal(major_digits.replace(",", ""))
            minor = Decimal(minor_digits.replace(",", ""))
        except InvalidOperation:
            continue
        value = quantize_money(_apply_scale(major, major_scale) + _apply_scale(minor, minor_scale))
        results.append((match.group(0).strip(), value))
        composite_spans.append(match.span())

    def overlaps_composite(start: int, end: int) -> bool:
        return any(
            start < span_end and end > span_start for span_start, span_end in composite_spans
        )

    numeric_spans: list[tuple[int, int]] = []
    for match in NUMBER_TOKEN.finditer(cleaned):
        if overlaps_composite(*match.span()):
            continue
        digits = match.group("number")
        if not _valid_grouping(digits):
            continue
        try:
            number = Decimal(digits.replace(",", ""))
        except InvalidOperation:
            continue
        value = quantize_money(_apply_scale(number, match.group("scale")))
        if match.group("sign"):
            value = -value
        results.append((match.group(0).strip(), value))
        numeric_spans.append(match.span())
    for match in WORD_AMOUNT.finditer(cleaned):
        if overlaps_composite(*match.span()):
            continue
        if any(
            match.start() < span_end and match.end() > span_start
            for span_start, span_end in numeric_spans
        ):
            continue
        value = _parse_word_amount(match.group(1))
        if value is not None:
            results.append((match.group(1).strip(), value))
    return results


def normalize_percentage(text: str) -> Decimal | None:
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|percent|per cent)", text, re.IGNORECASE)
    if not match:
        return None
    return Decimal(match.group(1))
