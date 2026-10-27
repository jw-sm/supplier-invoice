from __future__ import annotations
from typing import Literal, Optional
from pydantic import BaseModel, Field


class Material(BaseModel):
    description: str
    qty: Optional[float] = None
    unit: Optional[str] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class InvoiceData(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    due_date: Optional[str] = None
    currency: Optional[str] = "AUD"
    supplier_name: Optional[str] = None
    supplier_abn: Optional[str] = None
    bill_to_name: Optional[str] = None
    job_number: Optional[str] = None
    project: Optional[str] = None
    subtotal: Optional[float] = None
    gst: Optional[float] = None
    total_due: Optional[float] = None
    materials: list[Material] = Field(default_factory=list)


class ExtractionResponse(InvoiceData):
    strategy_used: Literal["deterministic", "llm_fallback"]
    confidence: float = Field(ge=0.0, le=1.0)
    gst_check_failed: bool = False
    warnings: list[str] = Field(default_factory=list)
    provider_used: Optional[str] = None