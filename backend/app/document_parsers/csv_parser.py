from __future__ import annotations

import csv
import io

from app.core.exceptions import ValidationAppError
from app.document_parsers.base import DocumentParser, ParsedDocument, TableData


def decode_text(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "cp1252"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValidationAppError("The file is not valid UTF-8 or Windows-1252 text")


class CsvParser(DocumentParser):
    name = "csv"
    extensions = frozenset({".csv"})

    def parse(self, content: bytes) -> ParsedDocument:
        text = decode_text(content)
        if "\x00" in text:
            raise ValidationAppError("The CSV file contains binary data")
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        except csv.Error:
            dialect = csv.excel
        reader = csv.reader(io.StringIO(text), dialect)
        rows = list(reader)
        if not rows:
            raise ValidationAppError("The CSV file is empty")
        headers = [header.strip() for header in rows[0]]
        if not any(headers):
            raise ValidationAppError("The CSV file has no header row")
        data_rows: list[dict[str, object]] = []
        row_numbers: list[int] = []
        for line_number, row in enumerate(rows[1:], start=2):
            if not any(str(cell).strip() for cell in row):
                continue
            padded = list(row) + [""] * (len(headers) - len(row))
            data_rows.append(dict(zip(headers, padded, strict=False)))
            row_numbers.append(line_number)
        table = TableData(
            name="csv",
            headers=headers,
            rows=data_rows,
            row_numbers=row_numbers,
        )
        preview = "\n".join(",".join(headers) + " | " + str(row) for row in data_rows[:5])
        return ParsedDocument(
            text=f"CSV headers: {', '.join(headers)}\n{preview}",
            readable=True,
            page_count=None,
            locators=[
                {"type": "row", "index": str(number), "label": f"row {number}"}
                for number in row_numbers
            ],
            tables=[table],
        )
