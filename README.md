# Supplier Invoice Extractor

A bounded tool that turns supplier invoice PDFs into validated JSON. Deterministic-first; LLM only as a fallback, with a configurable provider chain.

## Why

Financial figures should not be guessed by a language model. Most supplier invoices have stable, label-anchored layouts, so a table/regex extractor is cheaper, faster and testable. The LLM exists for the cases that genuinely need judgement — irregular layouts, unusual wording, missing structure.

## Architecture

    POST /extract
      -> pdfplumber (text + tables; borderless-table fallback)
      -> deterministic extractor (regex anchors, table column mapping)
      -> confidence score (field coverage, line items, subtotal+gst=total)
      -> if score >= threshold: return strategy_used="deterministic"
      -> else: walk LLM fallback chain (Gemini -> Claude by default)
      -> return strategy_used="llm_fallback" + provider_used

**Fallback chain.** When the deterministic parser falls below the confidence threshold, the pipeline tries LLM providers in `LLM_FALLBACK_ORDER` (default `gemini,claude`). Providers without an API key are skipped. If one errors, the next is tried; if all fail, the deterministic result is returned with warnings. `provider_used` in the response names whichever provider ran. The Claude adapter ships in the repo and activates the moment `ANTHROPIC_API_KEY` is set — no code change.

## Run

    uv sync
    cp .env.example .env       # fill in GEMINI_API_KEY at minimum
    uv run uvicorn app.main:app --reload --port 8000

    curl -X POST http://localhost:8000/extract -F "file=@invoice.pdf" | python -m json.tool

## Test

    uv run pytest -q

## Known limitation

Scanned PDFs with no text layer cannot be handled by a text-only LLM call. The API returns `confidence: 0.0` with an explicit warning. A vision pass is the natural next step.