#!/usr/bin/env python3
"""Synthetic Bank Statement Dataset Generator for KuralCredit.

Generates realistic, mathematically balanced Indian bank statement CSV datasets
representing various MSME business profiles with explainable variances
(personal transfers, NBFC loan disbursements, cash deposits, seasonality).

All datasets maintain strict mathematical accounting consistency:
    Balance[i] = Balance[i-1] + Credit[i] - Debit[i]
"""

from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

# Paths
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_FIXTURES = REPO_ROOT / "backend" / "app" / "fixtures" / "synthetic_bank_statements"
DATASETS_DIR = REPO_ROOT / "datasets" / "bank_statements"


def write_csv(filepath: Path, rows: list[list[str]]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [OK] Generated {filepath.name} ({len(rows) - 1} transactions)")


def verify_statement_math(rows: list[list[str]]) -> tuple[Decimal, Decimal, Decimal]:
    """Verify headers, credit sums, debit sums, and running balance consistency."""
    headers = rows[0]
    debit_idx = headers.index("Debit")
    credit_idx = headers.index("Credit")
    bal_idx = headers.index("Balance")

    total_credits = Decimal("0.00")
    total_debits = Decimal("0.00")
    prev_balance = Decimal("0.00")

    for i, row in enumerate(rows[1:], start=2):
        debit_str = row[debit_idx].strip()
        credit_str = row[credit_idx].strip()
        bal_str = row[bal_idx].strip()

        debit = Decimal(debit_str) if debit_str else Decimal("0.00")
        credit = Decimal(credit_str) if credit_str else Decimal("0.00")
        balance = Decimal(bal_str)

        total_credits += credit
        total_debits += debit

        if i == 2:
            expected_bal = credit - debit
        else:
            expected_bal = prev_balance + credit - debit

        if abs(balance - expected_bal) > Decimal("0.01"):
            raise ValueError(
                f"Row {i} balance mismatch: previous {prev_balance} + credit {credit} - debit {debit} "
                f"= expected {expected_bal}, got {balance}"
            )
        prev_balance = balance

    return total_credits, total_debits, prev_balance


# ==============================================================================
# Scenario 1: Meenakshi Handlooms & Textiles (Retail Textile Shop, Madurai)
# FY2025-26: Total Credits = ₹34,00,000.00 (EXACT)
# Declared Sales = ₹18,00,000.00
# Key Variance: ₹4,00,000 personal transfer + physical cash sales register
# ==============================================================================
def generate_meenakshi_textiles() -> list[list[str]]:
    rows = [
        ["Date", "Value Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
        [
            "01/04/2025",
            "01/04/2025",
            "Opening customer receipts NEFT - Sri Ram Silks",
            "N09123841",
            "",
            "200000.00",
            "200000.00",
        ],
        [
            "14/04/2025",
            "14/04/2025",
            "Counter sales UPI batch credit - HDFC POS",
            "UPI51049921",
            "",
            "150000.00",
            "350000.00",
        ],
        [
            "28/04/2025",
            "28/04/2025",
            "TNEB Power charges commercial",
            "NEFT992019",
            "25000.00",
            "",
            "325000.00",
        ],
        [
            "05/05/2025",
            "05/05/2025",
            "Customer receipts RTGS - Madurai Saree Palace",
            "R01928374",
            "",
            "250000.00",
            "575000.00",
        ],
        [
            "18/05/2025",
            "18/05/2025",
            "Customer receipts UPI settlement",
            "UPI51382910",
            "",
            "100000.00",
            "675000.00",
        ],
        [
            "28/05/2025",
            "28/05/2025",
            "Supplier payment cotton yarn - Lakshmi Mills",
            "CHQ009121",
            "250000.00",
            "",
            "425000.00",
        ],
        [
            "10/06/2025",
            "10/06/2025",
            "Customer receipts UPI bulk settlement",
            "U99201922",
            "",
            "300000.00",
            "725000.00",
        ],
        [
            "24/06/2025",
            "24/06/2025",
            "Shop rent Madurai main road",
            "CHQ009122",
            "45000.00",
            "",
            "680000.00",
        ],
        [
            "12/07/2025",
            "12/07/2025",
            "Customer receipts NEFT - Cauvery Silks",
            "N09123899",
            "",
            "250000.00",
            "930000.00",
        ],
        [
            "26/07/2025",
            "26/07/2025",
            "Weaving wages payout NEFT",
            "N09123905",
            "120000.00",
            "",
            "810000.00",
        ],
        [
            "20/08/2025",
            "20/08/2025",
            "Customer receipts NEFT - Tirunelveli Textiles",
            "N09123910",
            "",
            "200000.00",
            "1010000.00",
        ],
        [
            "30/08/2025",
            "30/08/2025",
            "Dyeing chemicals purchase - Apex Colours",
            "CHQ009123",
            "80000.00",
            "",
            "930000.00",
        ],
        [
            "08/09/2025",
            "08/09/2025",
            "Deepavali advance booking UPI - Sundaram",
            "UPI52519283",
            "",
            "150000.00",
            "1080000.00",
        ],
        [
            "18/09/2025",
            "18/09/2025",
            "Customer receipts IMPS - Jayam Fashions",
            "I88273910",
            "",
            "100000.00",
            "1180000.00",
        ],
        [
            "29/09/2025",
            "29/09/2025",
            "Bulk raw silk procurement - Kanchipuram",
            "RTGS001928",
            "400000.00",
            "",
            "780000.00",
        ],
        [
            "05/10/2025",
            "05/10/2025",
            "Customer receipts RTGS - Chennai Mega Mart",
            "R01928499",
            "",
            "300000.00",
            "1080000.00",
        ],
        [
            "20/10/2025",
            "20/10/2025",
            "Festival season counter UPI QR aggregate",
            "UPI52994821",
            "",
            "50000.00",
            "1130000.00",
        ],
        [
            "14/11/2025",
            "14/11/2025",
            "Customer receipts NEFT - Kongu Handlooms",
            "N09124012",
            "",
            "250000.00",
            "1380000.00",
        ],
        [
            "25/11/2025",
            "25/11/2025",
            "GST tax payment GSTR-3B Q2",
            "GST9920194",
            "45000.00",
            "",
            "1335000.00",
        ],
        [
            "09/12/2025",
            "09/12/2025",
            "Customer receipts IMPS - Wedding order bulk",
            "I88274022",
            "",
            "200000.00",
            "1535000.00",
        ],
        [
            "15/12/2025",
            "15/12/2025",
            "Personal transfer from savings - M Sundaram SB",
            "TRF99210",
            "",
            "400000.00",
            "1935000.00",
        ],
        [
            "18/12/2025",
            "18/12/2025",
            "Shop renovation & showcase fixture payment",
            "CHQ009124",
            "180000.00",
            "",
            "1755000.00",
        ],
        [
            "08/01/2026",
            "08/01/2026",
            "Pongal festive retail collection NEFT",
            "N09124110",
            "",
            "100000.00",
            "1855000.00",
        ],
        [
            "22/01/2026",
            "22/01/2026",
            "Customer receipts UPI QR code collections",
            "U99202055",
            "",
            "100000.00",
            "1955000.00",
        ],
        [
            "11/02/2026",
            "11/02/2026",
            "Customer receipts NEFT - Thanjavur Silk Store",
            "N09124190",
            "",
            "150000.00",
            "2105000.00",
        ],
        [
            "25/02/2026",
            "25/02/2026",
            "Yarn purchase invoice payment",
            "CHQ009125",
            "150000.00",
            "",
            "1955000.00",
        ],
        [
            "10/03/2026",
            "10/03/2026",
            "Customer receipts IMPS - Trichy Retail",
            "I88274150",
            "",
            "100000.00",
            "2055000.00",
        ],
        [
            "20/03/2026",
            "20/03/2026",
            "Customer receipts UPI clearing - Year end",
            "U99203112",
            "",
            "50000.00",
            "2105000.00",
        ],
    ]
    return rows


# ==============================================================================
# Scenario 2: Sri Krishna Auto Spares (Auto Components & Servicing, Coimbatore)
# FY2025-26: Total Credits = ₹29,00,000.00 (EXACT)
# Declared Sales = ₹25,00,000.00
# Key Variance: ₹5,00,000 NBFC equipment loan disbursement in Q2
# ==============================================================================
def generate_krishna_auto_spares() -> list[list[str]]:
    rows = [
        ["Date", "Value Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
        [
            "03/04/2025",
            "03/04/2025",
            "Opening balance customer NEFT - TVS Dealership",
            "NEFT0492811",
            "",
            "180000.00",
            "180000.00",
        ],
        [
            "15/04/2025",
            "15/04/2025",
            "Workshop spare parts billing UPI",
            "UPI51058291",
            "",
            "120000.00",
            "300000.00",
        ],
        [
            "28/04/2025",
            "28/04/2025",
            "Brake pads & clutch plates inventory debit",
            "CHQ104821",
            "160000.00",
            "",
            "140000.00",
        ],
        [
            "08/05/2025",
            "08/05/2025",
            "Fleet maintenance receipts - Royal Logistics",
            "RTGS019283",
            "",
            "220000.00",
            "360000.00",
        ],
        [
            "22/05/2025",
            "22/05/2025",
            "Customer billing UPI QR collection",
            "UPI51428190",
            "",
            "140000.00",
            "500000.00",
        ],
        [
            "06/06/2025",
            "06/06/2025",
            "Lubricants distributor payment - Castrol India",
            "NEFT0493920",
            "130000.00",
            "",
            "370000.00",
        ],
        [
            "18/06/2025",
            "18/06/2025",
            "Commercial vehicle fleet spares NEFT",
            "NEFT0494102",
            "",
            "190000.00",
            "560000.00",
        ],
        [
            "02/07/2025",
            "02/07/2025",
            "Workshop services counter receipts IMPS",
            "IMPS8829102",
            "",
            "150000.00",
            "710000.00",
        ],
        [
            "15/07/2025",
            "15/07/2025",
            "Bajaj Auto genuine spares inventory purchase",
            "CHQ104822",
            "210000.00",
            "",
            "500000.00",
        ],
        [
            "28/07/2025",
            "28/07/2025",
            "NBFC Business loan disbursement - Cholamandalam",
            "LN992019482",
            "",
            "500000.00",
            "1000000.00",
        ],
        [
            "10/08/2025",
            "10/08/2025",
            "Hydraulic ramp & diagnostic scanner purchase",
            "RTGS019482",
            "420000.00",
            "",
            "580000.00",
        ],
        [
            "20/08/2025",
            "20/08/2025",
            "Customer receipts NEFT - Coimbatore Cabs",
            "NEFT0495810",
            "",
            "180000.00",
            "760000.00",
        ],
        [
            "05/09/2025",
            "05/09/2025",
            "Wholesale spares sales - Erode Auto Center",
            "RTGS019512",
            "",
            "210000.00",
            "970000.00",
        ],
        [
            "22/09/2025",
            "22/09/2025",
            "Staff mechanic salaries & festival bonus",
            "NEFT0496102",
            "140000.00",
            "",
            "830000.00",
        ],
        [
            "09/10/2025",
            "09/10/2025",
            "Ayudha Pooja customer repair billings UPI",
            "UPI52819201",
            "",
            "160000.00",
            "990000.00",
        ],
        [
            "25/10/2025",
            "25/10/2025",
            "Auto electrical parts inventory payment",
            "CHQ104823",
            "175000.00",
            "",
            "815000.00",
        ],
        [
            "12/11/2025",
            "12/11/2025",
            "Customer fleet maintenance billing NEFT",
            "NEFT0497201",
            "",
            "190000.00",
            "1005000.00",
        ],
        [
            "05/12/2025",
            "05/12/2025",
            "Customer billing IMPS - Salem Transport",
            "IMPS8831920",
            "",
            "140000.00",
            "1145000.00",
        ],
        [
            "22/12/2025",
            "22/12/2025",
            "Advance tax payment Q3",
            "TAX001928",
            "35000.00",
            "",
            "1110000.00",
        ],
        [
            "10/01/2026",
            "10/01/2026",
            "Customer receipts NEFT - Tirupur Garment Vans",
            "NEFT0498192",
            "",
            "170000.00",
            "1280000.00",
        ],
        [
            "28/01/2026",
            "28/01/2026",
            "Exide Batteries distributor inventory payment",
            "CHQ104824",
            "190000.00",
            "",
            "1090000.00",
        ],
        [
            "12/02/2026",
            "12/02/2026",
            "Workshop repair billing UPI QR settlements",
            "UPI53419201",
            "",
            "150000.00",
            "1240000.00",
        ],
        [
            "08/03/2026",
            "08/03/2026",
            "Customer fleet billing RTGS - Western Express",
            "RTGS019721",
            "",
            "200000.00",
            "1440000.00",
        ],
    ]
    return rows


# ==============================================================================
# Scenario 3: Annamalai Agro Supplies (Seeds, Fertilizers & Pesticides, Thanjavur)
# FY2025-26: Total Credits = ₹12,50,000.00 (EXACT)
# Declared Sales = ₹12,00,000.00
# Key Variance: ₹50,000 timing difference in month-end clearing deposit
# ==============================================================================
def generate_annamalai_agro_supplies() -> list[list[str]]:
    rows = [
        ["Date", "Value Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
        [
            "08/04/2025",
            "08/04/2025",
            "Customer receipts UPI - Kuruvai pre-season",
            "UPI51081921",
            "",
            "75000.00",
            "75000.00",
        ],
        [
            "25/04/2025",
            "25/04/2025",
            "Fertilizer purchase - IFFCO urea delivery",
            "CHQ201941",
            "120000.00",
            "",
            "-45000.00",
        ],
        [
            "05/05/2025",
            "05/05/2025",
            "Farmers collective seed booking NEFT",
            "N0492811",
            "",
            "110000.00",
            "65000.00",
        ],
        [
            "22/05/2025",
            "22/05/2025",
            "Bio-pesticides inventory purchase",
            "NEFT0492822",
            "60000.00",
            "",
            "5000.00",
        ],
        [
            "12/06/2025",
            "12/06/2025",
            "Customer receipts NEFT - Thanjavur Paddy Farmers",
            "N0492833",
            "",
            "140000.00",
            "145000.00",
        ],
        [
            "28/06/2025",
            "28/06/2025",
            "Kharif peak season UPI counter collection",
            "UPI51728190",
            "",
            "125000.00",
            "270000.00",
        ],
        [
            "15/07/2025",
            "15/07/2025",
            "Warehouse godown rent Thanjavur bypass",
            "CHQ201942",
            "20000.00",
            "",
            "250000.00",
        ],
        [
            "10/08/2025",
            "10/08/2025",
            "Customer billing IMPS - Micro-irrigation equipment",
            "IMPS8829101",
            "",
            "85000.00",
            "335000.00",
        ],
        [
            "20/09/2025",
            "20/09/2025",
            "Customer receipts UPI - Secondary spraying inputs",
            "UPI52619201",
            "",
            "65000.00",
            "400000.00",
        ],
        [
            "15/10/2025",
            "15/10/2025",
            "Rabi winter sowing seed procurement - Mahyco",
            "CHQ201943",
            "180000.00",
            "",
            "220000.00",
        ],
        [
            "08/11/2025",
            "08/11/2025",
            "Farmer group NEFT payment - Samba crop season",
            "N0493910",
            "",
            "160000.00",
            "380000.00",
        ],
        [
            "26/11/2025",
            "26/11/2025",
            "Organic manure supplier payment - Erode",
            "NEFT0493944",
            "75000.00",
            "",
            "305000.00",
        ],
        [
            "12/12/2025",
            "12/12/2025",
            "Customer receipts UPI batch - Grain protection",
            "UPI53429102",
            "",
            "90000.00",
            "395000.00",
        ],
        [
            "05/01/2026",
            "05/01/2026",
            "Customer billing IMPS - Harvester spare blades",
            "IMPS8834910",
            "",
            "80000.00",
            "475000.00",
        ],
        [
            "18/02/2026",
            "18/02/2026",
            "Customer receipts NEFT - Summer crop inputs",
            "N0494812",
            "",
            "110000.00",
            "585000.00",
        ],
        [
            "10/03/2026",
            "10/03/2026",
            "Customer receipts UPI QR clearing",
            "UPI53819201",
            "",
            "160000.00",
            "745000.00",
        ],
        [
            "31/03/2026",
            "02/04/2026",
            "Customer outward cheque clearing in transit",
            "CHQ201955",
            "",
            "50000.00",
            "795000.00",
        ],
    ]
    return rows


# ==============================================================================
# Scenario 4: Shri Balaji Supermarket (Kirana / High-Frequency UPI Retail, Chennai)
# FY2025-26: Total Credits = ₹45,00,000.00 (EXACT)
# High transaction volume with daily UPI QR settlements, CDM cash deposits
# ==============================================================================
def generate_kirana_supermarket() -> list[list[str]]:
    rows = [
        ["Date", "Value Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
        [
            "02/04/2025",
            "02/04/2025",
            "PhonePe QR merchant daily settlement",
            "PPR99201920",
            "",
            "130000.00",
            "130000.00",
        ],
        [
            "07/04/2025",
            "07/04/2025",
            "GooglePay Business UPI settlement",
            "GPAY8820192",
            "",
            "130000.00",
            "260000.00",
        ],
        [
            "15/04/2025",
            "15/04/2025",
            "Cash Deposit Machine (CDM) counter cash deposit",
            "CDM001928",
            "",
            "180000.00",
            "440000.00",
        ],
        [
            "22/04/2025",
            "22/04/2025",
            "Hindustan Unilever distributor payment",
            "NEFT8819201",
            "240000.00",
            "",
            "200000.00",
        ],
        [
            "02/05/2025",
            "02/05/2025",
            "PhonePe QR merchant weekly settlement",
            "PPR99202110",
            "",
            "150000.00",
            "350000.00",
        ],
        [
            "12/05/2025",
            "12/05/2025",
            "Paytm Soundbox QR batch collection",
            "PYTM7720192",
            "",
            "120000.00",
            "470000.00",
        ],
        [
            "20/05/2025",
            "20/05/2025",
            "CDM branch cash deposit weekend collection",
            "CDM001955",
            "",
            "190000.00",
            "660000.00",
        ],
        [
            "28/05/2025",
            "28/05/2025",
            "ITC Limited FMCG supply payment",
            "CHQ449201",
            "210000.00",
            "",
            "450000.00",
        ],
        [
            "03/06/2025",
            "03/06/2025",
            "GooglePay Business UPI settlement",
            "GPAY8820299",
            "",
            "160000.00",
            "610000.00",
        ],
        [
            "16/06/2025",
            "16/06/2025",
            "PhonePe QR merchant settlement",
            "PPR99202450",
            "",
            "145000.00",
            "755000.00",
        ],
        [
            "25/06/2025",
            "25/06/2025",
            "Aavin Milk & Dairy distributor weekly payment",
            "NEFT8819340",
            "85000.00",
            "",
            "670000.00",
        ],
        [
            "04/07/2025",
            "04/07/2025",
            "CDM counter cash sales deposit",
            "CDM002011",
            "",
            "200000.00",
            "870000.00",
        ],
        [
            "18/07/2025",
            "18/07/2025",
            "UPI QR multi-bank settlement aggregate",
            "UPI99201948",
            "",
            "155000.00",
            "1025000.00",
        ],
        [
            "29/07/2025",
            "29/07/2025",
            "Nestle & Britannia distributor payment",
            "CHQ449202",
            "190000.00",
            "",
            "835000.00",
        ],
        [
            "05/08/2025",
            "05/08/2025",
            "PhonePe QR merchant settlement",
            "PPR99202890",
            "",
            "165000.00",
            "1000000.00",
        ],
        [
            "19/08/2025",
            "19/08/2025",
            "CDM cash deposit - Independence day sale",
            "CDM002088",
            "",
            "220000.00",
            "1220000.00",
        ],
        [
            "28/08/2025",
            "28/08/2025",
            "Shop electricity & refrigeration AMC",
            "NEFT8819490",
            "45000.00",
            "",
            "1175000.00",
        ],
        [
            "04/09/2025",
            "04/09/2025",
            "GooglePay Business UPI settlement",
            "GPAY8820410",
            "",
            "175000.00",
            "1350000.00",
        ],
        [
            "18/09/2025",
            "18/09/2025",
            "CDM cash deposit - Vinayagar Chaturthi sales",
            "CDM002144",
            "",
            "210000.00",
            "1560000.00",
        ],
        [
            "29/09/2025",
            "29/09/2025",
            "Tata Consumer Products distributor debit",
            "CHQ449203",
            "160000.00",
            "",
            "1400000.00",
        ],
        [
            "06/10/2025",
            "06/10/2025",
            "PhonePe QR festive batch collection",
            "PPR99203310",
            "",
            "190000.00",
            "1590000.00",
        ],
        [
            "19/10/2025",
            "19/10/2025",
            "Deepavali grocery pre-orders UPI batch",
            "UPI99202811",
            "",
            "210000.00",
            "1800000.00",
        ],
        [
            "25/10/2025",
            "25/10/2025",
            "CDM cash deposit festive counter sales",
            "CDM002201",
            "",
            "260000.00",
            "2060000.00",
        ],
        [
            "05/11/2025",
            "05/11/2025",
            "Godrej Consumer Products inventory billing",
            "NEFT8819610",
            "180000.00",
            "",
            "1880000.00",
        ],
        [
            "18/11/2025",
            "18/11/2025",
            "GooglePay Business UPI settlement",
            "GPAY8820550",
            "",
            "170000.00",
            "2050000.00",
        ],
        [
            "04/12/2025",
            "04/12/2025",
            "PhonePe QR merchant settlement",
            "PPR99203890",
            "",
            "160000.00",
            "2210000.00",
        ],
        [
            "19/12/2025",
            "19/12/2025",
            "CDM cash deposit - Monthly grocery accounts",
            "CDM002299",
            "",
            "195000.00",
            "2405000.00",
        ],
        [
            "06/01/2026",
            "06/01/2026",
            "Pongal harvest festival grocery sales UPI",
            "UPI99203410",
            "",
            "180000.00",
            "2585000.00",
        ],
        [
            "19/01/2026",
            "19/01/2026",
            "CDM counter cash deposit - Festive collection",
            "CDM002360",
            "",
            "220000.00",
            "2805000.00",
        ],
        [
            "05/02/2026",
            "05/02/2026",
            "Wholesale rice bag procurement - Thanjavur mill",
            "RTGS002810",
            "320000.00",
            "",
            "2485000.00",
        ],
        [
            "16/02/2026",
            "16/02/2026",
            "GooglePay Business UPI settlement",
            "GPAY8820690",
            "",
            "150000.00",
            "2635000.00",
        ],
        [
            "03/03/2026",
            "03/03/2026",
            "PhonePe QR merchant settlement",
            "PPR99204310",
            "",
            "165000.00",
            "2800000.00",
        ],
        [
            "18/03/2026",
            "18/03/2026",
            "CDM cash deposit year-end stock clearance",
            "CDM002440",
            "",
            "185000.00",
            "2985000.00",
        ],
        [
            "28/03/2026",
            "28/03/2026",
            "UPI QR merchant closing settlement",
            "UPI99204190",
            "",
            "85000.00",
            "3070000.00",
        ],
    ]
    return rows


# ==============================================================================
# Scenario 5: Madurai Mess & Catering (Restaurant & Food Services, Madurai)
# FY2025-26: Total Credits = ₹22,00,000.00 (EXACT)
# Food delivery aggregators (Swiggy/Zomato) + wedding catering advances
# ==============================================================================
def generate_madurai_mess_catering() -> list[list[str]]:
    rows = [
        ["Date", "Value Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
        [
            "04/04/2025",
            "04/04/2025",
            "Swiggy weekly restaurant settlement",
            "SWIG001928",
            "",
            "75000.00",
            "75000.00",
        ],
        [
            "11/04/2025",
            "11/04/2025",
            "Zomato dining & delivery settlement",
            "ZOM0019201",
            "",
            "65000.00",
            "140000.00",
        ],
        [
            "20/04/2025",
            "20/04/2025",
            "Counter POS card swipe settlement - PineLabs",
            "POS992019",
            "",
            "85000.00",
            "225000.00",
        ],
        [
            "28/04/2025",
            "28/04/2025",
            "Mandi vegetable purchase cash withdrawal",
            "ATM001928",
            "80000.00",
            "",
            "145000.00",
        ],
        [
            "06/05/2025",
            "06/05/2025",
            "Wedding catering booking advance - Chithirai festival",
            "NEFT059281",
            "",
            "140000.00",
            "285000.00",
        ],
        [
            "16/05/2025",
            "16/05/2025",
            "Swiggy & Zomato combined payout",
            "SWZ9920192",
            "",
            "95000.00",
            "380000.00",
        ],
        [
            "27/05/2025",
            "27/05/2025",
            "Provisions & cooking oil bulk purchase",
            "CHQ601928",
            "120000.00",
            "",
            "260000.00",
        ],
        [
            "05/06/2025",
            "05/06/2025",
            "Counter UPI QR payments aggregate",
            "UPI51829102",
            "",
            "80000.00",
            "340000.00",
        ],
        [
            "22/06/2025",
            "22/06/2025",
            "Corporate lunch catering billing - IT Park",
            "RTGS029102",
            "",
            "120000.00",
            "460000.00",
        ],
        [
            "04/07/2025",
            "04/07/2025",
            "Swiggy delivery weekly settlement",
            "SWIG002140",
            "",
            "65000.00",
            "525000.00",
        ],
        [
            "18/07/2025",
            "18/07/2025",
            "Zomato settlement & counter UPI batch",
            "UPI52194821",
            "",
            "95000.00",
            "620000.00",
        ],
        [
            "28/07/2025",
            "28/07/2025",
            "Commercial LPG cylinders refill subsidy debit",
            "IOCL992018",
            "45000.00",
            "",
            "575000.00",
        ],
        [
            "08/08/2025",
            "08/08/2025",
            "Swiggy & Zomato delivery settlement",
            "SWZ9920311",
            "",
            "85000.00",
            "660000.00",
        ],
        [
            "22/08/2025",
            "22/08/2025",
            "Temple festival Annadhanam catering contract",
            "NEFT059410",
            "",
            "180000.00",
            "840000.00",
        ],
        [
            "05/09/2025",
            "05/09/2025",
            "Counter card & UPI aggregate settlement",
            "POS992144",
            "",
            "95000.00",
            "935000.00",
        ],
        [
            "22/09/2025",
            "22/09/2025",
            "Mess staff wages & cook allowances",
            "NEFT059522",
            "110000.00",
            "",
            "825000.00",
        ],
        [
            "06/10/2025",
            "06/10/2025",
            "Ayudha Pooja special catering advance",
            "IMPS8841920",
            "",
            "120000.00",
            "945000.00",
        ],
        [
            "24/10/2025",
            "24/10/2025",
            "Swiggy Deepavali sweet box orders payout",
            "SWIG002490",
            "",
            "130000.00",
            "1075000.00",
        ],
        [
            "10/11/2025",
            "10/11/2025",
            "Marriage catering contract advance - Kalyana Mandapam",
            "RTGS029580",
            "",
            "200000.00",
            "1275000.00",
        ],
        [
            "26/11/2025",
            "26/11/2025",
            "Meat & poultry suppliers monthly settlement",
            "CHQ601929",
            "140000.00",
            "",
            "1135000.00",
        ],
        [
            "08/12/2025",
            "08/12/2025",
            "Swiggy & Zomato delivery settlement",
            "SWZ9920490",
            "",
            "90000.00",
            "1225000.00",
        ],
        [
            "28/12/2025",
            "28/12/2025",
            "Year-end party catering billing - Madurai Club",
            "NEFT059690",
            "",
            "145000.00",
            "1370000.00",
        ],
        [
            "09/01/2026",
            "09/01/2026",
            "Pongal festive orders UPI QR settlement",
            "UPI53519201",
            "",
            "95000.00",
            "1465000.00",
        ],
        [
            "12/02/2026",
            "12/02/2026",
            "Swiggy & Zomato weekly payout",
            "SWZ9920610",
            "",
            "80000.00",
            "1545000.00",
        ],
        [
            "05/03/2026",
            "05/03/2026",
            "Counter UPI and QR collections",
            "UPI53849102",
            "",
            "70000.00",
            "1615000.00",
        ],
        [
            "20/03/2026",
            "20/03/2026",
            "Final catering balance settlement - Spring wedding",
            "NEFT059810",
            "",
            "90000.00",
            "1705000.00",
        ],
    ]
    return rows


ALL_SCENARIOS = {
    "meenakshi_textiles": (
        "01_meenakshi_textiles_bank_statement.csv",
        generate_meenakshi_textiles,
        "Retail Textile Shop (Madurai) - FY2025-26 - Total Credits: INR 34,00,000.00",
    ),
    "krishna_auto_spares": (
        "02_krishna_auto_spares_bank_statement.csv",
        generate_krishna_auto_spares,
        "Auto Spares Wholesaler (Coimbatore) - FY2025-26 - Total Credits: INR 29,00,000.00",
    ),
    "annamalai_agro_supplies": (
        "03_annamalai_agro_supplies_bank_statement.csv",
        generate_annamalai_agro_supplies,
        "Agro Inputs & Fertilizers (Thanjavur) - FY2025-26 - Total Credits: INR 12,50,000.00",
    ),
    "kirana_supermarket": (
        "04_daily_upi_kirana_bank_statement.csv",
        generate_kirana_supermarket,
        "High-Frequency UPI Kirana / Grocery (Chennai) - FY2025-26 - Total Credits: INR 45,00,000.00",
    ),
    "madurai_mess_catering": (
        "05_madurai_mess_catering_bank_statement.csv",
        generate_madurai_mess_catering,
        "Restaurant & Food Catering (Madurai) - FY2025-26 - Total Credits: INR 22,00,000.00",
    ),
}


def main() -> int:
    print("=" * 70)
    print("  KuralCredit Synthetic Bank Statement Dataset Generator")
    print("=" * 70)

    for key, (filename, generator, description) in ALL_SCENARIOS.items():
        rows = generator()
        total_cr, total_db, final_bal = verify_statement_math(rows)
        print(f"\n[SCENARIO] {key}")
        print(f"  Description:   {description}")
        print(f"  Total Credits: INR {total_cr:,.2f}")
        print(f"  Total Debits:  INR {total_db:,.2f}")
        print(f"  Final Balance: INR {final_bal:,.2f}")

        # Save to both fixtures and datasets directories
        write_csv(BACKEND_FIXTURES / filename, rows)
        write_csv(DATASETS_DIR / filename, rows)

    # Maintain sample_bank_statement.csv for default test fixtures
    sample_rows = generate_meenakshi_textiles()
    write_csv(BACKEND_FIXTURES.parent / "sample_bank_statement.csv", sample_rows)
    write_csv(DATASETS_DIR / "sample_bank_statement.csv", sample_rows)

    print(
        "\n[SUMMARY] All 5 synthetic bank statement CSV datasets successfully generated and mathematically verified."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
