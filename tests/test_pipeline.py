import app.pipeline as pipeline


class FakeExtractor:
    name = "fake"

    def extract(self, text, schema_cls, instructions):
        return schema_cls(invoice_number="LLM-001", total_due=99.0)


class FailingExtractor:
    name = "failing"

    def extract(self, *a, **k):
        raise RuntimeError("rate limited")


def test_falls_back_to_first_provider(monkeypatch):
    monkeypatch.setattr(
        pipeline, "extract_text_and_tables",
        lambda b: ("Invoice\nsome unlabelled text", []),
    )
    monkeypatch.setattr(pipeline, "get_extractors", lambda: [FakeExtractor()])

    result = pipeline.extract_invoice(b"%PDF-fake")
    assert result.strategy_used == "llm_fallback"
    assert result.provider_used == "fake"
    assert result.invoice_number == "LLM-001"


def test_chain_falls_through_on_failure(monkeypatch):
    monkeypatch.setattr(
        pipeline, "extract_text_and_tables",
        lambda b: ("Invoice\nsome unlabelled text", []),
    )
    monkeypatch.setattr(
        pipeline, "get_extractors", lambda: [FailingExtractor(), FakeExtractor()]
    )
    result = pipeline.extract_invoice(b"%PDF-fake")
    assert result.provider_used == "fake"
    assert any("failing failed" in w for w in result.warnings)


def test_does_not_call_llm_when_deterministic_confident(monkeypatch):
    good_text = (
        "ACME SUPPLIES PTY LTD\nABN: 82 614 927 351\n"
        "Invoice No: INV-777\nInvoice Date: 1 August 2026\n"
        "Job Reference: JOB-9\nSub Total: 100.00\nGST: 10.00\nTotal Due: 110.00\n"
    )
    good_table = [
        ["Description", "Qty", "Unit Price", "Amount"],
        ["Widget", "1", "100.00", "100.00"],
    ]
    monkeypatch.setattr(
        pipeline, "extract_text_and_tables", lambda b: (good_text, [good_table])
    )

    def boom():
        raise AssertionError("LLM should not be called on confident path")

    monkeypatch.setattr(pipeline, "get_extractors", boom)

    result = pipeline.extract_invoice(b"%PDF-fake")
    assert result.strategy_used == "deterministic"
    assert result.gst_check_failed is False