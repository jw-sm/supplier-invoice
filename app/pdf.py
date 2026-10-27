from __future__ import annotations
import io
import pdfplumber

Table = list[list[str | None]]


def extract_text_and_tables(pdf_bytes: bytes) -> tuple[str, list[Table]]:
    """Return (concatenated text, list of tables across all pages).

    An empty text string means the PDF has no text layer (likely a scan).
    """
    texts: list[str] = []
    tables: list[Table] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            page_tables = page.extract_tables() or []
            if not page_tables:
                # Borderless-table fallback (common on supplier invoices)
                page_tables = page.extract_tables(
                    {
                        "vertical_strategy": "text",
                        "horizontal_strategy": "text",
                        "intersection_tolerance": 3,
                    }
                ) or []
            for table in page_tables:
                tables.append(table)

    return "\n".join(t for t in texts if t).strip(), tables