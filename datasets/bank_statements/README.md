# KuralCredit — Synthetic Bank Statement CSV Datasets

This directory contains **5 realistic, mathematically verified synthetic bank statement CSV datasets** designed for Indian MSME loan application clarification and evidence preparation.

Every dataset strictly satisfies the fundamental double-entry banking relation for each row:
$$\text{Balance}_i = \text{Balance}_{i-1} + \text{Credit}_i - \text{Debit}_i$$

---

## 1. Dataset Index & MSME Profiles

| File | Business Profile | Location | Annual Bank Credits | Declared Turnover | Primary Variance Explanation |
|---|---|---|---|---|---|
| **[`01_meenakshi_textiles_bank_statement.csv`](./01_meenakshi_textiles_bank_statement.csv)** | Retail Handloom & Silk Textiles | Madurai, TN | **₹34,00,000.00** | ₹18,00,000.00 | ₹4,00,000 personal transfer from owner's savings account; remainder accounted for by physical cash counter sales register. |
| **[`02_krishna_auto_spares_bank_statement.csv`](./02_krishna_auto_spares_bank_statement.csv)** | Auto Spares & Commercial Fleet Maintenance | Coimbatore, TN | **₹29,00,000.00** | ₹25,00,000.00 | ₹5,00,000 NBFC equipment loan disbursement credited in Q2 (Cholamandalam Finance). |
| **[`03_annamalai_agro_supplies_bank_statement.csv`](./03_annamalai_agro_supplies_bank_statement.csv)** | Seeds, Fertilizers & Agro Inputs | Thanjavur, TN | **₹12,50,000.00** | ₹12,00,000.00 | ₹50,000 month-end customer cheque float in transit (cleared on 02/04/2026). Seasonal Kharif/Rabi peaks. |
| **[`04_daily_upi_kirana_bank_statement.csv`](./04_daily_upi_kirana_bank_statement.csv)** | High-Frequency Daily UPI Grocery / Kirana | Chennai, TN | **₹45,00,000.00** | ₹42,00,000.00 | Daily PhonePe, GPay, Paytm Soundbox batch payouts + regular Cash Deposit Machine (CDM) counter deposits. |
| **[`05_madurai_mess_catering_bank_statement.csv`](./05_madurai_mess_catering_bank_statement.csv)** | Restaurant & Event Catering Services | Madurai, TN | **₹22,00,000.00** | ₹20,00,000.00 | Swiggy/Zomato weekly payouts, marriage catering advance contracts, cash vegetable market withdrawals. |

---

## 2. Standard CSV Schema

Each dataset contains standard commercial current account headers recognized out-of-the-box by KuralCredit's deterministic parser (`app/document_parsers/table_extractor.py`):

| Column | Type | Format / Example | Description |
|---|---|---|---|
| `Date` | Date | `DD/MM/YYYY` (`01/04/2025`) | Transaction booking date |
| `Value Date` | Date | `DD/MM/YYYY` (`01/04/2025`) | Interest / value clearing date |
| `Description` | String | `Customer receipts NEFT - Sri Ram Silks` | Bank narration including payment mode, sender, or purpose |
| `Ref No` | String | `N09123841`, `UPI51049921` | Bank UTR, NEFT ref, cheque no, or UPI reference |
| `Debit` | Decimal | `25000.00` (or blank) | Withdrawal or outgoing vendor payment amount in INR |
| `Credit` | Decimal | `200000.00` (or blank) | Inflow / incoming deposit amount in INR |
| `Balance` | Decimal | `2105000.00` | Account balance immediately after transaction |

---

## 3. Product Principles Applied

In accordance with KuralCredit's hard architectural boundaries:
1. **Bank credits $\neq$ Business revenue**: A bank statement credit may represent non-revenue cash flow (capital injection, personal transfers, loans, tax refunds).
2. **Transparent comparison**: The system uses deterministic rule reconciliation to compute:
   $$\Delta = \text{Bank Credits} - \text{Declared Sales}$$
   and prompts the applicant for neutral clarification rather than scoring or flagging adverse indicators.
3. **Traceable provenance**: Every row is tracked with a deterministic row locator (e.g. `rows 2-29`) preserved in the reviewer evidence packet.

---

## 4. How to Use

### Via KuralCredit Web UI
1. Navigate to your application dashboard at `http://localhost:5173/apply/<application_id>/documents`.
2. Select document type: **"Bank statement"**.
3. Choose any CSV from this folder (e.g. `01_meenakshi_textiles_bank_statement.csv`).
4. Click **Upload** — the parser will automatically extract the aggregate bank credit total and date range!

### Via Command-Line Re-Generation
To re-generate or verify all synthetic statements:
```powershell
python scripts/generate_synthetic_bank_statements.py
```

