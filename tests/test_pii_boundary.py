"""PII boundary contract: untrusted free text must be clean of structured PII.

Two jobs: (1) prove the scanner actually detects PII (teeth -- a scan that never
fires is worthless), and (2) assert the synthetic seed customer queries carry no
real contact/financial PII. The scanner here is the same component the Phase 2.3
safety gate runs on live customer input, so its behaviour is contract-tested now.
"""

from pathlib import Path

import pandas as pd
import pytest
from presidio_analyzer import AnalyzerEngine

from tsa.data.pii import BOUNDARY_PII_ENTITIES, build_analyzer, find_pii, scan_for_pii

SEED_DIR = Path(__file__).resolve().parents[1] / "data" / "seed"
SEED_TEXT_FILES = ("router.csv", "retrieval_grounding.csv")


@pytest.fixture(scope="session")
def analyzer() -> AnalyzerEngine:
    """Build the Presidio analyzer once for the whole test session (model load is slow)."""
    return build_analyzer()


def _seed_customer_queries() -> list[str]:
    texts: list[str] = []
    for name in SEED_TEXT_FILES:
        frame = pd.read_csv(SEED_DIR / name, dtype=str).fillna("")
        texts.extend(frame["customer_query"].tolist())
    return texts


def test_scanner_detects_planted_pii(analyzer: AnalyzerEngine) -> None:
    """Teeth: planted email + card must be flagged, or the boundary scan means nothing."""
    text = "Email me at john.doe@example.com -- my card is 4111 1111 1111 1111."
    found = {hit.entity_type for hit in find_pii(text, analyzer=analyzer)}
    assert "EMAIL_ADDRESS" in found, found
    assert "CREDIT_CARD" in found, found


def test_seed_customer_queries_are_pii_clean(analyzer: AnalyzerEngine) -> None:
    """Boundary contract: every synthetic customer_query must be free of structured PII."""
    queries = _seed_customer_queries()
    assert queries, "no customer_query text found to scan"
    findings = scan_for_pii(queries, analyzer=analyzer)
    assert findings == {}, f"PII detected in seed customer_query text: {findings}"


def test_boundary_set_targets_contact_financial_pii() -> None:
    """Guardrail for the design choice: scan contact/financial PII, not PERSON/LOCATION NER."""
    assert "EMAIL_ADDRESS" in BOUNDARY_PII_ENTITIES
    assert "CREDIT_CARD" in BOUNDARY_PII_ENTITIES
    assert "PERSON" not in BOUNDARY_PII_ENTITIES
    assert "LOCATION" not in BOUNDARY_PII_ENTITIES
