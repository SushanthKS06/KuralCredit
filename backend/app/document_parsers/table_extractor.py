from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal

from app.document_parsers.base import ParsedDocument, TableData
from app.document_parsers.profiles import DocumentProfile
from app.domain.money import quantize_money, sum_money, to_decimal
from app.domain.number_normalizer import normalize_amount
from app.domain.period import Period, parse_period


@dataclass
class ExtractedFactDraft:
    field_key: str
    label: str
    raw_value: str
    normalized_value: str
    currency: str
    period_start: date | None
    period_end: date | None
    measure_type: str
    source_type: str
    source_locator: str
    notes: str


@dataclass
class ExtractionOutcome:
    facts: list[ExtractedFactDraft] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    status: str = "parsed"
    requires_model: bool = False


def _find_column(headers: list[str], aliases: list[str]) -> int | None:
    normalized = [header.strip().lower() for header in headers]
    for alias in aliases:
        target = alias.strip().lower()
        if target in normalized:
            return normalized.index(target)
    return None


def _row_value(row: dict[str, object], headers: list[str], index: int | None) -> object:
    if index is None:
        return None
    return row.get(headers[index])


def _parse_amount(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return quantize_money(to_decimal(str(value)))
    text = str(value).strip()
    if not text:
        return None
    return normalize_amount(text)


def _parse_date(value: object, formats: list[str]) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _locator(table: TableData) -> str:
    if not table.row_numbers:
        return f"sheet {table.sheet}" if table.sheet else table.name
    first, last = table.row_numbers[0], table.row_numbers[-1]
    span = f"row {first}" if first == last else f"rows {first}-{last}"
    if table.sheet:
        return f"sheet {table.sheet} {span}"
    return span


def _aggregate_bank_credits(
    table: TableData, profile: DocumentProfile
) -> tuple[ExtractedFactDraft | None, list[str]]:
    notes: list[str] = []
    headers = table.headers
    credit_index = _find_column(headers, profile.columns.credit)
    amount_index = _find_column(headers, profile.columns.amount)
    date_index = _find_column(headers, profile.columns.date)
    if credit_index is None and amount_index is None:
        return None, [
            "No credit or amount column was found. The parser does not guess whether a "
            "transaction is a credit or a debit."
        ]
    if credit_index is None:
        return None, [
            "An amount column exists but no explicit credit column. Bank credits are not inferred "
            "from ambiguous amounts."
        ]
    credits: list[Decimal] = []
    dates: list[date] = []
    for row in table.rows:
        amount = _parse_amount(_row_value(row, headers, credit_index))
        if amount is None or amount == 0:
            continue
        credits.append(abs(amount))
        parsed_date = _parse_date(_row_value(row, headers, date_index), profile.date_formats)
        if parsed_date:
            dates.append(parsed_date)
    if not credits:
        return None, ["No non-zero credit rows were found."]
    total = sum_money(credits)
    period_start = min(dates) if dates else None
    period_end = max(dates) if dates else None
    notes.append(
        f"Summed {len(credits)} credit rows. Bank credits are not revenue and may include "
        "transfers, loan proceeds, refunds and non-business deposits."
    )
    if period_start is None:
        notes.append("No transaction dates could be parsed; the fact has no comparable period.")
    return (
        ExtractedFactDraft(
            field_key=profile.field_key,
            label=profile.label,
            raw_value=f"Sum of {len(credits)} credit rows",
            normalized_value=f"{total:.2f}",
            currency="INR",
            period_start=period_start,
            period_end=period_end,
            measure_type=profile.measure_type,
            source_type=profile.source_type,
            source_locator=_locator(table),
            notes=profile.notes,
        ),
        notes,
    )


def _aggregate_gst(
    table: TableData, profile: DocumentProfile
) -> tuple[ExtractedFactDraft | None, list[str]]:
    notes: list[str] = []
    headers = table.headers
    turnover_index = _find_column(headers, profile.columns.turnover)
    period_index = _find_column(headers, profile.columns.period)
    if turnover_index is None:
        return None, ["No GST turnover column was found."]
    amounts: list[Decimal] = []
    periods: list[Period] = []
    for row in table.rows:
        amount = _parse_amount(_row_value(row, headers, turnover_index))
        if amount is None:
            continue
        amounts.append(abs(amount))
        if period_index is not None:
            parsed = parse_period(str(_row_value(row, headers, period_index) or ""))
            if parsed is not None:
                periods.append(parsed)
    if not amounts:
        return None, ["No non-zero GST turnover values were found."]
    if periods:
        for index, left in enumerate(periods):
            for right in periods[index + 1 :]:
                if left.overlaps(right):
                    return None, [
                        "GST rows contain overlapping periods. Values were not summed; "
                        "a reviewer must resolve the overlap."
                    ]
    total = sum_money(amounts)
    period_start = min((period.start for period in periods), default=None)
    period_end = max((period.end for period in periods), default=None)
    if period_start is None:
        notes.append("No GST periods could be parsed; the fact has no comparable period.")
    notes.append(
        f"Summed {len(amounts)} GST turnover rows. GST turnover is not the same measure as total "
        "sales or bank credits."
    )
    return (
        ExtractedFactDraft(
            field_key=profile.field_key,
            label=profile.label,
            raw_value=f"Sum of {len(amounts)} GST rows",
            normalized_value=f"{total:.2f}",
            currency="INR",
            period_start=period_start,
            period_end=period_end,
            measure_type=profile.measure_type,
            source_type=profile.source_type,
            source_locator=_locator(table),
            notes=profile.notes,
        ),
        notes,
    )


def _aggregate_sales_register(
    table: TableData, profile: DocumentProfile
) -> tuple[list[ExtractedFactDraft], list[str]]:
    notes: list[str] = []
    headers = table.headers
    amount_index = _find_column(headers, profile.columns.amount)
    mode_index = _find_column(headers, profile.columns.payment_mode)
    date_index = _find_column(headers, profile.columns.date)
    if amount_index is None:
        return [], ["No sales amount column was found."]
    cash_total: list[Decimal] = []
    all_total: list[Decimal] = []
    dates: list[date] = []
    for row in table.rows:
        amount = _parse_amount(_row_value(row, headers, amount_index))
        if amount is None:
            continue
        all_total.append(abs(amount))
        parsed_date = _parse_date(_row_value(row, headers, date_index), profile.date_formats)
        if parsed_date:
            dates.append(parsed_date)
        if mode_index is not None:
            mode = str(_row_value(row, headers, mode_index) or "").strip().lower()
            if "cash" in mode:
                cash_total.append(abs(amount))
    facts: list[ExtractedFactDraft] = []
    period_start = min(dates) if dates else None
    period_end = max(dates) if dates else None
    if cash_total:
        total = sum_money(cash_total)
        facts.append(
            ExtractedFactDraft(
                field_key="cash_sales",
                label="Cash sales (applicant-provided register)",
                raw_value=f"Sum of {len(cash_total)} cash rows",
                normalized_value=f"{total:.2f}",
                currency="INR",
                period_start=period_start,
                period_end=period_end,
                measure_type="cash_sales",
                source_type="sales_register",
                source_locator=_locator(table),
                notes=profile.notes,
            )
        )
        notes.append(f"Summed {len(cash_total)} cash payment rows from the sales register.")
    else:
        notes.append("No cash payment rows were found in the sales register.")
    if all_total:
        total = sum_money(all_total)
        facts.append(
            ExtractedFactDraft(
                field_key="sales_register_total",
                label="Sales register total (applicant-provided)",
                raw_value=f"Sum of {len(all_total)} register rows",
                normalized_value=f"{total:.2f}",
                currency="INR",
                period_start=period_start,
                period_end=period_end,
                measure_type="sales_register_total",
                source_type="sales_register",
                source_locator=_locator(table),
                notes="Applicant-provided register total; not independently verified.",
            )
        )
    return facts, notes


def extract_profile_facts(parsed: ParsedDocument, profile: DocumentProfile) -> ExtractionOutcome:
    if not parsed.readable:
        return ExtractionOutcome(
            notes=parsed.notes or ["The document has no readable content."],
            status="failed",
        )
    if not parsed.tables:
        return ExtractionOutcome(
            notes=[
                "This document has no tabular data for deterministic extraction. "
                "Model-assisted extraction is required."
            ],
            status="needs_model",
            requires_model=True,
        )
    facts: list[ExtractedFactDraft] = []
    notes: list[str] = []
    for table in parsed.tables:
        if profile.aggregation == "sum_credit_rows":
            fact, table_notes = _aggregate_bank_credits(table, profile)
            notes.extend(table_notes)
            if fact:
                facts.append(fact)
        elif profile.aggregation == "sum_period_rows":
            fact, table_notes = _aggregate_gst(table, profile)
            notes.extend(table_notes)
            if fact:
                facts.append(fact)
        elif profile.aggregation == "sum_cash_sales":
            table_facts, table_notes = _aggregate_sales_register(table, profile)
            notes.extend(table_notes)
            facts.extend(table_facts)
        else:
            notes.append(f"Unknown aggregation rule: {profile.aggregation}")
    status = "parsed" if facts else "failed"
    return ExtractionOutcome(facts=facts, notes=notes, status=status)
