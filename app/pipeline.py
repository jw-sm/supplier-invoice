from __future__ import annotations
import os
from .schemas import ExtractionResponse
from .pdf import extract_text_and_tables
from .deterministic import parse_invoice
from .confidence import score, gst_consistent
from .extractors import get_extractors

DEFAULT_THRESHOLD = 0.75
MAX_TEXT_CHARS = 30_000

LLM_INSTRUCTIONS = (
    "You are extracting fields from a supplier invoice for a commercial "
    "electrical contractor. Extract only what is explicitly written. Do not "
    "calculate, infer, correct, or reformat monetary values. If a field is "
    "absent, return null. Include every line item in materials, in order."
)


def _threshold() -> float:
    try:
        return float(os.getenv("CONFIDENCE_THRESHOLD", DEFAULT_THRESHOLD))
    except ValueError:
        return DEFAULT_THRESHOLD


def _gst_flag(invoice) -> bool:
    consistent = gst_consistent(invoice.subtotal, invoice.gst, invoice.total_due)
    return consistent is False


def extract_invoice(pdf_bytes: bytes) -> ExtractionResponse:
    text, tables = extract_text_and_tables(pdf_bytes)
    det = parse_invoice(text, tables)
    confidence = score(det)
    threshold = _threshold()
    warnings: list[str] = []

    # Deterministic path wins when confident
    if confidence >= threshold:
        return ExtractionResponse(
            **det.invoice.model_dump(),
            strategy_used="deterministic",
            confidence=confidence,
            gst_check_failed=_gst_flag(det.invoice),
            warnings=warnings,
        )

    # No text layer: a text-only LLM can't help either
    if not det.has_text_layer:
        warnings.append(
            "No text layer detected — PDF is likely a scanned image. "
            "OCR or a vision pass is required."
        )
        return ExtractionResponse(
            **det.invoice.model_dump(),
            strategy_used="deterministic",
            confidence=0.0,
            gst_check_failed=_gst_flag(det.invoice),
            warnings=warnings,
        )

    # Low confidence on a text PDF: walk the provider chain
    chain = get_extractors()
    if not chain:
        warnings.append(
            f"Deterministic confidence {confidence} below threshold {threshold}, "
            "and no LLM provider is configured (check GEMINI_API_KEY / ANTHROPIC_API_KEY)."
        )
        return ExtractionResponse(
            **det.invoice.model_dump(),
            strategy_used="llm_fallback",
            confidence=confidence,
            gst_check_failed=_gst_flag(det.invoice),
            warnings=warnings,
        )

    warnings.append(
        f"Deterministic confidence {confidence} below threshold {threshold}; "
        f"trying fallback chain: {', '.join(e.name for e in chain)}."
    )

    for extractor in chain:
        try:
            llm_data = extractor.extract(
                text[:MAX_TEXT_CHARS], type(det.invoice), LLM_INSTRUCTIONS
            )
            warnings.append(f"{extractor.name} extraction succeeded.")
            return ExtractionResponse(
                **llm_data.model_dump(),
                strategy_used="llm_fallback",
                confidence=max(confidence, threshold),
                gst_check_failed=_gst_flag(llm_data),
                warnings=warnings,
                provider_used=extractor.name,
            )
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"{extractor.name} failed: {exc}")

    warnings.append("All LLM providers in the fallback chain failed.")
    return ExtractionResponse(
        **det.invoice.model_dump(),
        strategy_used="llm_fallback",
        confidence=confidence,
        gst_check_failed=_gst_flag(det.invoice),
        warnings=warnings,
    )