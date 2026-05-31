# ADR-0003: Seed eval data is a code-validated warehouse asset

- Status: Accepted
- Date: 2026-05-31
- Deciders: Snehal Nair

## Context

The eval/seed data arrived as a single 9-sheet `.xlsx` workbook (`viator_seed_v1.xlsx`). We must
decide how that data enters the system, what the source of truth is, and how its integrity is
guarded. Facts that drive the decision:

- **No production system reads spreadsheets at runtime.** In a real platform, analytics/eval data
  lives in a SQL warehouse (here: BigQuery) and everything downstream reads it via `SELECT`.
- The workbook had **real defects**: `PAYMENT_BILLING` used as a router intent but undefined in the
  Taxonomy (orphan foreign key), and a duplicated `RG025` `case_id` (duplicate primary key). These are
  unambiguous data bugs, not style nits — exactly what a data contract exists to catch.
- A binary `.xlsx` is **not diffable**: a reviewer cannot see what a data change did in a PR.
- This is an **offline eval/analytics asset**, distinct from the agent's *operational* state store
  (bookings, refund state machine) which is transactional PostgreSQL (Phase 1.4). Two different jobs.

## Decision

1. **Source of truth = versioned per-table CSV seeds** in `data/seed/*.csv` — hand-editable, diffable,
   code-reviewed. The `.xlsx` is demoted to a **one-time import artifact** (kept sha-pinned in
   `data/raw/` for provenance); `scripts/seed_from_xlsx.py` regenerates the CSVs from it. **No module
   in the running system reads Excel.**
2. **Read boundary = a SQL warehouse behind a port.** The `WarehouseSource` Protocol is the seam; the
   local golden-path adapter is **DuckDB** (in-process, columnar, standard-SQL — a faithful BigQuery
   mirror at $0 with zero infra). **BigQuery is the documented swap-in**: replace `DuckDBSource` with a
   `BigQuerySource` whose `read_sql` calls `bigquery.Client().query(...).to_dataframe()`; the port and
   every caller are unchanged. Ingestion lands CSV → DuckDB via native `read_csv` (the `bq load` shape),
   forced to `all_varchar` for deterministic column types.
3. **The contract validates the SQL result set, not the spreadsheet.** Pandera schemas
   (`src/tsa/data/seed.py`) run against what comes back from `SELECT`, so drift fails in CI at the
   warehouse read boundary — the same place it would fail in production.
4. **Defects are fixed at the source as reviewed text diffs**, never scoped around or silently coerced
   in ETL. Concretely: `PAYMENT_BILLING` added to the Taxonomy as a real intent; the duplicated
   `RG025` version-collision case renumbered to `RG026`. Both fixes are visible in the CSV diff.

## Consequences

Positive:
- **Production-shaped read path** — SQL through a port/adapter, with a one-line BigQuery swap. No
  Excel anywhere in the running system.
- **Diffable data** — every data change is a reviewable text diff with git history; corrections are
  auditable.
- **Drift caught at the boundary** — the contract guards the SQL result, the real production surface.
- **Deterministic types** — `all_varchar` ingestion removes type-inference surprises for an all-text
  eval seed; provenance preserved (xlsx + `.sha256` + reproducible converter).

Negative:
- The CSV seed is now **mutable source** (we forgo immutable-raw purity) — mitigated by git history and
  the contract. If the eval set grows beyond a hand-curated seed, revisit (below).
- **DuckDB is not byte-for-byte BigQuery** (SQL-dialect edge cases) — mitigated by reading only
  standard SQL through a narrow port.
- Mild duplication in the repo (xlsx import artifact + CSV source) — accepted for provenance.

## Alternatives considered

- **Keep the `.xlsx` as source and edit it in place** — Rejected: a binary blob is undiffable and keeps
  an Excel dependency in ingestion.
- **Raw-immutable + dbt-style SQL staging transforms for corrections** — Considered; stronger
  immutable-raw provenance, but heavier structure than a ~150-row curated seed warrants. CSV-as-source
  delivers the diff-ability benefit at lower cost. Promote to this if the dataset scales.
- **Read the spreadsheet directly with pandas at the boundary** — Rejected: a spreadsheet is not a
  production read boundary; nothing should read Excel at runtime.
- **PostgreSQL for the eval data** — Rejected: Postgres is the OLTP store for *operational* state
  (Phase 1.4). BigQuery's analog is DuckDB (OLAP). Do not conflate the offline eval seed with the
  transactional store.
- **Provision real BigQuery now** — Rejected for $0 / no-creds; documented as a swap-in behind the port.

## Revisit when

The eval set outgrows a hand-curated seed (move to raw-immutable + dbt staging, or DVC for the data);
real BigQuery is provisioned (swap the adapter behind `WarehouseSource`); or column-type fidelity needs
exceed `all_varchar`. A material change supersedes this ADR rather than editing it.
