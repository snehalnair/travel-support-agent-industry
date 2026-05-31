"""The data contract for the seed eval warehouse.

Pandera schemas are the executable contract, validated against the SQL result set at the
warehouse read boundary -- not against the spreadsheet. If the data drifts, CI fails here.
"""

from typing import cast

import pandas as pd
import pandera.pandas as pa

from tsa.data.warehouse import WarehouseSource


def taxonomy_values(source: WarehouseSource, category: str) -> set[str]:
    """The allowed-set of Values for one Taxonomy Category (e.g. 'Intent')."""
    frame = source.read_sql(
        'SELECT "Value" FROM taxonomy WHERE lower("Category") = ?',
        [category.casefold()],
    )
    values = cast(pd.Series, frame["Value"])
    return set(values.dropna())


def router_schema(allowed_intents: set[str]) -> pa.DataFrameSchema:
    """Contract for the router table: primary_intent must be a Taxonomy-defined intent."""
    return pa.DataFrameSchema(
        {
            "case_id": pa.Column(unique=True, nullable=False),
            "primary_intent": pa.Column(
                checks=pa.Check.isin(sorted(allowed_intents)),
                nullable=False,
            ),
        },
        strict=False,  # the table has many more columns; we only contract these
    )


def retrieval_schema() -> pa.DataFrameSchema:
    """Contract for the retrieval_grounding table: case_id is the primary key (unique)."""
    return pa.DataFrameSchema(
        {"case_id": pa.Column(unique=True, nullable=False)},
        strict=False,
    )
