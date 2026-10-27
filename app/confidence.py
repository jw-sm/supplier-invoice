from __future__ import annotations
from .deterministic import DeterministicResult

FIELD_WEIGHTS: dict[str, float] = {
    "invoice_number": 1.0,
    "supplier_name": 1.0,
    "total_due": 1.0,
    "job_reference": 0.5,
    "invoice_date": 0.5,
    "subtotal": 0.5,
    "gst": 0.5,
}
MATERIALS_WEIGHT = 1.0
GST_CONSISTENCY_WEIGHT = 0.5
GST_TOLERANCE = 0.05


def gst_consistent(
    subtotal: float | None, gst: float | None, total: float | None
) -> bool | None:
    if subtotal is None or gst is None or total is None:
        return None
    return abs(round(subtotal + gst, 2) - round(total, 2)) <= GST_TOLERANCE


def score(result: DeterministicResult) -> float:
    inv = result.invoice

    if not result.has_text_layer:
        return 0.0

    earned = 0.0
    possible = 0.0

    for name, weight in FIELD_WEIGHTS.items():
        possible += weight
        if getattr(inv, name) not in (None, ""):
            earned += weight

    possible += MATERIALS_WEIGHT
    if result.table_material_count > 0:
        earned += MATERIALS_WEIGHT

    consistency = gst_consistent(inv.subtotal, inv.gst, inv.total_due)
    if consistency is not None:
        possible += GST_CONSISTENCY_WEIGHT
        if consistency:
            earned += GST_CONSISTENCY_WEIGHT

    return round(earned / possible, 3) if possible else 0.0