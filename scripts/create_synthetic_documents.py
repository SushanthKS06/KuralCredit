#!/usr/bin/env python3
"""Synthetic document generator for KuralCredit demo and evaluation.

Creates internally consistent synthetic records:
1. Synthetic Bank Statement (CSV & PDF)
2. Synthetic GST Return Summary GSTR-3B (CSV & PDF)
3. Synthetic Cash Sales Register (CSV & XLSX)
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

FIXTURES_DIR = BACKEND_DIR / "app" / "fixtures" / "synthetic_financial_records"


def generate_bank_statement_csv(output_path: Path) -> None:
    rows = [
        ["Date", "Value Date", "Description", "Ref No", "Debit", "Credit", "Balance"],
        [
            "01/04/2025",
            "01/04/2025",
            "Opening customer receipts NEFT",
            "N09123841",
            "",
            "400000.00",
            "400000.00",
        ],
        [
            "15/05/2025",
            "15/05/2025",
            "Customer receipts RTGS",
            "R01928374",
            "",
            "350000.00",
            "750000.00",
        ],
        [
            "28/05/2025",
            "28/05/2025",
            "Supplier payment yarn",
            "CHQ009121",
            "250000.00",
            "",
            "500000.00",
        ],
        [
            "10/06/2025",
            "10/06/2025",
            "Customer receipts UPI bulk",
            "U99201922",
            "",
            "300000.00",
            "800000.00",
        ],
        [
            "12/07/2025",
            "12/07/2025",
            "Customer receipts NEFT",
            "N09123899",
            "",
            "250000.00",
            "1050000.00",
        ],
        [
            "20/08/2025",
            "20/08/2025",
            "Customer receipts NEFT",
            "N09123910",
            "",
            "200000.00",
            "1250000.00",
        ],
        [
            "18/09/2025",
            "18/09/2025",
            "Customer receipts IMPS",
            "I88273910",
            "",
            "250000.00",
            "1500000.00",
        ],
        [
            "05/10/2025",
            "05/10/2025",
            "Customer receipts RTGS",
            "R01928499",
            "",
            "300000.00",
            "1800000.00",
        ],
        [
            "14/11/2025",
            "14/11/2025",
            "Customer receipts NEFT",
            "N09124012",
            "",
            "250000.00",
            "2050000.00",
        ],
        [
            "09/12/2025",
            "09/12/2025",
            "Customer receipts IMPS",
            "I88274022",
            "",
            "200000.00",
            "2250000.00",
        ],
        [
            "15/12/2025",
            "15/12/2025",
            "Personal transfer from savings",
            "TRF99210",
            "",
            "400000.00",
            "2650000.00",
        ],
        [
            "22/01/2026",
            "22/01/2026",
            "Customer receipts UPI",
            "U99202055",
            "",
            "200000.00",
            "2850000.00",
        ],
        [
            "11/02/2026",
            "11/02/2026",
            "Customer receipts NEFT",
            "N09124190",
            "",
            "150000.00",
            "3000000.00",
        ],
        [
            "20/03/2026",
            "20/03/2026",
            "Customer receipts IMPS",
            "I88274150",
            "",
            "150000.00",
            "3150000.00",
        ],
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [OK] Generated {output_path.name}")


def generate_gst_summary_csv(output_path: Path) -> None:
    rows = [
        [
            "Tax Period",
            "Return Type",
            "Taxable Turnover (INR)",
            "IGST",
            "CGST",
            "SGST",
            "Total Tax",
        ],
        ["Q1 (Apr-Jun 2025)", "GSTR-3B", "450000.00", "0.00", "22500.00", "22500.00", "45000.00"],
        ["Q2 (Jul-Sep 2025)", "GSTR-3B", "400000.00", "0.00", "20000.00", "20000.00", "40000.00"],
        ["Q3 (Oct-Dec 2025)", "GSTR-3B", "450000.00", "0.00", "22500.00", "22500.00", "45000.00"],
        ["Q4 (Jan-Mar 2026)", "GSTR-3B", "350000.00", "0.00", "17500.00", "17500.00", "35000.00"],
        [
            "Total FY2025-26",
            "Annual Summary",
            "1650000.00",
            "0.00",
            "82500.00",
            "82500.00",
            "165000.00",
        ],
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [OK] Generated {output_path.name}")


def generate_cash_sales_register_csv(output_path: Path) -> None:
    rows = [
        ["Date", "Invoice No", "Customer / Description", "Payment Mode", "Amount (INR)"],
        ["05/04/2025", "INV-2025-001", "Counter Cash Sales - Sarees", "Cash", "50000.00"],
        ["12/05/2025", "INV-2025-002", "Counter Cash Sales - Dhotis", "Cash", "75000.00"],
        ["18/06/2025", "INV-2025-003", "Counter Cash Sales - Fabrics", "Cash", "60000.00"],
        ["21/07/2025", "INV-2025-004", "Festival Advance Booking", "Cash", "80000.00"],
        ["09/08/2025", "INV-2025-005", "Counter Cash Sales", "Cash", "65000.00"],
        ["17/09/2025", "INV-2025-006", "Deepavali Early Orders", "Cash", "70000.00"],
        ["23/10/2025", "INV-2025-007", "Festival Season Counter Sales", "Cash", "50000.00"],
        ["11/11/2025", "INV-2025-008", "Wedding Orders Cash", "Cash", "90000.00"],
        ["19/12/2025", "INV-2025-009", "Pongal Collection Booking", "Cash", "60000.00"],
        ["25/01/2026", "INV-2025-010", "Counter Cash Sales", "Cash", "55000.00"],
        ["14/02/2026", "INV-2025-011", "Counter Cash Sales", "Cash", "70000.00"],
        ["18/03/2026", "INV-2025-012", "Year-End Clearance Cash", "Cash", "50000.00"],
        ["Total FY2025-26", "", "Total Cash Sales Register", "", "775000.00"],
    ]
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [OK] Generated {output_path.name}")


def generate_cash_sales_register_xlsx(output_path: Path) -> None:
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Cash Sales FY2025-26"

        headers = ["Date", "Invoice No", "Customer / Description", "Payment Mode", "Amount (INR)"]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")

        data = [
            ["05/04/2025", "INV-2025-001", "Counter Cash Sales - Sarees", "Cash", 50000],
            ["12/05/2025", "INV-2025-002", "Counter Cash Sales - Dhotis", "Cash", 75000],
            ["18/06/2025", "INV-2025-003", "Counter Cash Sales - Fabrics", "Cash", 60000],
            ["21/07/2025", "INV-2025-004", "Festival Advance Booking", "Cash", 80000],
            ["09/08/2025", "INV-2025-005", "Counter Cash Sales", "Cash", 65000],
            ["17/09/2025", "INV-2025-006", "Deepavali Early Orders", "Cash", 70000],
            ["23/10/2025", "INV-2025-007", "Festival Season Counter Sales", "Cash", 50000],
            ["11/11/2025", "INV-2025-008", "Wedding Orders Cash", "Cash", 90000],
            ["19/12/2025", "INV-2025-009", "Pongal Collection Booking", "Cash", 60000],
            ["25/01/2026", "INV-2025-010", "Counter Cash Sales", "Cash", 55000],
            ["14/02/2026", "INV-2025-011", "Counter Cash Sales", "Cash", 70000],
            ["18/03/2026", "INV-2025-012", "Year-End Clearance Cash", "Cash", 50000],
            ["Total", "FY2025-26", "Total Cash Sales Register", "", 775000],
        ]
        for row in data:
            ws.append(row)

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = max(max_len + 3, 12)

        wb.save(output_path)
        print(f"  [OK] Generated {output_path.name}")
    except Exception as exc:
        print(f"  [WARN] Failed to generate XLSX: {exc}")


def generate_bank_statement_pdf(output_path: Path) -> None:
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36,
        )
        styles = getSampleStyleSheet()
        elements = []

        title_style = ParagraphStyle(
            "BankTitle",
            parent=styles["Heading1"],
            fontSize=16,
            textColor=colors.HexColor("#0f172a"),
            spaceAfter=6,
        )
        elements.append(
            Paragraph("Canara Bank - Current Account Statement (Synthetic Demo)", title_style)
        )
        elements.append(
            Paragraph(
                "Account Name: Meenakshi Textiles | Account No: 1092XXXXXX89 | Period: 01/04/2025 to 31/03/2026",
                styles["Normal"],
            )
        )
        elements.append(
            Paragraph("Branch: Madurai West | IFSC: CNRB0001092 | Currency: INR", styles["Normal"])
        )
        elements.append(Spacer(1, 12))

        table_data = [
            ["Date", "Description", "Ref No", "Debit (INR)", "Credit (INR)", "Balance (INR)"],
            [
                "01/04/2025",
                "Opening customer receipts",
                "N09123841",
                "-",
                "4,00,000.00",
                "4,00,000.00",
            ],
            [
                "15/05/2025",
                "Customer receipts RTGS",
                "R01928374",
                "-",
                "3,50,000.00",
                "7,50,000.00",
            ],
            ["28/05/2025", "Supplier payment yarn", "CHQ009121", "2,50,000.00", "-", "5,00,000.00"],
            ["10/06/2025", "Customer receipts UPI", "U99201922", "-", "3,00,000.00", "8,00,000.00"],
            [
                "12/07/2025",
                "Customer receipts NEFT",
                "N09123899",
                "-",
                "2,50,000.00",
                "10,50,000.00",
            ],
            [
                "20/08/2025",
                "Customer receipts NEFT",
                "N09123910",
                "-",
                "2,00,000.00",
                "12,50,000.00",
            ],
            [
                "18/09/2025",
                "Customer receipts IMPS",
                "I88273910",
                "-",
                "2,50,000.00",
                "15,00,000.00",
            ],
            [
                "05/10/2025",
                "Customer receipts RTGS",
                "R01928499",
                "-",
                "3,00,000.00",
                "18,00,000.00",
            ],
            [
                "14/11/2025",
                "Customer receipts NEFT",
                "N09124012",
                "-",
                "2,50,000.00",
                "20,50,000.00",
            ],
            [
                "09/12/2025",
                "Customer receipts IMPS",
                "I88274022",
                "-",
                "2,00,000.00",
                "22,50,000.00",
            ],
            [
                "15/12/2025",
                "Personal transfer savings",
                "TRF99210",
                "-",
                "4,00,000.00",
                "26,50,000.00",
            ],
            [
                "22/01/2026",
                "Customer receipts UPI",
                "U99202055",
                "-",
                "2,00,000.00",
                "28,50,000.00",
            ],
            [
                "11/02/2026",
                "Customer receipts NEFT",
                "N09124190",
                "-",
                "1,50,000.00",
                "30,00,000.00",
            ],
            [
                "20/03/2026",
                "Customer receipts IMPS",
                "I88274150",
                "-",
                "1,50,000.00",
                "31,50,000.00",
            ],
            [
                "Total",
                "Annual Credits FY25-26",
                "14 txns",
                "2,50,000.00",
                "34,00,000.00",
                "31,50,000.00",
            ],
        ]

        t = Table(table_data, colWidths=[65, 145, 75, 75, 80, 85])
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("ALIGN", (3, 1), (-1, -1), "RIGHT"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f1f5f9")),
                    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )
        elements.append(t)
        doc.build(elements)
        print(f"  [OK] Generated {output_path.name}")
    except Exception as exc:
        print(f"  [WARN] Failed to generate Bank PDF: {exc}")


def main() -> None:
    print("=" * 60)
    print("  Generating Synthetic Financial Records")
    print("=" * 60)
    FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    generate_bank_statement_csv(FIXTURES_DIR / "sample_bank_statement.csv")
    generate_gst_summary_csv(FIXTURES_DIR / "sample_gst_summary.csv")
    generate_cash_sales_register_csv(FIXTURES_DIR / "sample_cash_sales_register.csv")
    generate_cash_sales_register_xlsx(FIXTURES_DIR / "sample_cash_sales_register.xlsx")
    generate_bank_statement_pdf(FIXTURES_DIR / "sample_bank_statement.pdf")

    print("\n[OK] All synthetic documents successfully generated.")


if __name__ == "__main__":
    main()
