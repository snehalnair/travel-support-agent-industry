"""Warehouse read-boundary for analytics/eval data.

Production reads eval/analytics data from a SQL warehouse (BigQuery). The golden path
here is DuckDB -- an in-process, columnar, standard-SQL engine that mirrors a
BigQuery/dbt stack locally at $0 with zero infra. BigQuery is the documented swap-in
(ADR-0003): replace ``DuckDBSource`` with a ``BigQuerySource`` whose ``read_sql`` calls
``google.cloud.bigquery.Client.query(...).to_dataframe()``. The ``WarehouseSource`` port
and every caller stay unchanged.
"""

from collections.abc import Sequence
from typing import Protocol

import duckdb
import pandas as pd


class WarehouseSource(Protocol):
    """Read port: anything that answers parameterized SQL with a DataFrame."""

    def read_sql(self, query: str, params: Sequence[object] | None = None) -> pd.DataFrame: ...


class DuckDBSource:
    """Local golden-path adapter over an in-process DuckDB connection."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self._con = connection

    def read_sql(self, query: str, params: Sequence[object] | None = None) -> pd.DataFrame:
        if params is None:
            return self._con.execute(query).df()
        return self._con.execute(query, list(params)).df()
