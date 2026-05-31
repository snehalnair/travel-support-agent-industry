"""Integrity contract for the seed eval warehouse.

These tests validate the SQL result set at the warehouse read boundary (DuckDB locally,
BigQuery in production). If the seed drifts, CI goes red HERE -- before bad data can
reach an eval or the agent. Written RED first: they currently fail on real, verified
defects carried through from the raw seed.
"""

from collections.abc import Iterator

import duckdb
import pytest

from tsa.data.ingest import seed_warehouse
from tsa.data.seed import retrieval_schema, router_schema, taxonomy_values
from tsa.data.warehouse import DuckDBSource, WarehouseSource


@pytest.fixture
def warehouse() -> Iterator[WarehouseSource]:
    """Stand up an in-process DuckDB 'warehouse' seeded from the pinned raw file."""
    connection = duckdb.connect(":memory:")
    seed_warehouse(connection)
    try:
        yield DuckDBSource(connection)
    finally:
        connection.close()


def test_router_primary_intent_is_taxonomy_defined(warehouse: WarehouseSource) -> None:
    """Every router primary_intent must be a Taxonomy-defined intent (no orphans)."""
    intents = taxonomy_values(warehouse, "Intent")
    router = warehouse.read_sql("SELECT * FROM router")
    router_schema(intents).validate(router, lazy=True)


def test_retrieval_case_ids_are_unique(warehouse: WarehouseSource) -> None:
    """case_id is the primary key of retrieval_grounding -- no duplicates allowed."""
    rg = warehouse.read_sql("SELECT * FROM retrieval_grounding")
    retrieval_schema().validate(rg, lazy=True)
