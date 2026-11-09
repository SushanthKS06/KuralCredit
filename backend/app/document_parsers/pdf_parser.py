from __future__ import annotations

from io import BytesIO

from pypdf import PdfReader

from app.core.exceptions import ValidationAppError
from app.document_parsers.base import DocumentParser, ParsedDocument


class PdfParser(DocumentParser):
    name = "pdf"
    extensions = frozenset({".pdf"})

    def parse(self, content: bytes) -> ParsedDocument:
        try:
            reader = PdfReader(BytesIO(content))
        except Exception as exc:
            raise ValidationAppError("The PDF could not be opened") from exc
        pages: list[str] = []
        locators: list[dict[str, str]] = []
        for index, page in enumerate(reader.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            pages.append(text)
            locators.append({"type": "page", "index": str(index), "label": f"page {index}"})
        combined = "\n\n".join(
            f"[page {index}]\n{text}" for index, text in enumerate(pages, start=1) if text.strip()
        )
        readable = bool(combined.strip())
        notes = (
            []
            if readable
            else [
                "No selectable text was found. Scanned-only PDFs require OCR, which is not enabled."
            ]
        )
        return ParsedDocument(
            text=combined,
            readable=readable,
            page_count=len(reader.pages),
            locators=locators,
            notes=notes,
        )
