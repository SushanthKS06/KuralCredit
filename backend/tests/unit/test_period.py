from __future__ import annotations

from app.domain.period import fy_period, parse_period, periods_comparable


def test_parse_periods():
    fy = parse_period("FY2025-26")
    assert fy is not None
    assert fy.label == "FY2025-26"
    assert fy.start.year == 2025
    assert fy.end.year == 2026

    short_fy = parse_period("FY25-26")
    assert short_fy is not None
    assert short_fy.start.year == 2025


def test_quarter_takes_precedence_over_fiscal_year_range():
    quarter = parse_period("Q1 FY2025-26")
    assert quarter is not None
    assert quarter.start.isoformat() == "2025-04-01"
    assert quarter.end.isoformat() == "2025-06-30"


def test_period_comparability():
    p1 = fy_period(2025)
    p2 = fy_period(2025)
    p3 = fy_period(2024)

    assert periods_comparable(p1, p2) is True
    assert periods_comparable(p1, p3) is False
    assert periods_comparable(p1, None) is False
