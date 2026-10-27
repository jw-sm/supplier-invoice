"""Prove the extraction service reads the sample PDF correctly.
Compares API output against ground truth visible in the PDF.
Run: uv run python scripts/prove_extraction.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.main import app

load_dotenv()

# Ground truth — values printed on sample_electrical_invoice_usd.pdf
EXPECTED = {
    "invoice_number": "NES-2026-10482",
    "invoice_date":   "October 20, 2026",
    "due_date":       "November 19, 2026",
    "supplier_name":  "Northstar Electrical Supply Co.",
    "supplier_abn":   "84-7291056",
    "currency":       "USD",
    "job_reference":  "JOB-2026-174",
    "subtotal":       1609.25,
    "gst":            0.00,
    "total_due":      1609.25,
}

pdf = Path("sample_electrical_invoice_usd.pdf")
with pdf.open("rb") as f:
    r = TestClient(app).post(
        "/extract", files={"file": (pdf.name, f, "application/pdf")}
    )

body = r.json()


def fmt(v):
    return "(none)" if v is None else str(v)


print(f"{'Field':<16} | {'PDF shows':<36} | {'Extracted':<36} | Match")
print("-" * 105)

all_ok = True
for field, expected in EXPECTED.items():
    extracted = body.get(field)
    ok = str(extracted) == str(expected)
    all_ok = all_ok and ok
    print(f"{field:<16} | {fmt(expected):<36} | {fmt(extracted):<36} | {'OK' if ok else 'MISMATCH'}")

# Line-item count
mat_count = len(body.get("materials", []))
expected_mat = 14
mat_ok = mat_count == expected_mat
all_ok = all_ok and mat_ok
print(f"{'materials':<16} | {f'{expected_mat} line items':<36} | {f'{mat_count} line items':<36} | {'OK' if mat_ok else 'MISMATCH'}")

# Show a couple of line items as spot-check
print()
print("Sample line items:")
for item in body["materials"][:3]:
    print(f"  - {item['description']:<45} qty {item['qty']:>5} {item['unit'] or '':<4} @ ${item['unit_price']:.2f}")

print()
print(f"strategy_used : {body['strategy_used']}")
print(f"provider_used : {body['provider_used']}")
print(f"confidence    : {body['confidence']}")
print(f"gst_check     : {'consistent' if not body['gst_check_failed'] else 'FAILED'}")
print()
print("RESULT:", "All fields match the PDF" if all_ok else "MISMATCH — review")