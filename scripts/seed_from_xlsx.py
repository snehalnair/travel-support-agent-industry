"""One-time importer: vendored xlsx -> versioned per-table CSV seeds.

The CSVs in ``data/seed/`` are the source of truth: hand-editable, diffable, code-reviewed.
The xlsx is kept only as the original import artifact for provenance; runtime and ingestion
never read it. Re-run this script only to re-import from a fresh xlsx drop.

    uv run python scripts/seed_from_xlsx.py
"""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "data" / "raw" / "viator_seed_v1.xlsx"
OUT = ROOT / "data" / "seed"

# authoring sheet name -> clean seed/table name
SHEET_TO_TABLE = {
    "Taxonomy": "taxonomy",
    "1_Router": "router",
    "2_Tool_Plans": "tool_plans",
    "3_Response_Quality": "response_quality",
    "4_Retrieval_Grounding": "retrieval_grounding",
    "5_Safety_Security": "safety_security",
}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for sheet, table in SHEET_TO_TABLE.items():
        frame = pd.read_excel(XLSX, sheet_name=sheet)
        frame.to_csv(OUT / f"{table}.csv", index=False)
        print(f"{sheet:<22} -> data/seed/{table}.csv ({len(frame)} rows)")


if __name__ == "__main__":
    main()
