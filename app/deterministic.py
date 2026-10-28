from __future__ import annotations
import re
from dataclasses import dataclass, field

from .schemas import InvoiceData, Material
from .pdf import Table


def _money(s: str | None) -> float | None:
    if s is None or s == "":
        return None
    try:
        return round(float(s.replace(",", "").replace("$", "").strip()), 2)
    except ValueError:
        return None


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# --- strict ID pattern: PREFIX-NUMBER[-NUMBER...] (handles concatenated text) ---
_ID = r"([A-Z]{2,5}[-\/]\d{2,}(?:[-\/][A-Z0-9]+)*)"


RE_INVOICE_NO = re.compile(
    r"(?:invoice|inv)\s*(?:no\.?|number|#)\s*[:\-]?\s*" + _ID,
    re.I,
)

_DATE = (
    r"("
    r"\d{1,2}\s+[A-Za-z]{3,9},?\s+\d{4}"  # 28 Oct 2026, 28 October 2026
    r"|[A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4}"  # Oct 28 2026, October 28, 2026
    r"|\d{4}-\d{2}-\d{2}"                  # 2026-10-28 (YYYY-MM-DD)
    r"|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}" # 28/10/2026, 10/28/2026, 28-10-26
    r")"
)

#INVNO.
RE_INVOICE_DATE = re.compile(
    r"(?:invoice\s*date|date\s*of\s*invoice|dated)\s*[:\-]?\s*" + _DATE, re.I
)

RE_DUE_DATE = re.compile(r"(?:due\s*date|payment\s*due)\s*[:\-]?\s*" + _DATE, re.I)

RE_ABN = re.compile(
    r"\b(?:ABN|Tax\s*ID|EIN)\s*[:\-]?\s*"
    r"(\d{2}\s?\d{3}\s?\d{3}\s?\d{3}|\d{2}\s*-\s*\d{7}|\d{9,11})",
    re.I,
)

RE_CURRENCY = re.compile(r"\bcurrency\s*[:\-]?\s*([A-Z]{3})\b", re.I)

_JOB_REF_PATTERNS = [
    re.compile(r"job\s*ref(?:erence)?\s*[:\-]?\s*" + _ID, re.I),
    re.compile(r"job\s*(?:no\.?|number)\s*[:\-]?\s*" + _ID, re.I),
    re.compile(r"project\s*(?:no\.?|ref(?:erence)?)\s*[:\-]?\s*" + _ID, re.I),
    re.compile(r"purchase\s*order\s*[:\-]?\s*" + _ID, re.I),
    re.compile(r"po\s*(?:no\.?|number|#)\s*[:\-]?\s*" + _ID, re.I),
]

RE_SUBTOTAL = re.compile(
    r"(?:sub\s*-?\s*total|total\s*ex(?:cl)?\.?\s*(?:gst)?|net\s*total)"
    r"\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",
    re.I,
)

RE_GST = re.compile(
    r"(?:gst\s*\/\s*sales\s*tax|sales\s*tax|gst|goods\s*and\s*services\s*tax|vat)"
    r"[^0-9\n]*?\$?\s*([\d,]+\.\d{2})",
    re.I,
)

# Phrase-based total amount detection.
# Intentionally does NOT match a bare "Total" to avoid false matches
# such as "Sub Total".

RE_TOTAL = re.compile(
    r"(?:"
    r"total\s*(?:due|amount|payable|inc\.?\s*gst|incl\.?\s*gst)"  # Total Due, Total Amount, Total Payable, Total Inc GST, Total Incl. GST
    r"|balance\s*due"                                           # Balance Due
    r"|amount\s*due"                                            # Amount Due
    r")\s*[:\-]?\s*\$?\s*([\d,]+\.\d{2})",                     # Optional colon/hyphen, optional $, then amount (e.g. $1,250.00)
    re.I,                                                        # Case-insensitive matching
)

RE_COMPANY_SUFFIX = re.compile(r"\b(pty|ltd|limited|inc|llc|& co|co)\b", re.I)

