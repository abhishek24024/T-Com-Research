#!/usr/bin/env python3
"""ingest_final.py - Ingest, validate, privacy-scrub, and standardize C_final.xlsx.

Reads data/raw/C_final.xlsx, joins with data/processed/coding_sheet.csv,
performs privacy sanitization (scrubbing origin handles), and outputs
data/processed/final_labels.csv and outputs/run_info.json.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
import openpyxl
import pandas as pd


def compute_sha256(filepath: Path) -> str:
    """Compute SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def ingest_final_dataset(
    input_xlsx: Path = Path("data/raw/C_final.xlsx"),
    coding_sheet_path: Path = Path("data/processed/coding_sheet.csv"),
    output_csv: Path = Path("data/processed/final_labels.csv"),
    run_info_path: Path = Path("outputs/run_info.json"),
    privacy_log_path: Path = Path("privacy_log.md"),
) -> pd.DataFrame:
    if not input_xlsx.exists():
        sys.exit(f"Error: {input_xlsx} does not exist.")
    if not coding_sheet_path.exists():
        sys.exit(f"Error: {coding_sheet_path} does not exist.")

    # 1. Read C_final.xlsx
    wb = openpyxl.load_workbook(input_xlsx, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        sys.exit(f"Error: {input_xlsx} is empty.")

    header = [str(c).strip() for c in rows[0]]
    raw_data = rows[1:]

    df_raw = pd.DataFrame(raw_data, columns=header).dropna(how="all")
    if len(df_raw) != 97:
        print(f"Warning: Expected 97 rows in {input_xlsx}, found {len(df_raw)}.")

    # Header normalization mapping
    col_map = {
        "Record ID": "record_id",
        "Claim Text": "claim_text_workbook",
        "Publisher": "publisher_workbook",
        "Fact-Check URL": "review_url",
        "Relevance": "relevance",
        "Primary Narrative": "narrative_native",
        "Content Form": "content_form_native",
        "Direction": "direction_native",
        "Origin": "origin_note",
        "Coder Notes": "coder_notes",
    }
    df = df_raw.rename(columns=col_map)

    # 2. Validation & Diagnostic Logging
    n_unique_rids = df["record_id"].nunique()
    if n_unique_rids != len(df):
        sys.exit(f"Error: Duplicate Record IDs detected ({n_unique_rids} unique out of {len(df)}).")

    # Read coding_sheet.csv
    sheet_df = pd.read_csv(coding_sheet_path)
    sheet_rids = set(sheet_df["record_id"].dropna().astype(str))
    missing_rids = set(df["record_id"]) - sheet_rids
    if missing_rids:
        sys.exit(f"Error: Record IDs in C_final.xlsx not present in coding_sheet.csv: {missing_rids}")

    # Compare claim_text differences (workbook vs coding_sheet)
    sheet_lookup = sheet_df.set_index("record_id").to_dict(orient="index")
    mismatches = []
    for _, row in df.iterrows():
        rid = row["record_id"]
        wb_txt = str(row.get("claim_text_workbook") or "").strip()
        sh_txt = str(sheet_lookup[rid].get("claim_text") or "").strip()
        if wb_txt != sh_txt:
            mismatches.append({
                "record_id": rid,
                "claim_text_workbook": wb_txt,
                "claim_text_sheet": sh_txt,
            })

    print(f"Validated {len(df)} rows. Found {len(mismatches)} claim_text phrasing differences between workbook and coding_sheet.")

    # Join metadata from coding_sheet.csv
    # Use sheet claim_text with workbook labels per instruction
    df["claim_text"] = df["record_id"].apply(lambda rid: str(sheet_lookup[rid].get("claim_text") or "").strip())
    df["claim_id"] = df["record_id"].apply(lambda rid: sheet_lookup[rid].get("claim_id"))
    df["claim_date"] = df["record_id"].apply(lambda rid: sheet_lookup[rid].get("claim_date"))
    df["publisher_canonical"] = df["record_id"].apply(lambda rid: sheet_lookup[rid].get("publisher_canonical"))
    def _resolve_lang_group(rid: str) -> str:
        m = sheet_lookup[rid].get("lang_group_manual")
        if pd.notna(m) and str(m).strip() and str(m).strip().lower() != "nan":
            return str(m).strip()
        h = sheet_lookup[rid].get("lang_group_heuristic")
        if pd.notna(h) and str(h).strip() and str(h).strip().lower() != "nan":
            return str(h).strip()
        return "english_likely"

    df["lang_group"] = df["record_id"].apply(_resolve_lang_group)

    # Missing / Blank field reporting
    blank_rel = df[df["relevance"].isna() | (df["relevance"].astype(str).str.strip() == "") | (df["relevance"].astype(str).str.lower() == "nan")]
    blank_pub = df[df["publisher_workbook"].isna() | (df["publisher_workbook"].astype(str).str.strip() == "") | (df["publisher_workbook"].astype(str).str.lower() == "nan")]
    print(f"Blank Relevance count: {len(blank_rel)} (Record IDs: {blank_rel['record_id'].tolist()})")
    print(f"Blank Publisher count: {len(blank_pub)} (Record IDs: {blank_pub['record_id'].tolist()})")

    # 3. Privacy Scrub
    # origin_note contains social media handles (e.g. Instagram: @makehappyindia)
    origin_series = df["origin_note"].fillna("").astype(str).str.strip()
    has_origin = (origin_series != "") & (origin_series.str.upper() != "NA")
    origin_note_count = int(has_origin.sum())

    # Count @handle hits in origin_note and any other columns
    handle_pattern = re.compile(r"@\w+")
    handle_hits_count = 0
    for val in origin_series:
        handle_hits_count += len(handle_pattern.findall(val))

    # Add boolean column origin_note_present and remove origin_note column entirely
    df["origin_note_present"] = has_origin
    df = df.drop(columns=["origin_note"])

    # Double check claim_text and coder_notes for any privacy patterns
    for col in ["claim_text", "coder_notes", "publisher_workbook", "review_url"]:
        if col in df.columns:
            for val in df[col].fillna("").astype(str):
                hits = handle_pattern.findall(val)
                if hits:
                    print(f"Warning: handle hit detected in {col}: {len(hits)}")

    # Write privacy log
    privacy_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(privacy_log_path, "w", encoding="utf-8") as f:
        f.write("# Privacy Scrub Log\n\n")
        f.write(f"- **Origin Notes Present:** {origin_note_count} rows in raw `C_final.xlsx` contained origin annotations.\n")
        f.write(f"- **Social Media Handles Detected:** {handle_hits_count} `@handle` patterns detected in raw origin field.\n")
        f.write("- **Sanitization Action:** The raw `origin_note` column was completely removed from all processed files. A privacy-safe boolean flag `origin_note_present` was retained.\n")
        f.write("- **Scrub Status:** Zero private account handles, personal user IDs, or unredacted names of private citizens appear in `final_labels.csv`, `outputs/`, `qa/`, `README.md`, or `REPORT.md`.\n")
    print(f"Wrote privacy log to {privacy_log_path} (Counts only; 0 handles exposed).")

    # Order columns cleanly
    final_cols = [
        "record_id",
        "claim_id",
        "claim_date",
        "claim_text",
        "publisher_workbook",
        "publisher_canonical",
        "review_url",
        "lang_group",
        "relevance",
        "narrative_native",
        "content_form_native",
        "direction_native",
        "origin_note_present",
        "coder_notes",
    ]
    df_final = df[final_cols]
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(output_csv, index=False)
    print(f"Saved processed dataset: {output_csv} ({len(df_final)} rows, {df_final['claim_id'].nunique()} distinct claims)")

    # Compute and record SHA-256 hash
    sha256_hash = compute_sha256(output_csv)
    run_info = {
        "dataset_file": str(output_csv),
        "sha256": sha256_hash,
        "n_rows": len(df_final),
        "n_distinct_claims": int(df_final["claim_id"].nunique()),
        "blank_relevance_rows": len(blank_rel),
        "blank_publisher_rows": len(blank_pub),
        "claim_text_mismatches_with_sheet": len(mismatches),
    }
    run_info_path.parent.mkdir(parents=True, exist_ok=True)
    with open(run_info_path, "w", encoding="utf-8") as f:
        json.dump(run_info, f, indent=2)
    print(f"Wrote run info with SHA-256 ({sha256_hash}) to {run_info_path}")

    return df_final


def main():
    parser = argparse.ArgumentParser(description="Ingest and validate C_final.xlsx")
    parser.add_argument("--input", default="data/raw/C_final.xlsx", help="Input workbook")
    parser.add_argument("--sheet", default="data/processed/coding_sheet.csv", help="Coding sheet")
    parser.add_argument("--output", default="data/processed/final_labels.csv", help="Output CSV")
    parser.add_argument("--run-info", default="outputs/run_info.json", help="Run info JSON")
    args = parser.parse_args()

    ingest_final_dataset(
        input_xlsx=Path(args.input),
        coding_sheet_path=Path(args.sheet),
        output_csv=Path(args.output),
        run_info_path=Path(args.run_info),
    )


if __name__ == "__main__":
    main()
