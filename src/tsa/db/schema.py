"""Operational (OLTP) schema for the refund slice — SQLAlchemy Core, model-first.

This is the TRANSACTIONAL plane (Postgres): booking state the agent reads and the
refund decisions code commits. It is deliberately separate from the eval-seed
warehouse (DuckDB/BigQuery in tsa.data), which holds the offline eval fixtures
(router, tool_plans, response_quality, retrieval_grounding, safety_security,
taxonomy) — those grade the agent and are never operational state.

Designed for real-world mess: a booking accrues MANY refund_requests over time
(re-asks, partial cancels, rebooking, weather disruption); each request the
confirmation gate clears yields an append-only refund_decision. Decisions are never
UPDATEd — a correction is a new row — because this is the money-adjacent ledger.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID

# Stable, predictable constraint names so Alembic autogenerate diffs cleanly.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}
metadata = MetaData(naming_convention=NAMING_CONVENTION)

# --- Reference tables (seeded from data/fixtures in 1.5) ----------------------

refund_policies = Table(
    "refund_policies",
    metadata,
    Column("policy_id", String(64), primary_key=True),
    Column("policy_version", String(16), primary_key=True),  # pinned per booking
    Column("product_family", Text, nullable=False),
    Column("all_sales_final", Boolean, nullable=False),
    Column("currency", String(3), nullable=False),
    Column("effective_from", Date, nullable=False),
    Column("supersedes_version", String(16), nullable=True),
    Column("notes", Text, nullable=True),
)

refund_policy_tiers = Table(
    "refund_policy_tiers",
    metadata,
    Column("policy_id", String(64), primary_key=True),
    Column("policy_version", String(16), primary_key=True),
    Column("tier_order", Integer, primary_key=True),
    Column("min_hours_before_start", Integer, nullable=False),
    Column("refund_pct", Integer, nullable=False),
    ForeignKeyConstraint(
        ["policy_id", "policy_version"],
        ["refund_policies.policy_id", "refund_policies.policy_version"],
    ),
    CheckConstraint("refund_pct BETWEEN 0 AND 100", name="refund_pct_range"),
    CheckConstraint("min_hours_before_start >= 0", name="min_hours_nonneg"),
    CheckConstraint("tier_order >= 1", name="tier_order_positive"),
)

bookings = Table(
    "bookings",
    metadata,
    Column("booking_id", String(32), primary_key=True),
    Column("customer_id", String(32), nullable=False, index=True),  # the owner
    Column("product_family", Text, nullable=False),
    Column("option_name", Text, nullable=False),
    Column("status", String(20), nullable=False),
    Column("amount_paid_minor", BigInteger, nullable=False),  # integer minor units
    Column("currency", String(3), nullable=False),
    Column("purchase_ts", DateTime(timezone=True), nullable=False),
    Column("start_ts", DateTime(timezone=True), nullable=False),
    Column("traveler_count", Integer, nullable=False),
    Column("pinned_policy_id", String(64), nullable=False),
    Column("pinned_policy_version", String(16), nullable=False),
    Column("supplier_timezone", String(64), nullable=False),
    ForeignKeyConstraint(
        ["pinned_policy_id", "pinned_policy_version"],
        ["refund_policies.policy_id", "refund_policies.policy_version"],
    ),
    # These four are the 1.1 Python asserts, now enforced by the engine itself:
    CheckConstraint("amount_paid_minor >= 0", name="amount_nonneg"),
    CheckConstraint("traveler_count >= 1", name="traveler_count_positive"),
    CheckConstraint("start_ts > purchase_ts", name="start_after_purchase"),
    CheckConstraint(
        "status IN ('CONFIRMED','PARTIALLY_CANCELLED','CANCELLED',"
        "'COMPLETED','REBOOKED','PENDING')",
        name="status_valid",
    ),
)

# --- Runtime tables (the agent writes these; start empty) --------------------

refund_requests = Table(
    "refund_requests",
    metadata,
    Column("request_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column("booking_id", String(32), ForeignKey("bookings.booking_id"), nullable=False, index=True),
    Column(
        "requester_customer_id", String(32), nullable=False
    ),  # IDOR: compare to bookings.customer_id
    Column("request_type", String(24), nullable=False),
    Column("raw_text", Text, nullable=False),  # untrusted customer text -> PII-scanned (1.3)
    Column("status", String(24), nullable=False, server_default="OPEN"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    CheckConstraint(
        "request_type IN ('CANCEL','PARTIAL_CANCEL','REBOOK','WEATHER_DISRUPTION','OTHER')",
        name="request_type_valid",
    ),
    CheckConstraint(
        "status IN ('OPEN','QUOTED','AWAITING_CONFIRMATION','CONFIRMED','DENIED','ESCALATED')",
        name="request_status_valid",
    ),
)

refund_decisions = Table(
    "refund_decisions",
    metadata,
    Column("decision_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4),
    Column(
        "request_id", UUID(as_uuid=True), ForeignKey("refund_requests.request_id"), nullable=False
    ),
    Column("booking_id", String(32), ForeignKey("bookings.booking_id"), nullable=False, index=True),
    Column("decision_kind", String(24), nullable=False),
    Column("amount_minor", BigInteger, nullable=False),  # code computes this, never the LLM
    Column("currency", String(3), nullable=False),
    Column("applied_policy_id", String(64), nullable=False),
    Column("applied_policy_version", String(16), nullable=False),  # the PINNED version, not latest
    Column("covered_traveler_count", Integer, nullable=False),  # partial cancellation
    Column("hours_before_start_at_decision", Integer, nullable=False),  # the quote basis
    Column("rebooked_to_booking_id", String(32), ForeignKey("bookings.booking_id"), nullable=True),
    Column("confirmation_token", String(64), nullable=False),  # NOT NULL = the confirm gate cleared
    Column("decided_by", String(32), nullable=False, server_default="agent"),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    ForeignKeyConstraint(
        ["applied_policy_id", "applied_policy_version"],
        ["refund_policies.policy_id", "refund_policies.policy_version"],
    ),
    CheckConstraint("amount_minor >= 0", name="amount_nonneg"),
    CheckConstraint("covered_traveler_count >= 0", name="covered_count_nonneg"),
    CheckConstraint(
        "decision_kind IN ('FULL_REFUND','PARTIAL_REFUND','DENY','REBOOK_CREDIT')",
        name="decision_kind_valid",
    ),
)
