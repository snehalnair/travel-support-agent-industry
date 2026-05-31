"""Schema contract checked against the SQLAlchemy MetaData (no database required).

This runs in the fast CI gate. Migrations applying to a real Postgres is verified
locally against the compose spine until a Postgres service is wired into CI.
"""

from tsa.db.schema import metadata

EXPECTED_TABLES = {
    "refund_policies",
    "refund_policy_tiers",
    "bookings",
    "refund_requests",
    "refund_decisions",
}


def test_expected_operational_tables_present() -> None:
    assert EXPECTED_TABLES <= set(metadata.tables)


def test_decision_ledger_requires_confirmation_and_amount() -> None:
    """No money-adjacent decision row without a confirmation token and an amount."""
    decisions = metadata.tables["refund_decisions"]
    assert decisions.c.confirmation_token.nullable is False
    assert decisions.c.amount_minor.nullable is False
    assert decisions.c.decision_kind.nullable is False


def test_requests_are_one_to_many_and_track_requester() -> None:
    """Multiple requests per booking, and the requester id for the IDOR gate."""
    requests = metadata.tables["refund_requests"]
    assert "requester_customer_id" in requests.c
    assert requests.c.booking_id.nullable is False  # FK to bookings, many per booking
