#!/usr/bin/env python3
"""Deterministic offline evaluation for KuralCredit financial components.

This benchmark exercises the amount normalizer, period parser, reconciliation
rules, clarification-safety checks, and the explicit mock reasoning adapter.
It makes no network calls and does not evaluate live Groq or Gnani model
quality. Live provider verification is handled separately by
``scripts/run_provider_smoke_tests.py --live``.

Usage:
    python scripts/run_evaluation.py
    python scripts/run_evaluation.py --markdown-out docs/AI_EVALUATION.md
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.domain.fact_definitions import target_field_payload
from app.domain.financial_rules import (
    FactSnapshot,
    ReconciliationPolicy,
    compare_facts,
)
from app.domain.number_normalizer import normalize_amount
from app.domain.period import Period, fy_period, parse_period
from app.providers.adapters.local_reasoning_adapter import LocalTestReasoningAdapter

AMOUNT_CASES: list[tuple[str, str | None]] = [
    ("18 lakh", "1800000"),
    ("16 lakh 50 thousand", "1650000"),
    ("1.2 crore", "12000000"),
    ("Rs. 18,00,000", "1800000"),
    ("34,00,000.00", "3400000"),
    ("2.5 lakh", "250000"),
    ("75 thousand", "75000"),
    ("1,45,00,000", "14500000"),
    ("18,00,000.50", "1800000.50"),
    ("₹ 2.5 crore", "25000000"),
    ("1.2cr", "12000000"),
    ("75k", "75000"),
    ("eighteen lakh", "1800000"),
    ("sixteen lakh fifty thousand", "1650000"),
    ("one crore twenty five lakh", "12500000"),
    ("two hundred", "200"),
    ("fifty thousand", "50000"),
    ("-5 lakh", "-500000"),
    ("(2.5 lakh)", "-250000"),
    ("Rs 1,000", "1000"),
    ("1,000.50", "1000.50"),
    ("0", "0"),
    ("12", "12"),
    ("18 lakh rupees and GST 16 lakh", None),
    ("Rs. 18,00,000/-", "1800000"),
    ("INR 12.5 crore", "125000000"),
    ("5 crores", "50000000"),
    ("3 lakhs", "300000"),
    ("2 lacs", "200000"),
    ("1,234", "1234"),
    ("1,234,567", "1234567"),
    ("12,34,567", "1234567"),
    ("0.5 lakh", "50000"),
    ("1.05 crore", "10500000"),
    ("99,99,999", "9999999"),
    ("eight thousand five hundred", "8500"),
    ("twenty one thousand", "21000"),
    ("one lakh only", "100000"),
    ("approximately 18 lakh", "1800000"),
    ("18lakh", "1800000"),
]

PERIOD_CASES: list[tuple[str, str, str]] = [
    ("FY2025-26", "2025-04-01", "2026-03-31"),
    ("2025-2026", "2025-04-01", "2026-03-31"),
    ("FY24-25", "2024-04-01", "2025-03-31"),
    ("24-25", "2024-04-01", "2025-03-31"),
    ("FY 2025/26", "2025-04-01", "2026-03-31"),
    ("financial year 2025-26", "2025-04-01", "2026-03-31"),
    ("Q1 FY2025-26", "2025-04-01", "2025-06-30"),
    ("Q2 2025", "2025-07-01", "2025-09-30"),
    ("Q3 FY2025", "2025-10-01", "2025-12-31"),
    ("Q4 FY2025", "2026-01-01", "2026-03-31"),
    ("Q1 2026", "2026-04-01", "2026-06-30"),
    ("01/04/2025 to 31/03/2026", "2025-04-01", "2026-03-31"),
    ("01-04-2025 - 31-03-2026", "2025-04-01", "2026-03-31"),
    ("Apr 2025", "2025-04-01", "2025-04-30"),
    ("April-2025", "2025-04-01", "2025-04-30"),
    ("May 2025", "2025-05-01", "2025-05-31"),
    ("2025-06", "2025-06-01", "2025-06-30"),
    ("annual FY2025", "2025-04-01", "2026-03-31"),
    ("yearly 2026", "2026-04-01", "2027-03-31"),
    ("Jan 2026", "2026-01-01", "2026-01-31"),
]

FACT_CASES: list[dict[str, Any]] = [
    {
        "id": "fe-01",
        "text": (
            "My business is a textile shop. Last year sales were 18 lakh rupees. "
            "GST turnover was 16.5 lakh."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "1800000.00",
            "gst_turnover": "1650000.00",
        },
        "period": True,
    },
    {
        "id": "fe-02",
        "text": (
            "We run an auto spare parts workshop. Last year annual sales were "
            "42 lakh. GST turnover was 38 lakh."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Auto parts & workshop services",
            "annual_sales": "4200000.00",
            "gst_turnover": "3800000.00",
        },
        "period": True,
    },
    {
        "id": "fe-03",
        "text": (
            "This is a grocery store. Last year turnover was 25 lakh rupees. GST was 22 lakh."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Retail grocery / Kirana",
            "annual_sales": "2500000.00",
            "gst_turnover": "2200000.00",
        },
        "period": True,
    },
    {
        "id": "fe-04",
        "text": (
            "We sell textiles. Last year declared sales were 1.2 crore. GST turnover was 1.1 crore."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "12000000.00",
            "gst_turnover": "11000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-05",
        "text": (
            "Restaurant business. Last year sales were 9 lakh 50 thousand. "
            "GST turnover 8 lakh 75 thousand."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Restaurant & catering services",
            "annual_sales": "950000.00",
            "gst_turnover": "875000.00",
        },
        "period": True,
    },
    {
        "id": "fe-06",
        "text": "Clothing shop. Cash sales were 3 lakh last year.",
        "targets": ["business_type", "cash_sales"],
        "expected": {"business_type": "Textile retail", "cash_sales": "300000.00"},
        "period": True,
    },
    {
        "id": "fe-07",
        "text": ("We manufacture garments. Last year sales were 55 lakh. GST turnover 50 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Manufacturing",
            "annual_sales": "5500000.00",
            "gst_turnover": "5000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-08",
        "text": ("Wholesale trading business. Sales last year were 2.4 crore. GST 2.2 crore."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Trading",
            "annual_sales": "24000000.00",
            "gst_turnover": "22000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-09",
        "text": (
            "Salon services. Last year annual turnover was 12 lakh. GST turnover was 10 lakh."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Services",
            "annual_sales": "1200000.00",
            "gst_turnover": "1000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-10",
        "text": (
            "Hardware shop. Last year sales 7 lakh 25 thousand. GST turnover 6 lakh 80 thousand."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Retail shop",
            "annual_sales": "725000.00",
            "gst_turnover": "680000.00",
        },
        "period": True,
    },
    {
        "id": "fe-11",
        "text": ("Textile retail. Sales for FY2025-26 were 88 lakh. GST was 84 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "8800000.00",
            "gst_turnover": "8400000.00",
        },
        "period": True,
    },
    {
        "id": "fe-12",
        "text": ("Auto garage. Last year sales were 1 crore 20 lakh. GST was 95 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Auto parts & workshop services",
            "annual_sales": "12000000.00",
            "gst_turnover": "9500000.00",
        },
        "period": True,
    },
    {
        "id": "fe-13",
        "text": ("Agro fertilizer shop. Sales last year were 33 lakh. GST turnover 30 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Agro supplies & fertilizers",
            "annual_sales": "3300000.00",
            "gst_turnover": "3000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-14",
        "text": ("Kirana supermarket. Last year sales 60 lakh. GST turnover 54 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Retail grocery / Kirana",
            "annual_sales": "6000000.00",
            "gst_turnover": "5400000.00",
        },
        "period": True,
    },
    {
        "id": "fe-15",
        "text": ("Catering business. Last year sales 15 lakh. GST turnover 12 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Restaurant & catering services",
            "annual_sales": "1500000.00",
            "gst_turnover": "1200000.00",
        },
        "period": True,
    },
    {
        "id": "fe-16",
        "text": (
            "We do consulting services. Last year annual sales were 45 lakh. "
            "GST turnover was 40 lakh."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Services",
            "annual_sales": "4500000.00",
            "gst_turnover": "4000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-17",
        "text": ("Factory production unit. Last year sales 8 crore. GST turnover 7.5 crore."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Manufacturing",
            "annual_sales": "80000000.00",
            "gst_turnover": "75000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-18",
        "text": ("Wholesale distributor. Sales were 3.6 crore last year. GST 3.3 crore."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Trading",
            "annual_sales": "36000000.00",
            "gst_turnover": "33000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-19",
        "text": ("Saree shop. Sales last year were 70 lakh. GST turnover 65 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "7000000.00",
            "gst_turnover": "6500000.00",
        },
        "period": True,
    },
    {
        "id": "fe-20",
        "text": ("Vehicle spare parts shop. Last year sales 28 lakh. GST 24 lakh."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Auto parts & workshop services",
            "annual_sales": "2800000.00",
            "gst_turnover": "2400000.00",
        },
        "period": True,
    },
    {
        "id": "fe-21",
        "text": ("Textile shop. Sales were Rs 1,80,000 last year. GST turnover was Rs 1,65,000."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "180000.00",
            "gst_turnover": "165000.00",
        },
        "period": True,
    },
    {
        "id": "fe-22",
        "text": ("Grocery store. Sales were 18,00,000 last year. GST was 16,50,000."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Retail grocery / Kirana",
            "annual_sales": "1800000.00",
            "gst_turnover": "1650000.00",
        },
        "period": True,
    },
    {
        "id": "fe-23",
        "text": (
            "Restaurant. Sales were eighteen lakh rupees last year. "
            "GST turnover was sixteen lakh fifty thousand rupees."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Restaurant & catering services",
            "annual_sales": "1800000.00",
            "gst_turnover": "1650000.00",
        },
        "period": True,
    },
    {
        "id": "fe-24",
        "text": (
            "Manufacturing unit. Sales were 2 crore 50 lakh last year. GST was 2 crore 30 lakh."
        ),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Manufacturing",
            "annual_sales": "25000000.00",
            "gst_turnover": "23000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-25",
        "text": ("Retail shop. Last year sales were 1.5 crore. GST turnover was 1.4 crore."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Retail shop",
            "annual_sales": "15000000.00",
            "gst_turnover": "14000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-26",
        "text": ("Textile business. Sales were 75 thousand last year. GST turnover 70 thousand."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "75000.00",
            "gst_turnover": "70000.00",
        },
        "period": True,
    },
    {
        "id": "fe-27",
        "text": ("Trading. Sales were 10 lakh 25 thousand last year. GST 9 lakh 50 thousand."),
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Trading",
            "annual_sales": "1025000.00",
            "gst_turnover": "950000.00",
        },
        "period": True,
    },
    {
        "id": "fe-28",
        "text": "Service center. Sales were 22 lakh last year. GST turnover 20 lakh.",
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Services",
            "annual_sales": "2200000.00",
            "gst_turnover": "2000000.00",
        },
        "period": True,
    },
    {
        "id": "fe-29",
        "text": "Shop. Sales were 5 lakh last year. GST 4 lakh 50 thousand.",
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Retail shop",
            "annual_sales": "500000.00",
            "gst_turnover": "450000.00",
        },
        "period": True,
    },
    {
        "id": "fe-30",
        "text": "Textile store. Sales were 30 lakh last year. GST 27 lakh.",
        "targets": ["business_type", "annual_sales", "gst_turnover"],
        "expected": {
            "business_type": "Textile retail",
            "annual_sales": "3000000.00",
            "gst_turnover": "2700000.00",
        },
        "period": True,
    },
]

CLARIFICATION_FIELDS: list[tuple[str, str, str]] = [
    ("declared_sales_vs_gst_turnover_difference", "Values differ", "amount"),
    ("declared_sales_vs_bank_credit_context", "Different measures", "text"),
    ("gst_turnover_vs_bank_credit_context", "Different measures", "text"),
    ("cash_sales_vs_bank_credit_context", "Cash may not be banked", "text"),
    ("annual_sales", "Missing annual sales", "amount"),
    ("gst_turnover", "Missing GST turnover", "amount"),
    ("bank_credits", "Missing bank credits", "amount"),
    ("cash_sales", "Missing cash sales", "amount"),
    ("sales_register_total", "Missing sales register", "amount"),
    ("business_type", "Missing business type", "text"),
    ("years_in_operation", "Missing operating history", "number"),
    ("gst_filing_status", "Missing GST filing status", "text"),
    ("gst_period", "Missing GST period", "date"),
    ("bank_credit_context", "Need neutral context", "text"),
    ("cash_sales_context", "Need neutral context", "text"),
    ("customer_receipts", "Need receipt context", "amount"),
    ("own_account_transfer", "Need transfer context", "amount"),
    ("loan_disbursement", "Need loan context", "amount"),
    ("sales_register_evidence", "Need register evidence", "text"),
    ("declared_vs_document_difference", "Difference needs explanation", "text"),
]

FORBIDDEN_CLARIFICATION_TERMS = (
    "fraud",
    "approve",
    "approval",
    "reject",
    "eligible",
    "eligibility",
    "credit score",
    "risk grade",
)


def _snapshot(
    field_key: str,
    measure_type: str,
    value: str,
    *,
    period: Period | None = None,
    provenance: str = "applicant_confirmed",
    version: int = 1,
) -> FactSnapshot:
    return FactSnapshot(
        id=f"f-{field_key}-{version}",
        field_key=field_key,
        label=field_key.replace("_", " "),
        measure_type=measure_type,
        normalized_value=value,
        raw_value=value,
        currency="INR",
        period=period,
        source_type="applicant_text",
        provenance_status=provenance,
        version=version,
    )


def _comparison(
    left: FactSnapshot | None,
    right: FactSnapshot | None,
    *,
    policy: ReconciliationPolicy | None = None,
    explanation: bool = False,
) -> dict[str, Any]:
    result = compare_facts(
        left,
        right,
        policy or ReconciliationPolicy(),
        explanation_present=explanation,
    )
    return {
        "status": result.status.value,
        "requires_clarification": result.requires_clarification,
    }


def _reconciliation_cases() -> list[dict[str, Any]]:
    fy25 = fy_period(2025)
    fy24 = fy_period(2024)
    declared = _snapshot("annual_sales", "declared_sales", "1000000", period=fy25)
    gst = _snapshot("gst_turnover", "gst_turnover", "1000000", period=fy25)
    bank = _snapshot("bank_credits", "bank_credit", "1000000", period=fy25)
    cash = _snapshot("cash_sales", "cash_sales", "1000000", period=fy25)
    return [
        {
            "id": "rc-01",
            "expected": {"status": "within_tolerance", "requires_clarification": False},
            "actual": _comparison(declared, gst),
        },
        {
            "id": "rc-02",
            "expected": {"status": "within_tolerance", "requires_clarification": False},
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1040000", period=fy25),
            ),
        },
        {
            "id": "rc-03",
            "expected": {"status": "within_tolerance", "requires_clarification": False},
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1050000", period=fy25),
            ),
        },
        {
            "id": "rc-04",
            "expected": {
                "status": "difference_requires_context",
                "requires_clarification": True,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1060000", period=fy25),
            ),
        },
        {
            "id": "rc-05",
            "expected": {
                "status": "difference_requires_context",
                "requires_clarification": True,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "900000", period=fy25),
            ),
        },
        {
            "id": "rc-06",
            "expected": {
                "status": "difference_requires_context",
                "requires_clarification": True,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1200000", period=fy25),
            ),
        },
        {
            "id": "rc-07",
            "expected": {"status": "context_provided", "requires_clarification": False},
            "actual": _comparison(declared, bank, explanation=True),
        },
        {
            "id": "rc-08",
            "expected": {
                "status": "not_comparable_measure",
                "requires_clarification": True,
            },
            "actual": _comparison(declared, bank),
        },
        {
            "id": "rc-09",
            "expected": {
                "status": "not_comparable_measure",
                "requires_clarification": True,
            },
            "actual": _comparison(gst, bank),
        },
        {
            "id": "rc-10",
            "expected": {
                "status": "not_comparable_measure",
                "requires_clarification": True,
            },
            "actual": _comparison(cash, bank),
        },
        {
            "id": "rc-11",
            "expected": {
                "status": "not_comparable_measure",
                "requires_clarification": False,
            },
            "actual": _comparison(declared, cash),
        },
        {
            "id": "rc-12",
            "expected": {
                "status": "not_comparable_period",
                "requires_clarification": False,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1000000", period=fy24),
            ),
        },
        {
            "id": "rc-13",
            "expected": {
                "status": "not_comparable_period",
                "requires_clarification": False,
            },
            "actual": _comparison(
                declared,
                _snapshot(
                    "gst_turnover",
                    "gst_turnover",
                    "1000000",
                    period=Period(date(2025, 4, 1), date(2025, 4, 30)),
                ),
            ),
        },
        {
            "id": "rc-14",
            "expected": {
                "status": "not_comparable_period",
                "requires_clarification": False,
            },
            "actual": _comparison(
                _snapshot("annual_sales", "declared_sales", "1000000"),
                gst,
            ),
        },
        {
            "id": "rc-15",
            "expected": {
                "status": "not_comparable_period",
                "requires_clarification": False,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1000000"),
            ),
        },
        {
            "id": "rc-16",
            "expected": {
                "status": "missing_information",
                "requires_clarification": False,
            },
            "actual": _comparison(None, gst),
        },
        {
            "id": "rc-17",
            "expected": {
                "status": "missing_information",
                "requires_clarification": False,
            },
            "actual": _comparison(declared, None),
        },
        {
            "id": "rc-18",
            "expected": {"status": "within_tolerance", "requires_clarification": False},
            "actual": _comparison(
                _snapshot("annual_sales", "declared_sales", "0", period=fy25),
                _snapshot("gst_turnover", "gst_turnover", "0", period=fy25),
            ),
        },
        {
            "id": "rc-19",
            "expected": {
                "status": "difference_requires_context",
                "requires_clarification": True,
            },
            "actual": _comparison(
                _snapshot("annual_sales", "declared_sales", "0", period=fy25),
                _snapshot("gst_turnover", "gst_turnover", "100", period=fy25),
            ),
        },
        {
            "id": "rc-20",
            "expected": {"status": "within_tolerance", "requires_clarification": False},
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1080000", period=fy25),
                policy=ReconciliationPolicy(tolerance_percent=Decimal("10")),
            ),
        },
        {
            "id": "rc-21",
            "expected": {
                "status": "difference_requires_context",
                "requires_clarification": True,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "1030000", period=fy25),
                policy=ReconciliationPolicy(tolerance_percent=Decimal("2")),
            ),
        },
        {
            "id": "rc-22",
            "expected": {
                "status": "difference_requires_context",
                "requires_clarification": True,
            },
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "950000", period=fy25),
            ),
        },
        {
            "id": "rc-23",
            "expected": {"status": "within_tolerance", "requires_clarification": False},
            "actual": _comparison(
                declared,
                _snapshot("gst_turnover", "gst_turnover", "960000", period=fy25),
            ),
        },
        {
            "id": "rc-24",
            "expected": {"status": "context_provided", "requires_clarification": False},
            "actual": _comparison(bank, declared, explanation=True),
        },
        {
            "id": "rc-25",
            "expected": {
                "status": "not_comparable_measure",
                "requires_clarification": False,
            },
            "actual": _comparison(cash, declared),
        },
    ]


def evaluate_amounts() -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    started = time.perf_counter()
    for text, expected in AMOUNT_CASES:
        actual = normalize_amount(text)
        expected_value = Decimal(expected) if expected is not None else None
        if actual != expected_value:
            failures.append(
                {
                    "input": text,
                    "expected": expected,
                    "actual": format(actual, "f") if actual is not None else None,
                }
            )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _suite_result("Amount normalization", len(AMOUNT_CASES), failures, elapsed_ms)


def evaluate_periods() -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    started = time.perf_counter()
    for text, expected_start, expected_end in PERIOD_CASES:
        period = parse_period(text)
        actual = f"{period.start.isoformat()}..{period.end.isoformat()}" if period else None
        expected = f"{expected_start}..{expected_end}"
        if actual != expected:
            failures.append({"input": text, "expected": expected, "actual": str(actual)})
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _suite_result("Period parsing", len(PERIOD_CASES), failures, elapsed_ms)


def _extract_mock_facts(case: dict[str, Any]) -> list[dict[str, Any]]:
    adapter = LocalTestReasoningAdapter()
    result = adapter.extract_applicant_facts(
        transcript=case["text"],
        target_fields=target_field_payload(case["targets"]),
        language="en-IN",
        prior_facts=[],
    )
    return list(result.data.get("candidate_facts", []))


def evaluate_fact_extraction() -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    failed_cases = 0
    started = time.perf_counter()
    for case in FACT_CASES:
        facts = _extract_mock_facts(case)
        extracted = {fact["field_key"]: str(fact["normalized_candidate"]) for fact in facts}
        case_failures: list[dict[str, str]] = []
        for field_key, expected in case["expected"].items():
            actual = extracted.get(field_key)
            if actual != expected:
                case_failures.append(
                    {
                        "id": case["id"],
                        "field": field_key,
                        "expected": expected,
                        "actual": str(actual),
                    }
                )
        if case["period"]:
            for fact in facts:
                field_key = fact["field_key"]
                expected = case["expected"].get(field_key)
                if expected is None or "." not in expected:
                    continue
                if not fact.get("period_start"):
                    case_failures.append(
                        {
                            "id": case["id"],
                            "field": field_key,
                            "expected": "non-null period",
                            "actual": "null",
                        }
                    )
        if case_failures:
            failed_cases += 1
            failures.extend(case_failures)
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _suite_result(
        "Mock fact extraction",
        len(FACT_CASES),
        failures,
        elapsed_ms,
        failed_count=failed_cases,
    )


def evaluate_reconciliation() -> dict[str, Any]:
    cases = _reconciliation_cases()
    failures: list[dict[str, str]] = []
    started = time.perf_counter()
    for case in cases:
        if case["actual"] != case["expected"]:
            failures.append(
                {
                    "id": case["id"],
                    "expected": json.dumps(case["expected"], sort_keys=True),
                    "actual": json.dumps(case["actual"], sort_keys=True),
                }
            )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _suite_result("Reconciliation rules", len(cases), failures, elapsed_ms)


def evaluate_clarifications() -> dict[str, Any]:
    adapter = LocalTestReasoningAdapter()
    failures: list[dict[str, str]] = []
    started = time.perf_counter()
    for field_key, reason, answer_type in CLARIFICATION_FIELDS:
        result = adapter.generate_clarification(
            field_key=field_key,
            reason=reason,
            known_facts=[],
            language="en-IN",
            expected_answer_type=answer_type,
        )
        data = result.data
        question = str(data.get("question", ""))
        problems: list[str] = []
        if data.get("target_field") != field_key:
            problems.append("target_field mismatch")
        if data.get("language") != "en-IN":
            problems.append("language changed")
        if not question.strip():
            problems.append("empty question")
        if len(question.split()) > 40:
            problems.append("question too long")
        lowered = question.lower()
        for term in FORBIDDEN_CLARIFICATION_TERMS:
            if term in lowered:
                problems.append(f"forbidden term: {term}")
        if problems:
            failures.append(
                {
                    "field": field_key,
                    "expected": "safe neutral question",
                    "actual": "; ".join(problems),
                }
            )
    elapsed_ms = (time.perf_counter() - started) * 1000
    return _suite_result(
        "Clarification safety",
        len(CLARIFICATION_FIELDS),
        failures,
        elapsed_ms,
    )


def _suite_result(
    name: str,
    total: int,
    failures: list[dict[str, str]],
    latency_ms: float,
    *,
    failed_count: int | None = None,
) -> dict[str, Any]:
    failed = len(failures) if failed_count is None else failed_count
    passed = max(total - failed, 0)
    return {
        "name": name,
        "total": total,
        "passed": passed,
        "failed": failed,
        "accuracy_pct": round((passed / total) * 100, 2) if total else 0.0,
        "latency_ms": round(latency_ms, 2),
        "failures": failures,
    }


def _status(suite: dict[str, Any]) -> str:
    return "PASS" if suite["failed"] == 0 else "FAIL"


def render_markdown(results: list[dict[str, Any]], generated_at: str) -> str:
    lines = [
        "# AI and Rules Evaluation",
        "",
        f"Generated by `scripts/run_evaluation.py` on {generated_at}.",
        "",
        "## Scope and honest limitations",
        "",
        "This is an offline, deterministic benchmark. It validates amount",
        "normalization, period parsing, reconciliation policy, clarification",
        "safety checks, and the explicit mock reasoning adapter used for demos and",
        "tests. It does **not** measure live Groq GPT-OSS 120B or Gnani Prisma",
        "quality. Live provider verification requires rotated credentials and is",
        "reported by `scripts/run_provider_smoke_tests.py --live`.",
        "",
        "| Suite | Cases | Passed | Failed | Accuracy | Status |",
        "| --- | ---: | ---: | ---: | ---: | --- |",
    ]
    for suite in results:
        lines.append(
            f"| {suite['name']} | {suite['total']} | {suite['passed']} | "
            f"{suite['failed']} | {suite['accuracy_pct']:.2f}% | {_status(suite)} |"
        )
    total_cases = sum(suite["total"] for suite in results)
    total_passed = sum(suite["passed"] for suite in results)
    overall = round((total_passed / total_cases) * 100, 2) if total_cases else 0.0
    lines.extend(
        [
            "",
            f"**Overall deterministic accuracy: {overall:.2f}% "
            f"({total_passed}/{total_cases} cases).**",
            "",
            "## Live provider evaluation",
            "",
            "**BLOCKED in this environment.** No live Groq or Gnani request was",
            "made while producing this report. Previously exposed credentials must",
            "be rotated by the owner before live checks are meaningful.",
            "",
            "Required follow-up after rotation:",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\run_provider_smoke_tests.py --live",
            "```",
            "",
            "## Failure details",
            "",
        ]
    )
    any_failures = False
    for suite in results:
        if not suite["failures"]:
            continue
        any_failures = True
        lines.append(f"### {suite['name']}")
        lines.append("")
        for failure in suite["failures"]:
            lines.append(f"- `{json.dumps(failure, ensure_ascii=False, sort_keys=True)}`")
        lines.append("")
    if not any_failures:
        lines.append("No deterministic benchmark failures were recorded.")
        lines.append("")
    lines.extend(
        [
            "## Reproduction",
            "",
            "```powershell",
            ".\\.venv\\Scripts\\python.exe scripts\\run_evaluation.py",
            "```",
            "",
            "The benchmark exits non-zero if any deterministic case fails.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run deterministic KuralCredit evaluation.")
    parser.add_argument(
        "--markdown-out",
        default="docs/AI_EVALUATION.md",
        help="Markdown report path (default: docs/AI_EVALUATION.md).",
    )
    parser.add_argument(
        "--json-out",
        default=None,
        help="Optional JSON results path.",
    )
    args = parser.parse_args()

    print("=" * 64)
    print("  KuralCredit Deterministic AI & Rules Evaluation")
    print("=" * 64)
    print("  No live provider calls are made by this benchmark.")

    results = [
        evaluate_amounts(),
        evaluate_periods(),
        evaluate_fact_extraction(),
        evaluate_reconciliation(),
        evaluate_clarifications(),
    ]

    for suite in results:
        print(f"\n{suite['name']}:")
        print(
            f"  {_status(suite)}  {suite['passed']}/{suite['total']} "
            f"({suite['accuracy_pct']:.2f}%), {suite['latency_ms']} ms"
        )
        for failure in suite["failures"][:5]:
            print(f"  - {failure}")
        if len(suite["failures"]) > 5:
            print(f"  - ... {len(suite['failures']) - 5} more failure(s)")

    markdown_path = Path(args.markdown_out)
    if not markdown_path.is_absolute():
        markdown_path = Path(__file__).resolve().parents[1] / markdown_path
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    generated_at = date.today().isoformat()
    markdown_path.write_text(render_markdown(results, generated_at), encoding="utf-8")
    print(f"\nMarkdown report written to {markdown_path}")

    if args.json_out:
        json_path = Path(args.json_out)
        if not json_path.is_absolute():
            json_path = Path(__file__).resolve().parents[1] / json_path
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"JSON results written to {json_path}")

    failed = [suite["name"] for suite in results if suite["failed"]]
    if failed:
        print(f"\n[FAIL] Deterministic evaluation failed: {', '.join(failed)}")
        return 1
    print("\n[PASS] All deterministic evaluation cases passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
