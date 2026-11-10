#!/usr/bin/env python3
"""Stage 2: Build coding sheet and finalize human labels into dataset.

Subcommands:
  make-sheet: Filters raw claims, normalises text, proposes claim_ids, writes coding sheet and coder template.
  finalize: Merges coder labels, resolves disagreements, enforces one narrative per claim, merges rare classes, writes dataset.csv.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
import pandas as pd

from config import (
    CONTENT_FORMS,
    DIRECTIONS,
    MIN_CLAIMS_PER_CLASS,
    NARRATIVES,
    ORIGINS,
    RELEVANCES,
    get_out_dir,
    get_processed_data_dir,
    get_raw_data_dir,
)
from utils import (
    UnionFind,
    compute_label_agreement,
    detect_lang_group_heuristic,
    detect_script,
    filter_claims_by_date,
    normalize_text,
    propose_claim_ids,
)


def assign_topic_flag(text: str) -> str:
    """Heuristic flag for topic relevance: 'likely_on_topic' vs 'needs_check'."""
    text_lower = text.lower()

    off_topic_keywords = [
        "10 october", "october 10", "10th october", "2 october", "october 2",
        "shivaji park", "mumbai", "jaipur", "kolkata", "jharkhand", "bihar",
        "lakhimpur", "bengaluru", "nana patekar", "producer"
    ]
    if any(k in text_lower for k in off_topic_keywords):
        return "needs_check"

    on_topic_keywords = [
        "jantar mantar", "20 july", "neet", "lathicharge", "लाठीचार्ज",
        "संसद", "march", "protest", "प्रदर्शन", "police", "पुलिस",
        "student", "छात्र", "भीड़", "crowd", "stone", "पथराव", "cjp",
        "cockroach", "आंदोलन", "rally"
    ]
    if any(k in text_lower for k in on_topic_keywords):
        return "likely_on_topic"

    return "needs_check"


def get_canonical_publisher(publisher_name: str | None, review_url: str | None = None) -> str:
    """Maps publisher variants and domains to standard canonical outlet names."""
    pub = str(publisher_name).strip() if publisher_name and str(publisher_name).lower() != "nan" else ""
    url = str(review_url).lower() if review_url else ""

    if "afp.com" in url or pub in ["AFP Fact Check", "फ़ैक्ट चेक"]:
        return "AFP Fact Check"
    if "boomlive.in" in url or pub in ["BOOM", "BOOM Fact Check"]:
        return "BOOM"
    if "ptinews.com" in url or pub in ["PTI", "Press Trust of India"]:
        return "Press Trust of India"
    if "vishvasnews.com" in url or pub in ["विश्वास न्यूज", "Vishwas News"]:
        return "विश्वास न्यूज"
    if "thequint.com" in url or pub == "The Quint":
        return "The Quint"
    if "altnews.in" in url or pub == "Alt News":
        return "Alt News"
    if "aajtak.in" in url or pub == "AajTak":
        return "AajTak"
    if "factly.in" in url or pub == "FACTLY":
        return "FACTLY"
    if "lighthousejournalism.com" in url or pub == "Lighthouse Journalism":
        return "Lighthouse Journalism"
    if "newsmobile.in" in url or pub == "NewsMobile":
        return "NewsMobile"
    if "telugupost.com" in url or pub == "Telugu Post":
        return "Telugu Post"
    if "indiatoday.in" in url or pub == "India Today":
        return "India Today"
    if "digiteye.in" in url or pub == "DigitEye India":
        return "DigitEye India"

    return pub or "Unknown"



def run_apply_merges(merges_path_str: str | None = None) -> None:
    """Applies human-confirmed claim_id merges from duplicate review CSV using Union-Find.
    
    Safe to re-run repeatedly by always starting from the pre-merge baseline if present.
    """
    proc_dir = get_processed_data_dir()
    sheet_path = proc_dir / "coding_sheet.csv"
    pre_merge_path = proc_dir / "coding_sheet_pre_merge.csv"

    # Prefer reading from pristine pre-merge copy if it exists to allow safe reruns
    source_path = pre_merge_path if pre_merge_path.exists() else sheet_path
    if not source_path.exists():
        sys.exit(f"Error: Neither {pre_merge_path} nor {sheet_path} found. Run make-sheet first.")

    out_dir = get_out_dir()
    if merges_path_str:
        merges_path = Path(merges_path_str)
    else:
        merges_path = out_dir / "duplicate_pairs_review.csv"

    if not merges_path.exists():
        sys.exit(f"Error: Merges file not found: {merges_path}")

    sheet_df = pd.read_csv(source_path).fillna("")
    merges_df = pd.read_csv(merges_path).fillna("")

    before_rows = len(sheet_df)
    before_claims = sheet_df["claim_id"].nunique()

    # Find confirmed merges: same_claim_FINAL in ['yes', 'same', 'true', '1']
    confirmed = merges_df[
        merges_df["same_claim_FINAL"].astype(str).str.strip().str.lower().isin(["yes", "same", "true", "1"])
    ]

    uf = UnionFind()
    # Map record_id to claim_id
    rec_to_cid = dict(zip(sheet_df["record_id"], sheet_df["claim_id"]))

    merge_count = 0
    for _, row in confirmed.iterrows():
        r1 = str(row["record_id_1"]).strip()
        r2 = str(row["record_id_2"]).strip()
        c1 = rec_to_cid.get(r1)
        c2 = rec_to_cid.get(r2)
        if c1 and c2 and c1 != c2:
            uf.union(c1, c2)
            merge_count += 1

    # Apply unified claim_ids
    sheet_df["claim_id"] = sheet_df["claim_id"].apply(lambda cid: uf.find(cid))

    after_rows = len(sheet_df)
    after_claims = sheet_df["claim_id"].nunique()

    sheet_df.to_csv(sheet_path, index=False)
    # Update slim template
    cols_tpl = ["record_id", "relevance", "narrative", "content_form", "direction", "origin", "coder_notes"]
    available_cols = [c for c in cols_tpl if c in sheet_df.columns]
    if available_cols:
        sheet_df[available_cols].to_csv(proc_dir / "coder_template.csv", index=False)

    print("=" * 65)
    print("CLAIM MERGES APPLIED (Transitive Union-Find)")
    print("=" * 65)
    print(f"Source coding sheet: {source_path}")
    print(f"Confirmed merge pairs processed: {len(confirmed)} ({merge_count} active cross-cluster unions)")
    print(f"Records (rows):   {before_rows} -> {after_rows} (unchanged)")
    print(f"Distinct claims:  {before_claims} -> {after_claims} (reduction of {before_claims - after_claims})")
    print(f"Updated coding sheet saved to: {sheet_path}")
    print("=" * 65)


def run_make_sheet() -> None:
    raw_dir = get_raw_data_dir()
    proc_dir = get_processed_data_dir()
    proc_dir.mkdir(parents=True, exist_ok=True)

    api_path = raw_dir / "factcheck_api_claims.csv"
    manual_path = raw_dir / "manual_claims.csv"

    dfs = []
    if api_path.exists():
        api_df = pd.read_csv(api_path)
        if not api_df.empty:
            dfs.append(api_df)
    if manual_path.exists():
        manual_df = pd.read_csv(manual_path)
        if not manual_df.empty:
            dfs.append(manual_df)

    if not dfs:
        sys.exit(f"Error: No raw claim files found. Checked {api_path} and {manual_path}.")

    combined = pd.concat(dfs, ignore_index=True)
    initial_len = len(combined)

    # 1. Drop empty claim text
    combined = combined[combined["claim_text"].notna() & (combined["claim_text"].astype(str).str.strip() != "")]
    drop_empty = initial_len - len(combined)

    # 2. Date filter
    filtered_df, drop_counts = filter_claims_by_date(combined)
    print("Stage 2a Filtering Summary:")
    print(f"  Initial records: {initial_len}")
    print(f"  Dropped empty claim text: {drop_empty}")
    for reason, count in drop_counts.items():
        print(f"  Dropped ({reason}): {count}")
    print(f"  Retained after date filter: {len(filtered_df)}")

    if filtered_df.empty:
        sys.exit("Error: No claims remained after date filtering.")

    # 3. Normalise text and drop duplicates on (normalised_text, review_url)
    filtered_df = filtered_df.copy()
    filtered_df["normalised_text"] = filtered_df["claim_text"].apply(normalize_text)
    pre_dedup = len(filtered_df)
    filtered_df = filtered_df.drop_duplicates(subset=["normalised_text", "review_url"])
    print(f"  Dropped exact duplicates on (normalised_text, review_url): {pre_dedup - len(filtered_df)}")

    # 4. Propose claim_ids via TF-IDF char-wb cosine similarity
    texts = filtered_df["claim_text"].tolist()
    proposed_ids = propose_claim_ids(texts)
    filtered_df["claim_id"] = proposed_ids
    unique_claims = filtered_df["claim_id"].nunique()
    print(f"  Proposed {unique_claims} unique claim_ids across {len(filtered_df)} records.")

    # 5. Assign record_id, script, and lang_group_heuristic
    filtered_df = filtered_df.reset_index(drop=True)
    filtered_df["record_id"] = [f"R{i+1:04d}" for i in range(len(filtered_df))]
    filtered_df["topic_flag"] = filtered_df["claim_text"].apply(assign_topic_flag)
    filtered_df["publisher_canonical"] = filtered_df.apply(
        lambda r: get_canonical_publisher(r.get("publisher_name"), r.get("review_url")),
        axis=1,
    )
    filtered_df["script"] = filtered_df["claim_text"].apply(detect_script)
    filtered_df["lang_group_heuristic"] = filtered_df.apply(
        lambda r: detect_lang_group_heuristic(str(r["claim_text"]), script=str(r["script"])),
        axis=1,
    )

    # Columns for human coders to fill
    filtered_df["lang_group_manual"] = ""
    filtered_df["relevance"] = ""
    filtered_df["narrative"] = ""
    filtered_df["content_form"] = ""
    filtered_df["direction"] = ""
    filtered_df["origin"] = ""
    filtered_df["coder_notes"] = ""

    # Desired columns
    cols = [
        "record_id",
        "claim_id",
        "claim_date",
        "review_date",
        "date_check",
        "topic_flag",
        "publisher_name",
        "publisher_canonical",
        "review_url",
        "text_source",
        "claim_text",
        "script",
        "lang_group_heuristic",
        "lang_group_manual",
        "relevance",
        "narrative",
        "content_form",
        "direction",
        "origin",
        "coder_notes",
    ]
    sheet_df = filtered_df[cols]
    pre_merge_path = proc_dir / "coding_sheet_pre_merge.csv"
    sheet_df.to_csv(pre_merge_path, index=False)
    sheet_path = proc_dir / "coding_sheet.csv"
    sheet_df.to_csv(sheet_path, index=False)
    print(f"Saved pre-merge coding sheet baseline: {pre_merge_path}")
    print(f"Saved coding sheet: {sheet_path}")

    # Write slim coder template
    cols_tpl = ["record_id", "relevance", "narrative", "content_form", "direction", "origin", "coder_notes"]
    coder_template = filtered_df[cols_tpl]
    template_path = proc_dir / "coder_template.csv"
    coder_template.to_csv(template_path, index=False)
    print(f"Saved coder template: {template_path}")


def write_adjudication_workbook(disagreements_df: pd.DataFrame, excel_path: Path) -> None:
    """Generates adjudication.xlsx with openpyxl, frozen headers, wrapped text,
    clickable hyperlinks, and row-specific dropdown data validation per field."""
    import openpyxl
    from openpyxl.worksheet.datavalidation import DataValidation
    from openpyxl.styles import Font, Alignment, PatternFill

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Adjudication"
    ws.freeze_panes = "A2"

    headers = ["record_id", "field", "option_1", "option_2", "review_url", "final"]
    ws.append(headers)

    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1F497D", end_color="1F497D", fill_type="solid")
    align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

    for col_idx, col_name in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center

    field_validations = {
        "relevance": DataValidation(type="list", formula1='"on_topic,off_topic,unsure"', allow_blank=True),
        "narrative": DataValidation(type="list", formula1=f'"{",".join(NARRATIVES)}"', allow_blank=True),
        "content_form": DataValidation(type="list", formula1=f'"{",".join(CONTENT_FORMS)}"', allow_blank=True),
        "direction": DataValidation(type="list", formula1=f'"{",".join(DIRECTIONS)}"', allow_blank=True),
        "origin": DataValidation(type="list", formula1=f'"{",".join(ORIGINS)}"', allow_blank=True),
    }
    for dv in field_validations.values():
        ws.add_data_validation(dv)

    for row_idx, row in disagreements_df.iterrows():
        excel_row = row_idx + 2
        r_id = str(row.get("record_id", ""))
        fld = str(row.get("field", "")).strip().lower()
        opt1 = str(row.get("option_1", ""))
        opt2 = str(row.get("option_2", ""))
        url = str(row.get("review_url", ""))
        final_val = str(row.get("final", ""))

        ws.append([r_id, fld, opt1, opt2, url, final_val])

        # Hyperlink on review_url (column 5)
        url_cell = ws.cell(row=excel_row, column=5)
        if url.startswith("http"):
            url_cell.hyperlink = url
            url_cell.font = Font(name="Calibri", size=10, color="0000FF", underline="single")
        url_cell.alignment = align_left

        # Add data validation to final cell (column 6)
        final_cell = ws.cell(row=excel_row, column=6)
        if fld in field_validations:
            field_validations[fld].add(final_cell)

    widths = {"A": 12, "B": 15, "C": 25, "D": 25, "E": 45, "F": 25}
    for col_letter, width in widths.items():
        ws.column_dimensions[col_letter].width = width

    excel_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(excel_path)
    print(f"Generated adjudication workbook: {excel_path}")


def run_finalize() -> None:
    proc_dir = get_processed_data_dir()
    raw_dir = get_raw_data_dir()
    out_dir = get_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    sheet_path = proc_dir / "coding_sheet.csv"
    if not sheet_path.exists():
        sys.exit(f"Error: Missing {sheet_path}. Run 'python3 02_build_dataset.py make-sheet' first.")

    coder_a_path = raw_dir / "coder_A.csv"
    if not coder_a_path.exists():
        sys.exit(f"Error: Missing human coder file {coder_a_path}.")

    sheet_df = pd.read_csv(sheet_path).fillna("")
    coder_a = pd.read_csv(coder_a_path).fillna("")

    coder_b_path = raw_dir / "coder_B.csv"
    has_coder_b = coder_b_path.exists()
    coder_b = pd.read_csv(coder_b_path).fillna("") if has_coder_b else pd.DataFrame()

    adj_path = raw_dir / "adjudicated.csv"
    has_adj = adj_path.exists()
    adj_df = pd.read_csv(adj_path).fillna("") if has_adj else pd.DataFrame()

    FIELDS = ["relevance", "narrative", "content_form", "direction", "origin"]
    ALLOWED_VALUES = {
        "relevance": set(RELEVANCES),
        "narrative": set(NARRATIVES),
        "content_form": set(CONTENT_FORMS),
        "direction": set(DIRECTIONS),
        "origin": set(ORIGINS),
    }

    # 1. Validate vocabulary across coder files and adjudicated.csv
    def validate_file_values(df: pd.DataFrame, source_name: str) -> None:
        if df.empty:
            return
        for fld in FIELDS:
            if fld in df.columns:
                vals = set(df[fld].astype(str).str.strip().unique())
                vals.discard("")
                vals.discard("nan")
                invalid = vals - ALLOWED_VALUES[fld]
                if invalid:
                    sys.exit(
                        f"Error: Invalid {fld} codes in {source_name}: {sorted(list(invalid))}. "
                        f"Expected subset of {sorted(list(ALLOWED_VALUES[fld]))}."
                    )

    validate_file_values(coder_a, "coder_A.csv")
    if has_coder_b and not coder_b.empty:
        validate_file_values(coder_b, "coder_B.csv")
    if has_adj and not adj_df.empty:
        validate_file_values(adj_df, "adjudicated.csv")

    # 2. Agreement between Coder A and B (computed before adjudication)
    if has_coder_b and not coder_b.empty:
        cols_merge = ["record_id"]
        for c in FIELDS:
            if c in coder_a.columns and c in coder_b.columns:
                cols_merge.append(c)

        merged_ab = pd.merge(
            coder_a[cols_merge],
            coder_b[cols_merge],
            on="record_id",
            suffixes=("_A", "_B"),
        )
        if not merged_ab.empty:
            cb_ids_path = proc_dir / "codebook_example_ids.csv"
            if not cb_ids_path.exists():
                cb_ids_path = Path("data/processed/codebook_example_ids.csv")

            ex_ids = set()
            if cb_ids_path.exists():
                ex_df = pd.read_csv(cb_ids_path)
                if "record_id" in ex_df.columns:
                    ex_ids = set(ex_df["record_id"].dropna().astype(str).tolist())

            merged_ab_non_ex = merged_ab[~merged_ab["record_id"].astype(str).isin(ex_ids)]

            def eval_agreement(subset: pd.DataFrame) -> dict[str, Any]:
                res: dict[str, Any] = {"n": len(subset)}
                for fld in FIELDS:
                    col_a = f"{fld}_A"
                    col_b = f"{fld}_B"
                    if col_a in subset.columns and col_b in subset.columns:
                        res[fld] = compute_label_agreement(subset[col_a].tolist(), subset[col_b].tolist())
                    else:
                        res[fld] = {"n": 0, "percent_agreement": 0.0, "cohen_kappa": 0.0}
                return res

            all_res = eval_agreement(merged_ab)
            non_ex_res = eval_agreement(merged_ab_non_ex)

            agreement_payload: dict[str, Any] = {
                "all_rows": all_res,
                "non_example_rows": non_ex_res,
            }
            for fld in FIELDS:
                if fld in all_res:
                    agreement_payload[fld] = {
                        "all_rows": all_res[fld],
                        "non_example_rows": non_ex_res[fld],
                    }

            agreement_json_path = out_dir / "label_agreement.json"
            with open(agreement_json_path, "w", encoding="utf-8") as f:
                json.dump(agreement_payload, f, indent=2)
            print(f"Reported pre-adjudication coder agreement to: {agreement_json_path}")
            for fld in FIELDS:
                print(f"  {fld:<15} (n={all_res['n']}): Agreement = {all_res[fld]['percent_agreement']}% (Kappa: {all_res[fld]['cohen_kappa']})")

    # 3. Disagreements identification across all fields
    disagreements = []
    disagreements_key = []
    import random
    rng = random.Random(42)

    a_dict = coder_a.set_index("record_id").to_dict(orient="index")
    b_dict = coder_b.set_index("record_id").to_dict(orient="index") if (has_coder_b and not coder_b.empty) else {}
    adj_dict = adj_df.set_index("record_id").to_dict(orient="index") if (has_adj and not adj_df.empty) else {}

    if has_coder_b and not coder_b.empty:
        for _, s_row in sheet_df.iterrows():
            r_id = s_row["record_id"]
            review_url = s_row.get("review_url", "")
            a_row = a_dict.get(r_id, {})
            b_row = b_dict.get(r_id, {})

            for fld in FIELDS:
                val_a = str(a_row.get(fld, "")).strip()
                val_b = str(b_row.get(fld, "")).strip()

                is_disagreement = False
                if val_a != "" and val_b != "":
                    if val_a != val_b or val_a == "unsure" or val_b == "unsure":
                        is_disagreement = True

                if is_disagreement:
                    if rng.random() < 0.5:
                        opt_1, opt_2 = val_a, val_b
                        a_is_opt = 1
                    else:
                        opt_1, opt_2 = val_b, val_a
                        a_is_opt = 2

                    disagreements.append({
                        "record_id": r_id,
                        "field": fld,
                        "option_1": opt_1,
                        "option_2": opt_2,
                        "review_url": review_url,
                        "final": "",
                    })
                    disagreements_key.append({
                        "record_id": r_id,
                        "field": fld,
                        "coder_A_value": val_a,
                        "coder_B_value": val_b,
                        "option_1": opt_1,
                        "option_2": opt_2,
                        "coder_A_option": f"option_{a_is_opt}",
                        "review_url": review_url,
                    })

    disagreements_df = pd.DataFrame(disagreements)
    disagreements_path = out_dir / "label_disagreements.csv"
    disagreements_df.to_csv(disagreements_path, index=False)

    key_path = out_dir / "label_disagreements_key.csv"
    pd.DataFrame(disagreements_key).to_csv(key_path, index=False)
    print(f"Logged {len(disagreements_df)} field-level disagreements to: {disagreements_path}")
    print(f"Logged blind randomization key to: {key_path}")

    # Write adjudication.xlsx
    excel_path = out_dir / "adjudication.xlsx"
    write_adjudication_workbook(disagreements_df, excel_path)

    # 4. Final label resolution per field & record
    final_records = []
    excluded_off_topic_records = []

    for _, s_row in sheet_df.iterrows():
        r_id = s_row["record_id"]
        c_id = s_row["claim_id"]
        row_dict = s_row.to_dict()

        a_row = a_dict.get(r_id, {})
        b_row = b_dict.get(r_id, {})
        adj_row = adj_dict.get(r_id, {})

        resolved_values: dict[str, str] = {}
        resolved_statuses: dict[str, str] = {}

        for fld in FIELDS:
            val_a = str(a_row.get(fld, "")).strip() if a_row else ""
            val_b = str(b_row.get(fld, "")).strip() if (b_row and has_coder_b and not coder_b.empty) else ""
            val_adj = str(adj_row.get(fld, "")).strip() if adj_row else ""

            if val_a != "" and val_b != "":
                # Both coders filled
                if val_a == val_b and val_a != "unsure":
                    if val_adj != "":
                        resolved_values[fld] = val_adj
                        resolved_statuses[fld] = "adjudicated"
                    else:
                        resolved_values[fld] = val_a
                        resolved_statuses[fld] = "two_coders_agree"
                else:
                    # They differ OR at least one is 'unsure'
                    if val_adj != "":
                        resolved_values[fld] = val_adj
                        resolved_statuses[fld] = "adjudicated"
                    else:
                        resolved_values[fld] = ""
                        resolved_statuses[fld] = "unresolved_disagreement"
            elif val_a != "" or val_b != "":
                # Only one coder filled
                if val_adj != "":
                    resolved_values[fld] = val_adj
                    resolved_statuses[fld] = "adjudicated"
                else:
                    resolved_values[fld] = val_a if val_a != "" else val_b
                    resolved_statuses[fld] = "single_coder"
            else:
                # Neither coder filled
                if val_adj != "":
                    resolved_values[fld] = val_adj
                    resolved_statuses[fld] = "adjudicated"
                else:
                    resolved_values[fld] = ""
                    resolved_statuses[fld] = "unlabelled"

        # Relevance gate
        resolved_rel = resolved_values["relevance"]
        if resolved_rel == "off_topic":
            row_dict["exclusion_reason"] = "coder_marked_off_topic"
            excluded_off_topic_records.append(row_dict)
            continue  # Excluded from dataset.csv; NEVER labelled 'other'

        row_dict["text"] = s_row["claim_text"]
        row_dict["lang_group"] = s_row.get("lang_group_manual") or s_row.get("lang_group_heuristic") or "english_likely"
        row_dict["relevance"] = resolved_values["relevance"]
        row_dict["narrative"] = resolved_values["narrative"]
        row_dict["narrative_original"] = resolved_values["narrative"]
        row_dict["content_form"] = resolved_values["content_form"]
        row_dict["direction"] = resolved_values["direction"]
        row_dict["origin"] = resolved_values["origin"]

        # Per-field status columns
        row_dict["status_relevance"] = resolved_statuses["relevance"]
        row_dict["status_narrative"] = resolved_statuses["narrative"]
        row_dict["status_content_form"] = resolved_statuses["content_form"]
        row_dict["status_direction"] = resolved_statuses["direction"]
        row_dict["status_origin"] = resolved_statuses["origin"]
        row_dict["label_status"] = resolved_statuses["narrative"]

        final_records.append(row_dict)

    # Write excluded off-topic rows
    excluded_path = out_dir / "excluded_off_topic.csv"
    excluded_df = pd.DataFrame(excluded_off_topic_records)
    excluded_df.to_csv(excluded_path, index=False)
    n_excl_rows = len(excluded_df)
    n_excl_claims = excluded_df["claim_id"].nunique() if (not excluded_df.empty and "claim_id" in excluded_df.columns) else 0
    print(f"Excluded off-topic records: {n_excl_rows} rows ({n_excl_claims} distinct claims) written to {excluded_path}")

    df_final = pd.DataFrame(final_records)

    # 5. Enforce one narrative per claim_id: majority vote across records sharing claim_id
    conflicts = []
    if not df_final.empty and "claim_id" in df_final.columns:
        for c_id, group in df_final.groupby("claim_id"):
            valid_group = group[group["status_narrative"] != "unresolved_disagreement"]
            narrs = [n for n in valid_group["narrative"].tolist() if n]
            if not narrs:
                continue
            counts = pd.Series(narrs).value_counts()
            top_count = counts.iloc[0]
            tied_candidates = counts[counts == top_count].index.tolist()
            chosen = sorted(tied_candidates)[0]

            if len(set(narrs)) > 1:
                conflicts.append({
                    "claim_id": c_id,
                    "record_ids": ";".join(group["record_id"].tolist()),
                    "narratives_found": ";".join(set(narrs)),
                    "chosen_narrative": chosen,
                })
                df_final.loc[(df_final["claim_id"] == c_id) & (df_final["narrative"] != ""), "narrative"] = chosen

    conflicts_df = pd.DataFrame(conflicts)
    conflicts_path = out_dir / "claim_label_conflicts.csv"
    conflicts_df.to_csv(conflicts_path, index=False)
    if not conflicts_df.empty:
        print(f"Logged {len(conflicts_df)} claim-level label conflicts to: {conflicts_path}")

    # 6. Rare-class merge: distinct claims count < MIN_CLAIMS_PER_CLASS
    merged_classes = []
    if not df_final.empty and "narrative" in df_final.columns:
        usable_mask = (df_final["status_narrative"] != "unresolved_disagreement") & (df_final["narrative"] != "")
        claim_counts = df_final[usable_mask].groupby("narrative")["claim_id"].nunique().to_dict()

        for narr, count in claim_counts.items():
            if narr != "other" and count < MIN_CLAIMS_PER_CLASS:
                merged_classes.append((narr, count))
                mask = usable_mask & (df_final["narrative"] == narr)
                df_final.loc[mask, "narrative"] = "other"

    if merged_classes:
        print("Rare-Class Merge Notice:")
        for narr, count in merged_classes:
            print(f"  Class '{narr}' had {count} distinct claims (< {MIN_CLAIMS_PER_CLASS}); merged into 'other'.")

    # 7. Save dataset.csv
    cols_dataset = [
        "record_id",
        "claim_id",
        "claim_date",
        "text",
        "text_source",
        "script",
        "lang_group",
        "relevance",
        "narrative",
        "narrative_original",
        "content_form",
        "direction",
        "origin",
        "status_relevance",
        "status_narrative",
        "status_content_form",
        "status_direction",
        "status_origin",
        "label_status",
        "publisher_name",
        "publisher_canonical",
        "review_url",
    ]
    for c in cols_dataset:
        if c not in df_final.columns:
            if c == "publisher_canonical":
                df_final[c] = df_final.apply(lambda r: get_canonical_publisher(r.get("publisher_name"), r.get("review_url")), axis=1)
            else:
                df_final[c] = ""

    df_dataset = df_final[cols_dataset]
    dataset_path = proc_dir / "dataset.csv"
    df_dataset.to_csv(dataset_path, index=False)
    print(f"Saved finalized dataset: {dataset_path} ({len(df_dataset)} rows, {df_dataset['claim_id'].nunique()} claims)")

    print("\nFinal Status Summary per Field:")
    for fld in FIELDS:
        col = f"status_{fld}"
        counts = df_dataset[col].value_counts().to_dict()
        print(f"  {fld:<15}: {counts}")

    # 8. Write RQ1 table: content_form x narrative counted at CLAIM level
    resolved_mask = (df_dataset["content_form"] != "") & (df_dataset["narrative"] != "")
    resolved_claims_df = df_dataset[resolved_mask].drop_duplicates(subset=["claim_id"])
    total_claims = df_dataset["claim_id"].nunique()
    excluded_claims_count = total_claims - len(resolved_claims_df)
    print(f"\nRQ1 Table: counted {len(resolved_claims_df)} claims with resolved content_form ({excluded_claims_count} claims excluded due to unresolved/unlabelled content_form)")

    if not resolved_claims_df.empty:
        rq1_crosstab = pd.crosstab(
            resolved_claims_df["content_form"],
            resolved_claims_df["narrative"],
            margins=True,
        )
    else:
        rq1_crosstab = pd.DataFrame()
    rq1_path = out_dir / "rq1_form_by_narrative.csv"
    rq1_crosstab.to_csv(rq1_path)
    print(f"Saved RQ1 claim-level form x narrative table: {rq1_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 2: Build dataset and finalize labels.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("make-sheet", help="Filter claims and generate coding sheet.")
    subparsers.add_parser("finalize", help="Finalize coder labels into dataset.csv.")
    merges_p = subparsers.add_parser("apply-merges", help="Apply human confirmed claim merges.")
    merges_p.add_argument("merges_file", nargs="?", default=None, help="Path to duplicate_pairs_review.csv (optional positional)")
    merges_p.add_argument("--merges", type=str, default=None, help="Path to duplicate_pairs_review.csv")

    args = parser.parse_args()
    if args.subcommand == "make-sheet":
        run_make_sheet()
    elif args.subcommand == "finalize":
        run_finalize()
    elif args.subcommand == "apply-merges":
        merges_path = args.merges_file or args.merges
        run_apply_merges(merges_path)


if __name__ == "__main__":
    main()