# Table header aliases — CRITICAL: unit_price BEFORE unit
HEADER_ALIASES: dict[str, set[str]] = {
    "description": {"description", "desc", "item", "items", "details", "particulars", "product", "service"},
    "qty": {"qty", "quantity", "units", "hours"},
    "unit_price": {"unit price", "price", "rate", "unit cost"},
    "amount": {"amount", "line total", "extended", "value"},
    "unit": {"unit", "uom", "unit of measure", "measure"},
}

SKIP_ROW = re.compile(
    r"^(sub\s*-?\s*total|gst|tax|total|freight|delivery|less\s*deposit"
    r"|balance|amount\s*paid)",
    re.I,
)


def _header_map(row: list[str | None]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for idx, cell in enumerate(row):
        if not cell:
            continue
        c = _norm(cell)
        for key, aliases in HEADER_ALIASES.items():
            if key in mapping:
                continue
            if c in aliases or any(a in c for a in aliases):
                mapping[key] = idx
    return mapping


def _parse_table_rows(tables: list[Table]) -> list[Material]:
    materials: list[Material] = []

    for table in tables:
        header_idx = None
        header: dict[str, int] = {}

        for i, row in enumerate(table[:4]):
            m = _header_map(row)
            if "description" in m and ("amount" in m or "qty" in m):
                header_idx, header = i, m
                break

        if header_idx is None:
            continue

        for row in table[header_idx + 1:]:
            if not row or not any(row):
                continue
            desc = row[header["description"]] if header["description"] < len(row) else None
            if not desc or SKIP_ROW.match(_norm(desc)):
                continue

            def cell(key: str) -> str | None:
                i = header.get(key)
                return row[i] if i is not None and i < len(row) else None

            qty = _money(cell("qty"))
            unit_price = _money(cell("unit_price"))
            amount = _money(cell("amount"))
            if amount is None and qty is not None and unit_price is not None:
                amount = round(qty * unit_price, 2)

            materials.append(
                Material(
                    description=desc.strip(),
                    qty=qty,
                    unit=(cell("unit") or "").strip() or None,
                    unit_price=unit_price,
                    amount=amount,
                )
            )

    return materials


def _guess_supplier(lines: list[str]) -> str | None:
    """Deliberately conservative: return None rather than a bad guess."""
    for line in lines[:10]:
        if RE_COMPANY_SUFFIX.search(line) and len(line) < 80:
            if not re.match(r"^\d", line.strip()):
                return line.strip()
    return None


def _find_job_ref(text: str) -> str | None:
    for pattern in _JOB_REF_PATTERNS:
        if m := pattern.search(text):
            return m.group(1).strip()
    return None


@dataclass
class DeterministicResult:
    invoice: InvoiceData
    has_text_layer: bool
    table_material_count: int
    signals: dict = field(default_factory=dict)


def parse_invoice(text: str, tables: list[Table] | None = None) -> DeterministicResult:
    tables = tables or []
    lines = [ln for ln in text.splitlines() if ln.strip()]

    data = InvoiceData()

    if m := RE_INVOICE_NO.search(text):
        data.invoice_number = m.group(1).strip()
    if m := RE_INVOICE_DATE.search(text):
        data.invoice_date = m.group(1).strip()
    if m := RE_DUE_DATE.search(text):
        data.due_date = m.group(1).strip()
    if m := RE_ABN.search(text):
        data.supplier_abn = m.group(1).strip()
    if m := RE_CURRENCY.search(text):
        data.currency = m.group(1).upper()

    data.job_reference = _find_job_ref(text)
    data.supplier_name = _guess_supplier(lines)

    if m := RE_SUBTOTAL.search(text):
        data.subtotal = _money(m.group(1))
    if m := RE_GST.search(text):
        data.gst = _money(m.group(1))
    if m := RE_TOTAL.search(text):
        data.total_due = _money(m.group(1))

    data.materials = _parse_table_rows(tables)

    return DeterministicResult(
        invoice=data,
        has_text_layer=bool(text.strip()),
        table_material_count=len(data.materials),
    )