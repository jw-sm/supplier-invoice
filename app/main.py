from __future__ import annotations
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from .schemas import ExtractionResponse
from .pipeline import extract_invoice

app = FastAPI(title="Supplier Invoice Extractor", version="1.0.0")

MAX_UPLOAD_BYTES = 15 * 1024 * 1024


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/extract", response_model=ExtractionResponse)
async def extract(file: UploadFile = File(...)) -> ExtractionResponse:
    if file.content_type not in {"application/pdf", "application/octet-stream"}:
        raise HTTPException(status_code=415, detail="Expected a PDF upload.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")
    if len(pdf_bytes) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large.")

    try:
        return extract_invoice(pdf_bytes)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=500, content={"detail": f"Extraction failed: {exc}"}
        )