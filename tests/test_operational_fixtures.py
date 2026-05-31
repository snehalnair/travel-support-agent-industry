"""Referential-integrity contract for the operational fixtures (bookings + refund policies).

This is the OPERATIONAL data plane (Postgres/OLTP-bound), distinct from the eval-seed
warehouse (DuckDB/OLAP) guarded by test_dataset_integrity.py. There is no database yet, so
these assertions stand in for the FOREIGN KEY and CHECK constraints that Phase 1.4 will
encode in the Postgres schema; until then CI guards fixture consistency HERE.

Every column is read as text (mirroring the warehouse's all_varchar) and coerced explicitly,
so a typo in a CSV fails loudly instead of being silently inferred into the wrong dtype.
"""

from pathlib import Path
from typing import cast

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "data" / "fixtures"

ALLOWED_STATUSES = {"CONFIRMED", "CANCELLED", "COMPLETED", "PENDING"}


def _read(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES_DIR / name, dtype=str).fillna("")


def _bool(series: pd.Series) -> pd.Series:
    assert set(series.unique()) <= {"true", "false"}, "all_sales_final must be 'true' or 'false'"
    return series.map({"true": True, "false": False})


def _policy_keys(policies: pd.DataFrame) -> set[tuple[str, str]]:
    return set(zip(policies["policy_id"], policies["policy_version"], strict=True))


@pytest.fixture(scope="module")
def policies() -> pd.DataFrame:
    return _read("refund_policies.csv")


@pytest.fixture(scope="module")
def tiers() -> pd.DataFrame:
    return _read("refund_policy_tiers.csv")


@pytest.fixture(scope="module")
def bookings() -> pd.DataFrame:
    return _read("bookings.csv")


def test_primary_keys_unique(policies: pd.DataFrame, bookings: pd.DataFrame) -> None:
    """(policy_id, policy_version) and booking_id are primary keys -- no duplicates."""
    keys = list(zip(policies["policy_id"], policies["policy_version"], strict=True))
    assert len(keys) == len(set(keys)), "duplicate (policy_id, policy_version)"
    assert bookings["booking_id"].is_unique, "duplicate booking_id"


def test_bookings_reference_existing_policy(bookings: pd.DataFrame, policies: pd.DataFrame) -> None:
    """FK: every booking's pinned (policy_id, policy_version) must exist."""
    known = _policy_keys(policies)
    pinned = set(zip(bookings["pinned_policy_id"], bookings["pinned_policy_version"], strict=True))
    assert pinned <= known, f"bookings pin unknown policy versions: {pinned - known}"


def test_tiers_reference_existing_policy(tiers: pd.DataFrame, policies: pd.DataFrame) -> None:
    """FK: every tier's (policy_id, policy_version) must exist."""
    known = _policy_keys(policies)
    tier_keys = set(zip(tiers["policy_id"], tiers["policy_version"], strict=True))
    assert tier_keys <= known, f"tiers reference unknown policy versions: {tier_keys - known}"


def test_supersedes_references_existing_version(policies: pd.DataFrame) -> None:
    """A policy that supersedes another must point at a real earlier version of itself."""
    known = _policy_keys(policies)
    for _, row in policies.iterrows():
        supersedes = str(row["supersedes_version"])
        if supersedes:
            assert (row["policy_id"], supersedes) in known, (
                f"{row['policy_id']} supersedes missing version {supersedes}"
            )


def test_tier_presence_matches_all_sales_final(policies: pd.DataFrame, tiers: pd.DataFrame) -> None:
    """Invariant: all-sales-final policies carry NO tiers; refundable ones carry >= 1."""
    final = _bool(cast(pd.Series, policies["all_sales_final"]))
    has_tiers = _policy_keys(tiers)
    for (_, row), is_final in zip(policies.iterrows(), final, strict=True):
        key = (row["policy_id"], row["policy_version"])
        if is_final:
            assert key not in has_tiers, f"all-sales-final policy {key} must have no tiers"
        else:
            assert key in has_tiers, f"refundable policy {key} must have at least one tier"


