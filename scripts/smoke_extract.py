"""End-to-end smoke test: POST the sample PDF to /extract via TestClient."""
from pathlib import Path

from dotenv import load_dotenv
from fastapi.testclient import TestClient

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.main import app

load_dotenv()

pdf = Path("sample_electrical_invoice_usd.pdf")
with pdf.open("rb") as f:
    r = TestClient(app).post(
        "/extract", files={"file": (pdf.name, f, "application/pdf")}
    )

print("status:", r.status_code)
body = r.json()
print("strategy_used :", body["strategy_used"])
print("provider_used :", body["provider_used"])
print("confidence    :", body["confidence"])
print("supplier_name :", body["supplier_name"])
print("job_reference :", body["job_reference"])
print("total_due     :", body["total_due"])
print("materials     :", len(body["materials"]))
print("warnings      :", body["warnings"])