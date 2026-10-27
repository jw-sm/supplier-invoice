from app.deterministic import parse_invoice
from app.confidence import score, gst_consistent


# Mirrors the real pdfplumber output for sample_electrical_invoice_usd.pdf
SAMPLE_TEXT = """\
INVOICE
Northstar Electrical Supply Co.
1250 Industrial Parkway, Houston, TX 77029, USA
Phone: (713) 555-0148 | Email: billing@northstarelectrical.example
Tax ID: 84-7291056
Invoice Number: NES-2026-10482 Bill To
Invoice Date: October 20, 2026 Apex Electrical Contractors LLC
Due Date: November 19, 2026 4500 Commerce Drive, Dallas, TX 75207, USA
Purchase Order: PO-8117 Customer ID: AEC-00421
Quote Reference: QT-2026-0881
Currency: USD
Job: Commercial Panel Upgrade — Building B
Job Reference: JOB-2026-174
Subtotal $1,609.25
GST / Sales Tax $0.00
Total Due $1,609.25
"""

SAMPLE_TABLE = [
    ["SKU", "Description", "Qty", "Unit", "Unit Price", "Line Total"],
    ["WIR-THIN-12", "12 AWG THHN Copper Wire, Black", "500", "ft", "$0.32", "$160.00"],
    ["WIR-THIN-10", "10 AWG THHN Copper Wire, Red", "300", "ft", "$0.58", "$174.00"],
    ["CON-EMT-34", "3/4-inch EMT Conduit, 10 ft", "40", "ea", "$8.75", "$350.00"],
    ["FIT-EMT-34C", "3/4-inch EMT Compression Connector", "50", "ea", "$1.20", "$60.00"],
    ["FIT-EMT-34S", "3/4-inch EMT Set-Screw Coupling", "40", "ea", "$0.95", "$38.00"],
    ["BOX-4SQ", "4-inch Square Electrical Box", "25", "ea", "$3.40", "$85.00"],
    ["BRK-20A-1P", "20A Single-Pole Circuit Breaker", "12", "ea", "$18.50", "$222.00"],
    ["BRK-30A-2P", "30A Double-Pole Circuit Breaker", "6", "ea", "$42.00", "$252.00"],
    ["REC-20A-DP", "20A Duplex Receptacle", "20", "ea", "$4.25", "$85.00"],
    ["SW-15A-SG", "15A Single-Gang Light Switch", "15", "ea", "$3.10", "$46.50"],
    ["PLT-1G-WH", "Single-Gang Wall Plate, White", "15", "ea", "$0.85", "$12.75"],
    ["GRD-10AWG", "10 AWG Grounding Wire", "100", "ft", "$0.44", "$44.00"],
    ["LAB-CUT", "Conduit Cutting and Preparation Charge", "1", "lot", "$45.00", "$45.00"],
    ["DEL-STD", "Standard Delivery Charge", "1", "lot", "$35.00", "$35.00"],
]


def test_header_fields():
    inv = parse_invoice(SAMPLE_TEXT, [SAMPLE_TABLE]).invoice
    assert inv.invoice_number == "NES-2026-10482"
    assert inv.invoice_date == "October 20, 2026"
    assert inv.due_date == "November 19, 2026"
    assert inv.supplier_abn == "84-7291056"
    assert inv.currency == "USD"
    assert inv.job_reference == "JOB-2026-174"     # NOT PO-8117


def test_totals():
    inv = parse_invoice(SAMPLE_TEXT, [SAMPLE_TABLE]).invoice
    assert inv.subtotal == 1609.25
    assert inv.gst == 0.00
    assert inv.total_due == 1609.25


def test_supplier_name_extracted_from_header():
    inv = parse_invoice(SAMPLE_TEXT, [SAMPLE_TABLE]).invoice
    assert inv.supplier_name == "Northstar Electrical Supply Co."


def test_line_items_parsed():
    result = parse_invoice(SAMPLE_TEXT, [SAMPLE_TABLE])
    assert result.table_material_count == 14
    first = result.invoice.materials[0]
    assert first.description == "12 AWG THHN Copper Wire, Black"
    assert first.qty == 500.0
    assert first.unit == "ft"
    assert first.unit_price == 0.32
    assert first.amount == 160.00


def test_gst_consistent():
    assert gst_consistent(12573.00, 1257.30, 13830.30) is True
    assert gst_consistent(1609.25, 0.00, 1609.25) is True
    assert gst_consistent(12573.00, 1257.30, 14000.00) is False
    assert gst_consistent(None, None, None) is None


def test_confidence_above_threshold():
    result = parse_invoice(SAMPLE_TEXT, [SAMPLE_TABLE])
    assert score(result) >= 0.80