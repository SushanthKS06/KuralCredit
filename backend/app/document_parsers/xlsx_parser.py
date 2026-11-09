from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from app.core.exceptions import ValidationAppError
from app.document_parsers.base import DocumentParser, ParsedDocument, TableData


class XlsxParser(DocumentParser):
    name = "xlsx"
    extensions = frozenset({".xlsx"})

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
        except Exception as exc:
            raise ValidationAppError("The XLSX file could not be opened") from exc
        tables: list[TableData] = []
        notes: list[str] = []
        text_parts: list[str] = []
        locators: list[dict[str, str]] = []
        for sheet in workbook.worksheets:
            values = list(sheet.iter_rows(values_only=True))
            if not values:
                notes.append(f"Sheet '{sheet.title}' is empty")
                continue
            headers = [str(cell).strip() if cell is not None else "" for cell in values[0]]
            rows: list[dict[str, object]] = []
            row_numbers: list[int] = []
            for row_index, row in enumerate(values[1:], start=2):
                if not any(cell is not None and str(cell).strip() for cell in row):
                    continue
                padded = list(row) + [None] * (len(headers) - len(row))
                rows.append(dict(zip(headers, padded, strict=False)))
                row_numbers.append(row_index)
            tables.append(
                TableData(
                    name=sheet.title,
                    headers=headers,
                    rows=rows,
                    row_numbers=row_numbers,
                    sheet=sheet.title,
                )
            )
            text_parts.append(f"Sheet {sheet.title}: headers {', '.join(headers)}")
            for number in row_numbers[:3]:
                locators.append(
                    {
                        "type": "row",
                        "index": str(number),
                        "label": f"sheet {sheet.title} row {number}",
                    }
                )
        workbook.close()
        return ParsedDocument(
            text="\n".join(text_parts),
            readable=bool(tables),
            page_count=len(tables),
            locators=locators,
            tables=tables,
            notes=notes,
        )
