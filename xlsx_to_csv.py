#!/usr/bin/env python3
"""xlsx_to_csv.py - Convert a completed coder Excel workbook back to CSV with strict schema validation.

Validates controlled vocabularies from config.py:
  - relevance: RELEVANCES (on_topic, off_topic, unsure)
  - narrative: NARRATIVES
  - content_form: CONTENT_FORMS
  - direction: DIRECTIONS
  - origin: ORIGINS (documented_ai, documented_non_ai, disputed, unknown)

Fails with a descriptive error message on any invalid value.
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
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert coder Excel workbook to validated CSV.")
    parser.add_argument("input_file", nargs="?", default=None, help="Path to input .xlsx file")
    parser.add_argument("output_file", nargs="?", default=None, help="Path to output .csv file")
    parser.add_argument("--input", "-i", dest="opt_input", help="Optional named input path")
    parser.add_argument("--output", "-o", dest="opt_output", help="Optional named output path")
    return parser.parse_args()


def convert_xlsx_to_csv(input_path: Path, output_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        sys.exit(f"Error: Input workbook not found: {input_path}")

    wb = openpyxl.load_workbook(input_path, data_only=True)
    ws = wb.active

    # Read header row
    header = [cell.value for cell in ws[1]]
    header_map = {}
    for idx, h in enumerate(header):
        if not h:
            continue
        h_str = str(h).strip().lower().replace(" ", "_").replace("-", "_")
        header_map[h_str] = idx

    # Expected column mappings
    field_aliases = {
        "record_id": ["record_id", "recordid"],
        "relevance": ["relevance", "relevance_code"],
        "narrative": ["primary_narrative", "narrative", "narrative_code"],
        "content_form": ["content_form", "form"],
        "direction": ["direction", "political_direction"],
        "origin": ["origin", "media_origin"],
        "coder_notes": ["coder_notes", "notes"],
    }

    resolved_cols: dict[str, int] = {}
    for field, aliases in field_aliases.items():
        for alias in aliases:
            if alias in header_map:
                resolved_cols[field] = header_map[alias]
                break

    if "record_id" not in resolved_cols:
        sys.exit(f"Error: Missing required column 'Record ID' in workbook {input_path}.")

    # Collect and validate rows
    rows = []
    errors = []

    valid_relevances = set(RELEVANCES)
    valid_narratives = set(NARRATIVES)
    valid_forms = set(CONTENT_FORMS)
    valid_directions = set(DIRECTIONS)
    valid_origins = set(ORIGINS)

    for row_num, row_cells in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        # Stop on completely empty trailing rows
        if not any(row_cells):
            continue

        r_id = str(row_cells[resolved_cols["record_id"]] or "").strip()
        if not r_id:
            continue

        rel = str(row_cells[resolved_cols["relevance"]] or "").strip() if "relevance" in resolved_cols else ""
        narr = str(row_cells[resolved_cols["narrative"]] or "").strip() if "narrative" in resolved_cols else ""
        form = str(row_cells[resolved_cols["content_form"]] or "").strip() if "content_form" in resolved_cols else ""
        direction = str(row_cells[resolved_cols["direction"]] or "").strip() if "direction" in resolved_cols else ""
        origin = str(row_cells[resolved_cols["origin"]] or "").strip() if "origin" in resolved_cols else ""
        notes = str(row_cells[resolved_cols["coder_notes"]] or "").strip() if "coder_notes" in resolved_cols else ""

        # Validate controlled vocabularies if filled
        if rel and rel not in valid_relevances:
            errors.append(f"Row {row_num} (record_id={r_id}): Invalid relevance '{rel}'. Allowed: {sorted(list(valid_relevances))}")

        if narr and narr not in valid_narratives:
            errors.append(f"Row {row_num} (record_id={r_id}): Invalid narrative '{narr}'. Allowed: {sorted(list(valid_narratives))}")

        if form and form not in valid_forms:
            errors.append(f"Row {row_num} (record_id={r_id}): Invalid content_form '{form}'. Allowed: {sorted(list(valid_forms))}")

        if direction and direction not in valid_directions:
            errors.append(f"Row {row_num} (record_id={r_id}): Invalid direction '{direction}'. Allowed: {sorted(list(valid_directions))}")

        if origin and origin not in valid_origins:
            errors.append(f"Row {row_num} (record_id={r_id}): Invalid origin '{origin}'. Allowed: {sorted(list(valid_origins))}")

        rows.append({
            "record_id": r_id,
            "relevance": rel,
            "narrative": narr,
            "content_form": form,
            "direction": direction,
            "origin": origin,
            "coder_notes": notes,
        })

    if errors:
        print("=" * 60, file=sys.stderr)
        print(f"VALIDATION FAILED with {len(errors)} error(s) in {input_path}:", file=sys.stderr)
        for err in errors[:15]:
            print(f"  - {err}", file=sys.stderr)
        if len(errors) > 15:
            print(f"  ... and {len(errors) - 15} more errors.", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        sys.exit(1)

    df_out = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(output_path, index=False)
    print(f"Successfully converted {input_path} -> {output_path} ({len(df_out)} records validated)")
    return df_out


def main() -> None:
    args = parse_args()
    input_file = args.input_file or args.opt_input
    output_file = args.output_file or args.opt_output

    if not input_file or not output_file:
        sys.exit("Usage: python3 xlsx_to_csv.py <input.xlsx> <output.csv>")

    convert_xlsx_to_csv(Path(input_file), Path(output_file))


if __name__ == "__main__":
    main()
