#!/usr/bin/env python3
"""Converts a filled adjudication Excel workbook into data/raw/adjudicated.csv.

Validates that all submitted values conform to the codebook controlled vocabularies.
Fails with a clear, descriptive error on any invalid value.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
import openpyxl
import pandas as pd

from config import (
    CONTENT_FORMS,
    DIRECTIONS,
    NARRATIVES,
    ORIGINS,
    RELEVANCES,
    get_out_dir,
    get_raw_data_dir,
)

ALLOWED_VALUES = {
    "relevance": set(RELEVANCES),
    "narrative": set(NARRATIVES),
    "content_form": set(CONTENT_FORMS),
    "direction": set(DIRECTIONS),
    "origin": set(ORIGINS),
}

FIELDS = ["relevance", "narrative", "content_form", "direction", "origin"]


def convert_adjudication_to_csv(xlsx_path: Path, csv_path: Path) -> pd.DataFrame:
    """Reads adjudication workbook and converts it to validated adjudicated.csv."""
    if not xlsx_path.exists():
        sys.exit(f"Error: Adjudication workbook not found: {xlsx_path}")

    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit(f"Error: Adjudication workbook {xlsx_path} is empty.")

    header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
    expected_cols = ["record_id", "field", "option_1", "option_2", "review_url", "final"]
    for col in expected_cols:
        if col not in header:
            sys.exit(f"Error: Missing required column '{col}' in {xlsx_path}. Found: {header}")

    col_idx = {name: header.index(name) for name in expected_cols}

    records: dict[str, dict[str, str]] = {}

    for row_num, r in enumerate(rows[1:], start=2):
        r_id = str(r[col_idx["record_id"]]).strip() if r[col_idx["record_id"]] is not None else ""
        field = str(r[col_idx["field"]]).strip().lower() if r[col_idx["field"]] is not None else ""
        final_val = str(r[col_idx["final"]]).strip() if r[col_idx["final"]] is not None else ""

        if not r_id or r_id.lower() == "none":
            continue

        if field not in ALLOWED_VALUES:
            sys.exit(f"Error (row {row_num}): Unknown field '{field}'. Allowed fields: {FIELDS}")

        if final_val and final_val.lower() != "none":
            # Validate value
            if final_val not in ALLOWED_VALUES[field]:
                sys.exit(
                    f"Error (row {row_num}, record {r_id}): Invalid value '{final_val}' for field '{field}'. "
                    f"Allowed values: {sorted(list(ALLOWED_VALUES[field]))}"
                )
            if r_id not in records:
                records[r_id] = {fld: "" for fld in FIELDS}
            records[r_id][field] = final_val

    if not records:
        # Create empty template DataFrame
        df_out = pd.DataFrame(columns=["record_id"] + FIELDS)
    else:
        out_rows = []
        for r_id, vals in sorted(records.items()):
            row_dict = {"record_id": r_id}
            row_dict.update(vals)
            out_rows.append(row_dict)
        df_out = pd.DataFrame(out_rows)

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(csv_path, index=False)
    print(f"Successfully converted {xlsx_path} -> {csv_path} ({len(df_out)} records adjudicated)")
    return df_out


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert adjudication workbook to adjudicated.csv.")
    parser.add_argument("input_xlsx", nargs="?", default=None, help="Path to adjudication.xlsx")
    parser.add_argument("output_csv", nargs="?", default=None, help="Path to adjudicated.csv")
    args = parser.parse_args()

    out_dir = get_out_dir()
    raw_dir = get_raw_data_dir()

    xlsx_path = Path(args.input_xlsx) if args.input_xlsx else (out_dir / "adjudication.xlsx")
    csv_path = Path(args.output_csv) if args.output_csv else (raw_dir / "adjudicated.csv")

    convert_adjudication_to_csv(xlsx_path, csv_path)


if __name__ == "__main__":
    main()