def test_tier_values_in_range(tiers: pd.DataFrame) -> None:
    """CHECK: refund_pct in [0, 100]; min_hours_before_start >= 0; tier_order >= 1."""
    pct = tiers["refund_pct"].astype(int)
    hours = tiers["min_hours_before_start"].astype(int)
    order = tiers["tier_order"].astype(int)
    assert pct.between(0, 100).all(), "refund_pct out of [0, 100]"
    assert (hours >= 0).all(), "negative min_hours_before_start"
    assert (order >= 1).all(), "tier_order must be >= 1"


def test_booking_scalar_constraints(bookings: pd.DataFrame) -> None:
    """CHECK: non-negative amount, >= 1 traveler, known status, purchase before start."""
    assert (bookings["amount_paid_minor"].astype(int) >= 0).all(), "negative amount_paid_minor"
    assert (bookings["traveler_count"].astype(int) >= 1).all(), "traveler_count must be >= 1"
    assert set(bookings["status"].unique()) <= ALLOWED_STATUSES, "unknown booking status"
    purchase = pd.to_datetime(bookings["purchase_ts"], utc=True)
    start = pd.to_datetime(bookings["start_ts"], utc=True)
    assert (purchase < start).all(), "purchase_ts must precede start_ts"


def test_booking_currency_matches_policy(bookings: pd.DataFrame, policies: pd.DataFrame) -> None:
    """A booking's currency must match the currency of its pinned policy."""
    merged = bookings.merge(
        policies[["policy_id", "policy_version", "currency"]],
        left_on=["pinned_policy_id", "pinned_policy_version"],
        right_on=["policy_id", "policy_version"],
        suffixes=("_booking", "_policy"),
    )
    assert len(merged) == len(bookings), "a booking failed to join its pinned policy"
    mismatch = merged[merged["currency_booking"] != merged["currency_policy"]]
    assert mismatch.empty, f"currency mismatch on bookings: {list(mismatch['booking_id'])}"


def test_booking_pinned_to_policy_in_force_at_purchase(
    bookings: pd.DataFrame, policies: pd.DataFrame
) -> None:
    """A booking can only pin a policy version that already existed when it was purchased."""
    merged = bookings.merge(
        policies[["policy_id", "policy_version", "effective_from"]],
        left_on=["pinned_policy_id", "pinned_policy_version"],
        right_on=["policy_id", "policy_version"],
    )
    purchase = pd.to_datetime(merged["purchase_ts"], utc=True)
    effective = pd.to_datetime(merged["effective_from"], utc=True)
    too_early = merged[purchase < effective]
    assert too_early.empty, (
        f"bookings pinned to a not-yet-effective policy: {list(too_early['booking_id'])}"
    )


def test_version_collision_is_grounded(policies: pd.DataFrame, bookings: pd.DataFrame) -> None:
    """The RG026 eval case needs a real collision: the Colosseum policy must have a legacy
    all-sales-final v6 AND a refundable v7, with at least one live booking pinned to v6."""
    colosseum = policies[policies["policy_id"] == "POL_COLOSSEUM"]
    versions = cast(pd.Series, colosseum["policy_version"])
    final_flags = _bool(cast(pd.Series, colosseum["all_sales_final"]))
    by_version = dict(zip(versions, final_flags, strict=True))
    assert by_version.get("v6") is True, "POL_COLOSSEUM v6 must be all-sales-final"
    assert by_version.get("v7") is False, "POL_COLOSSEUM v7 must be refundable"
    pinned_v6 = bookings[
        (bookings["pinned_policy_id"] == "POL_COLOSSEUM")
        & (bookings["pinned_policy_version"] == "v6")
    ]
    assert not pinned_v6.empty, "need a booking pinned to the legacy v6 policy"
