"""Ingestion: versioned CSV seeds -> warehouse tables.

The CSVs in ``data/seed/`` are the source of truth. ``seed_warehouse`` lands them into
DuckDB via native CSV read -- the same shape as ``bq load`` / a BigQuery external table.
No module in the running system reads Excel; the xlsx is a one-time import artifact only
(see scripts/seed_from_xlsx.py and ADR-0003). ``all_varchar`` keeps column types stable
and deterministic for the contract -- an eval seed is text, not inferred numerics.
"""

from pathlib import Path

import duckdb

SEED_DIR = Path(__file__).resolve().parents[3] / "data" / "seed"

TABLES = (
    "taxonomy",
    "router",
    "tool_plans",
    "response_quality",
    "retrieval_grounding",
    "safety_security",
)


def seed_warehouse(connection: duckdb.DuckDBPyConnection, seed_dir: Path = SEED_DIR) -> None:
    """Materialize each CSV seed as a warehouse table (idempotent)."""
    for table in TABLES:
        csv_path = seed_dir / f"{table}.csv"
        # `table` is always one of the fixed TABLES names above (never user input), so
        # interpolating it into DDL is safe -- DuckDB cannot bind an identifier as a param.
        connection.execute(
            f"CREATE OR REPLACE TABLE {table} AS "
            "SELECT * FROM read_csv(?, header = true, all_varchar = true)",
            [str(csv_path)],
        )
