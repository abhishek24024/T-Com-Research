#!/usr/bin/env python3
"""merge_halves.py - Merge two partial coder workbooks into a single validated workbook.

Designed for the team workflow where two teammates split a coding workbook
(e.g., Coder 1 labels rows 2-49, Coder 2 labels rows 50-98).

Verifies:
  1. Each coder filled only their assigned rows and left the other half completely blank.
  2. Both workbooks share the exact same record IDs in the same row positions.
  3. All dropdown entries conform strictly to the codebook controlled vocabularies.
  4. No required cell is left blank in the final merged file:
     - Relevance is required for all records.
     - For on_topic and unsure records, narrative, content_form, direction, and origin are required.
  5. Preserves Excel data validations and review_url hyperlinks in the merged output.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any
import openpyxl

from config import (
    CONTENT_FORMS,
    DIRECTIONS,
    NARRATIVES,
    ORIGINS,
    RELEVANCES,
)

ALLOWED_VALUES = {
    "relevance": set(RELEVANCES),
    "narrative": set(NARRATIVES),
    "content_form": set(CONTENT_FORMS),
    "direction": set(DIRECTIONS),
    "origin": set(ORIGINS),
}

FIELD_ALIASES = {
    "record_id": ["record_id", "recordid", "record"],
    "claim_text": ["claim_text", "claim", "text"],
    "publisher_name": ["publisher", "publisher_name"],
    "review_url": ["fact_check_url", "review_url", "url"],
    "relevance": ["relevance", "relevance_code"],
    "narrative": ["primary_narrative", "narrative", "narrative_code"],
    "content_form": ["content_form", "form"],
    "direction": ["direction", "political_direction"],
    "origin": ["origin", "media_origin"],
    "coder_notes": ["coder_notes", "notes"],
}

CODER_FIELDS = ["relevance", "narrative", "content_form", "direction", "origin", "coder_notes"]
LABEL_FIELDS = ["relevance", "narrative", "content_form", "direction", "origin"]


def parse_range(range_str: str) -> tuple[int, int]:
    """Parse range string like '2-49' into (2, 49)."""
    parts = range_str.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Invalid range format '{range_str}'. Expected format like '2-49'.")
    start, end = int(parts[0].strip()), int(parts[1].strip())
    if start < 2 or end < start:
        raise ValueError(f"Invalid range bounds '{range_str}'. Start must be >= 2 and <= end.")
    return start, end


def find_column_indices(ws: openpyxl.worksheet.worksheet.Worksheet) -> dict[str, int]:
    """Identify column 1-based indices from header row (row 1)."""
    header_cells = [ws.cell(row=1, column=c).value for c in range(1, ws.max_column + 1)]
    col_map: dict[str, int] = {}

    for col_idx, h_val in enumerate(header_cells, start=1):
        if not h_val:
            continue
        clean_h = str(h_val).strip().lower().replace(" ", "_").replace("-", "_")
        for field, aliases in FIELD_ALIASES.items():
            if clean_h in aliases:
                col_map[field] = col_idx
                break

    if "record_id" not in col_map:
        raise ValueError("Missing required column 'Record ID' in workbook header.")
    for fld in LABEL_FIELDS:
        if fld not in col_map:
            raise ValueError(f"Missing required coding column '{fld}' in workbook header.")

    return col_map


def merge_half_workbooks(
    half1_path: Path,
    half2_path: Path,
    output_path: Path,
    rows1: tuple[int, int] = (2, 49),
    rows2: tuple[int, int] = (50, 98),
) -> Path:
    """Validate and merge two half-filled workbooks into output_path."""
    if not half1_path.exists():
        raise FileNotFoundError(f"Half 1 workbook not found: {half1_path}")
    if not half2_path.exists():
        raise FileNotFoundError(f"Half 2 workbook not found: {half2_path}")

    # Load workbooks: data_only=True for clean string reading
    wb1_data = openpyxl.load_workbook(half1_path, data_only=True)
    wb2_data = openpyxl.load_workbook(half2_path, data_only=True)
    ws1 = wb1_data.active
    ws2 = wb2_data.active

    col_map1 = find_column_indices(ws1)
    col_map2 = find_column_indices(ws2)

    errors: list[str] = []

    # 1. Structural check: row ranges and Record IDs must match
    r1_start, r1_end = rows1
    r2_start, r2_end = rows2
    min_row = min(r1_start, r2_start)
    max_row = max(r1_end, r2_end)

    if ws1.max_row < max_row:
        errors.append(f"Half 1 workbook has only {ws1.max_row} rows, expected at least {max_row}.")
    if ws2.max_row < max_row:
        errors.append(f"Half 2 workbook has only {ws2.max_row} rows, expected at least {max_row}.")

    for r in range(min_row, max_row + 1):
        rid1 = str(ws1.cell(row=r, column=col_map1["record_id"]).value or "").strip()
        rid2 = str(ws2.cell(row=r, column=col_map2["record_id"]).value or "").strip()
        if not rid1:
            errors.append(f"Half 1 workbook has empty Record ID at row {r}.")
        if not rid2:
            errors.append(f"Half 2 workbook has empty Record ID at row {r}.")
        if rid1 and rid2 and rid1 != rid2:
            errors.append(f"Record ID mismatch at row {r}: Half 1 has '{rid1}', Half 2 has '{rid2}'.")

    # 2. Isolation check: each person must leave the other half completely blank
    # In Half 1, rows2 should be blank for all CODER_FIELDS
    for r in range(r2_start, r2_end + 1):
        rid = str(ws1.cell(row=r, column=col_map1["record_id"]).value or "").strip()
        for fld in CODER_FIELDS:
            if fld in col_map1:
                val = str(ws1.cell(row=r, column=col_map1[fld]).value or "").strip()
                if val:
                    errors.append(
                        f"Half 1 isolation violation: row {r} (record_id={rid}) has non-blank {fld}='{val}'. "
                        f"Coder 1 must leave rows {r2_start}-{r2_end} completely blank."
                    )

    # In Half 2, rows1 should be blank for all CODER_FIELDS
    for r in range(r1_start, r1_end + 1):
        rid = str(ws2.cell(row=r, column=col_map2["record_id"]).value or "").strip()
        for fld in CODER_FIELDS:
            if fld in col_map2:
                val = str(ws2.cell(row=r, column=col_map2[fld]).value or "").strip()
                if val:
                    errors.append(
                        f"Half 2 isolation violation: row {r} (record_id={rid}) has non-blank {fld}='{val}'. "
                        f"Coder 2 must leave rows {r1_start}-{r1_end} completely blank."
                    )

    # 3. Dropdown value validation on assigned rows
    def validate_half_dropdowns(
        ws: openpyxl.worksheet.worksheet.Worksheet,
        col_map: dict[str, int],
        r_start: int,
        r_end: int,
        half_name: str,
    ) -> None:
        for r in range(r_start, r_end + 1):
            rid = str(ws.cell(row=r, column=col_map["record_id"]).value or "").strip()
            for fld in LABEL_FIELDS:
                val = str(ws.cell(row=r, column=col_map[fld]).value or "").strip()
                if val and val not in ALLOWED_VALUES[fld]:
                    errors.append(
                        f"{half_name} invalid dropdown: row {r} (record_id={rid}) has invalid {fld}='{val}'. "
                        f"Allowed values: {sorted(list(ALLOWED_VALUES[fld]))}"
                    )

    validate_half_dropdowns(ws1, col_map1, r1_start, r1_end, "Half 1")
    validate_half_dropdowns(ws2, col_map2, r2_start, r2_end, "Half 2")

    # 4. Check for blank required cells in the final merged data
    # Assemble merged representation
    merged_cells: dict[int, dict[str, str]] = {}
    for r in range(r1_start, r1_end + 1):
        rid = str(ws1.cell(row=r, column=col_map1["record_id"]).value or "").strip()
        merged_cells[r] = {"record_id": rid}
        for fld in CODER_FIELDS:
            merged_cells[r][fld] = str(ws1.cell(row=r, column=col_map1[fld]).value or "").strip() if fld in col_map1 else ""

    for r in range(r2_start, r2_end + 1):
        rid = str(ws2.cell(row=r, column=col_map2["record_id"]).value or "").strip()
        merged_cells[r] = {"record_id": rid}
        for fld in CODER_FIELDS:
            merged_cells[r][fld] = str(ws2.cell(row=r, column=col_map2[fld]).value or "").strip() if fld in col_map2 else ""

    for r in range(min_row, max_row + 1):
        r_data = merged_cells.get(r, {})
        rid = r_data.get("record_id", f"row_{r}")
        rel = r_data.get("relevance", "")

        # Relevance is strictly required for every record
        if not rel:
            errors.append(f"Merged row {r} (record_id={rid}): Blank required cell for 'relevance'.")
            continue

        if rel in ("on_topic", "unsure"):
            # All 4 other labels are required
            for fld in ["narrative", "content_form", "direction", "origin"]:
                val = r_data.get(fld, "")
                if not val:
                    errors.append(
                        f"Merged row {r} (record_id={rid}): Blank required cell for '{fld}' "
                        f"(required when relevance='{rel}')."
                    )

    if errors:
        err_msg = f"Merge validation failed with {len(errors)} error(s):\n" + "\n".join(f"  - {err}" for err in errors)
        print("=" * 70, file=sys.stderr)
        print(err_msg, file=sys.stderr)
        print("=" * 70, file=sys.stderr)
        raise ValueError(err_msg)

    # 5. Merge workbooks preserving formatting, validation, and hyperlinks
    # Load half1 without data_only to preserve formulas/links/data_validations
    wb_out = openpyxl.load_workbook(half1_path, data_only=False)
    ws_out = wb_out.active
    col_map_out = find_column_indices(ws_out)

    # Copy coder fields for rows2 from half2 into wb_out
    for r in range(r2_start, r2_end + 1):
        for fld in CODER_FIELDS:
            if fld in col_map2 and fld in col_map_out:
                val = ws2.cell(row=r, column=col_map2[fld]).value
                ws_out.cell(row=r, column=col_map_out[fld], value=val)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    wb_out.save(output_path)

    # 6. Print summary row counts
    count_half1 = r1_end - r1_start + 1
    count_half2 = r2_end - r2_start + 1
    total_records = max_row - min_row + 1

    print("=" * 60)
    print("Workbook Merge Successful:")
    print(f"  Half 1 (Coder 1 rows): {r1_start} to {r1_end} ({count_half1} records)")
    print(f"  Half 2 (Coder 2 rows): {r2_start} to {r2_end} ({count_half2} records)")
    print(f"  Total Merged Records : {total_records} records (rows {min_row} to {max_row})")
    print(f"  Output Saved To      : {output_path}")
    print("  Data Validations     : Preserved")
    print("  Review URL Links     : Preserved")
    print("=" * 60)

    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge two halves of a coder workbook into a single validated workbook.")
    parser.add_argument("half1_file", nargs="?", default=None, help="Path to Half 1 workbook (.xlsx)")
    parser.add_argument("half2_file", nargs="?", default=None, help="Path to Half 2 workbook (.xlsx)")
    parser.add_argument("output_file", nargs="?", default=None, help="Path to output merged workbook (.xlsx)")
    parser.add_argument("--half1", "-1", dest="opt_half1", help="Optional named input path for Half 1")
    parser.add_argument("--half2", "-2", dest="opt_half2", help="Optional named input path for Half 2")
    parser.add_argument("--output", "-o", dest="opt_output", help="Optional named output path")
    parser.add_argument("--rows1", default="2-49", help="Row range for Half 1 (default: 2-49)")
    parser.add_argument("--rows2", default="50-98", help="Row range for Half 2 (default: 50-98)")

    args = parser.parse_args()
    h1 = args.half1_file or args.opt_half1
    h2 = args.half2_file or args.opt_half2
    out = args.output_file or args.opt_output

    if not h1 or not h2 or not out:
        sys.exit("Usage: python3 merge_halves.py <half1.xlsx> <half2.xlsx> <merged_coder_X.xlsx> [--rows1 2-49] [--rows2 50-98]")

    try:
        r1 = parse_range(args.rows1)
        r2 = parse_range(args.rows2)
        merge_half_workbooks(Path(h1), Path(h2), Path(out), rows1=r1, rows2=r2)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
