from __future__ import annotations

from app.core.exceptions import ValidationAppError
from app.document_parsers.base import DocumentParser
from app.document_parsers.csv_parser import CsvParser
from app.document_parsers.pdf_parser import PdfParser
from app.document_parsers.xlsx_parser import XlsxParser

PARSERS: dict[str, DocumentParser] = {
    ".pdf": PdfParser(),
    ".csv": CsvParser(),
    ".xlsx": XlsxParser(),
}


def get_parser(extension: str) -> DocumentParser:
    parser = PARSERS.get(extension.lower())
    if parser is None:
        raise ValidationAppError(f"No parser is available for '{extension}' files")
    return parser


def supported_extensions() -> list[str]:
    return sorted(PARSERS.keys())
