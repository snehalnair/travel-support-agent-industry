"""PII scanner for the data boundary (Presidio).

Untrusted free text -- synthetic customer queries today, live user input in Phase 2 --
is treated as data, never assumed clean. This wraps Presidio's AnalyzerEngine into a
small boundary check that flags high-confidence contact/financial PII so it can't
silently ride into the seed warehouse, a trace, or a prompt. The same scanner is
reused by the Phase 2.3 safety gate on live customer input.

Two deliberate scope choices:
- A focused entity set (emails, phones, cards, IBAN, SSN). PERSON/LOCATION NER is
  excluded on purpose: product names ("Colosseum") trip it, and the real boundary
  risk is leaked contact/financial PII, not attraction names.
- The lightweight en_core_web_sm model. Structured PII is pattern-driven, so the
  small model keeps CI fast; en_core_web_lg is the documented accuracy swap-in.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from functools import lru_cache

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider

# High-confidence, structured PII scanned at the boundary.
BOUNDARY_PII_ENTITIES: tuple[str, ...] = (
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "CREDIT_CARD",
    "IBAN_CODE",
    "US_SSN",
)

_NLP_CONFIGURATION = {
    "nlp_engine_name": "spacy",
    "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}],
}


@lru_cache(maxsize=1)
def build_analyzer() -> AnalyzerEngine:
    """Construct an AnalyzerEngine backed by the small English spaCy model.

    Cached: loading the model is the expensive part, so it happens once per process.
    """
    nlp_engine = NlpEngineProvider(nlp_configuration=_NLP_CONFIGURATION).create_engine()
    return AnalyzerEngine(nlp_engine=nlp_engine, supported_languages=["en"])


def find_pii(
    text: str,
    *,
    analyzer: AnalyzerEngine | None = None,
    entities: Sequence[str] = BOUNDARY_PII_ENTITIES,
    threshold: float = 0.5,
) -> list[RecognizerResult]:
    """Return PII entities detected in ``text`` at or above ``threshold``."""
    engine = analyzer if analyzer is not None else build_analyzer()
    return engine.analyze(
        text=text,
        language="en",
        entities=list(entities),
        score_threshold=threshold,
    )


def scan_for_pii(
    texts: Iterable[str],
    *,
    analyzer: AnalyzerEngine | None = None,
    entities: Sequence[str] = BOUNDARY_PII_ENTITIES,
    threshold: float = 0.5,
) -> dict[str, list[str]]:
    """Scan many strings; return ``{text: [entity_type, ...]}`` for any with findings.

    An empty dict means the batch is PII-clean at this boundary.
    """
    engine = analyzer if analyzer is not None else build_analyzer()
    findings: dict[str, list[str]] = {}
    for text in texts:
        hits = find_pii(text, analyzer=engine, entities=entities, threshold=threshold)
        if hits:
            findings[text] = [hit.entity_type for hit in hits]
    return findings
