from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date

from app.domain.exceptions import UnsupportedPeriodError

MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

MONTH_NAME_PATTERN = (
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
)


@dataclass(frozen=True)
class Period:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.end < self.start:
            raise UnsupportedPeriodError("Period end cannot be before start")

    @property
    def months(self) -> int:
        return (self.end.year - self.start.year) * 12 + self.end.month - self.start.month + 1

    @property
    def granularity(self) -> str:
        if (
            self.start.month == 4
            and self.start.day == 1
            and self.end.month == 3
            and self.end.day == 31
        ):
            if self.end.year == self.start.year + 1:
                return "annual_fy"
        if (
            self.start.month == 1
            and self.start.day == 1
            and self.end.month == 12
            and self.end.day == 31
        ):
            if self.end.year == self.start.year:
                return "annual_calendar"
        if self.months == 3 and self.start.day == 1 and self.end.day == _last_day(self.end):
            return "quarter"
        if self.months == 1 and self.start.day == 1 and self.end.day == _last_day(self.end):
            return "month"
        return "custom"

    @property
    def label(self) -> str:
        if self.granularity == "annual_fy":
            return f"FY{self.start.year}-{str(self.start.year + 1)[-2:]}"
        if self.granularity == "annual_calendar":
            return f"CY{self.start.year}"
        if self.granularity == "month":
            return self.start.strftime("%b %Y")
        if self.granularity == "quarter":
            quarter = (self.start.month - 1) // 3 + 1
            return f"Q{quarter} {self.start.year}"
        return f"{self.start.isoformat()} to {self.end.isoformat()}"

    def overlaps(self, other: Period) -> bool:
        return self.start <= other.end and other.start <= self.end

    def same_as(self, other: Period) -> bool:
        return self.start == other.start and self.end == other.end


def _last_day(value: date) -> int:
    return calendar.monthrange(value.year, value.month)[1]


def month_period(year: int, month: int) -> Period:
    return Period(date(year, month, 1), date(year, month, _last_day(date(year, month, 1))))


def fy_period(start_year: int) -> Period:
    return Period(date(start_year, 4, 1), date(start_year + 1, 3, 31))


def previous_fy_period(today: date | None = None) -> Period:
    current = today or date.today()
    start_year = current.year if current.month >= 4 else current.year - 1
    return fy_period(start_year - 1)


def period_from_dates(start: date | None, end: date | None) -> Period | None:
    if start is None or end is None:
        return None
    try:
        return Period(start, end)
    except UnsupportedPeriodError:
        return None


def quarter_period(start_year: int, quarter: int) -> Period:
    if quarter not in {1, 2, 3, 4}:
        raise UnsupportedPeriodError("Quarter must be between 1 and 4")
    start_month = {1: 4, 2: 7, 3: 10, 4: 1}[quarter]
    year = start_year if quarter != 4 else start_year + 1
    start = date(year, start_month, 1)
    end_month = start_month + 2 if start_month <= 10 else start_month - 10
    end_year = year if start_month <= 10 else year + 1
    return Period(start, date(end_year, end_month, _last_day(date(end_year, end_month, 1))))


def parse_period(text: str) -> Period | None:
    if not text or not text.strip():
        return None
    value = text.strip().lower()

    quarter_match = re.search(r"\bq([1-4])\s*(?:fy\s*)?(\d{4})(?:\s*[-/]\s*(\d{2,4}))?", value)
    if quarter_match:
        start_year = int(quarter_match.group(2))
        return quarter_period(start_year, int(quarter_match.group(1)))

    fy_match = re.search(r"(?:fy\s*)?(\d{2,4})\s*[-/]\s*(\d{2,4})", value)
    if fy_match:
        s_token = fy_match.group(1)
        start_year = int(s_token) if len(s_token) == 4 else int(f"20{s_token}")
        end_token = fy_match.group(2)
        end_year = int(end_token) if len(end_token) == 4 else int(f"20{end_token}")
        if end_year == start_year + 1:
            return fy_period(start_year)

    range_match = re.search(
        r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*(?:-|to|until|through)\s*(\d{1,2})[/-](\d{1,2})[/-](\d{4})",
        value,
    )
    if range_match:
        start = date(
            int(range_match.group(3)),
            int(range_match.group(2)),
            int(range_match.group(1)),
        )
        end = date(
            int(range_match.group(6)),
            int(range_match.group(5)),
            int(range_match.group(4)),
        )
        return Period(start, end)

    month_match = re.search(rf"{MONTH_NAME_PATTERN}\s*[-/ ]\s*(\d{{4}})", value)
    if month_match:
        month = MONTHS[month_match.group(1)]
        year = int(month_match.group(2))
        return month_period(year, month)

    iso_month = re.search(r"\b(\d{4})-(\d{2})\b", value)
    if iso_month:
        year = int(iso_month.group(1))
        month = int(iso_month.group(2))
        if 1 <= month <= 12:
            return month_period(year, month)

    annual_match = re.search(r"(?:annual|yearly|full year)\s*(?:fy\s*)?(\d{4})", value)
    if annual_match:
        return fy_period(int(annual_match.group(1)))

    return None


def periods_comparable(left: Period | None, right: Period | None) -> bool:
    if left is None or right is None:
        return False
    return left.granularity == right.granularity and left.same_as(right)
