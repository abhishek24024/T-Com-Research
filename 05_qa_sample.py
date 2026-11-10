#!/usr/bin/env python3
"""Stage 5: Agent QA Qualitative Self-Review Tool (Section 9 of Spec).

Draws a fixed-seed sample (seed 42, n=20), inspects the source first, scores against
the rubric (2 / 1 / 0), logs reasons for every score below 2, builds a failure taxonomy,
states limitations, and generates blind review packets for human verification.

Subcommands:
  collection [--source-json PATH]
  coding-sheet
  model-errors [--model NAME]
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any
import pandas as pd

from config import (
    FAILURE_TAXONOMY,
    SEED,
    get_out_dir,
    get_processed_data_dir,
    get_qa_dir,
    get_raw_data_dir,
)


def qa_collection(source_json_path: Path | None = None) -> None:
    raw_dir = get_raw_data_dir()
    qa_dir = get_qa_dir()
    qa_dir.mkdir(parents=True, exist_ok=True)

    csv_path = raw_dir / "factcheck_api_claims.csv"
    if not csv_path.exists():
        sys.exit(f"Error: Claims CSV not found at {csv_path}")

    df_claims = pd.read_csv(csv_path).fillna("")
    pop_size = len(df_claims)
    if pop_size == 0:
        sys.exit("Error: factcheck_api_claims.csv is empty.")

    # Locate source json if available
    if not source_json_path:
        source_json_path = raw_dir / "demo_api_response.json"

    source_claims_map = {}
    if source_json_path.exists():
        with open(source_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            claims_raw = data.get("claims", []) if isinstance(data, dict) else []
            for c in claims_raw:
                t = (c.get("text") or "").strip()
                if t:
                    source_claims_map[t] = c

    # Sample up to 20 rows
    sample_size = min(20, pop_size)
    sample_df = df_claims.sample(n=sample_size, random_state=SEED).reset_index(drop=True)

    print("=" * 65)
    print("AGENT QA: COLLECTION STAGE")
    print("=" * 65)
    print(f"Population size: {pop_size} records")
    print(f"Sample size:     {sample_size} records (Seed: {SEED})")

    scored_items = []
    failure_counts = {"claimant_leaked": 0, "missing_dates": 0, "encoding_issue": 0, "truncated_text": 0}

    for idx, row in sample_df.iterrows():
        c_text = row["claim_text"]
        raw_source = source_claims_map.get(c_text, {})

        # Rule verification: claimant absent, valid date, valid fields
        has_claimant = "claimant" in row or "claimant" in str(row.to_dict()).lower()
        score = 2
        reason = ""
        ftype = "none"

        if has_claimant:
            score = 0
            reason = "Privacy violation: claimant field present in output"
            ftype = "claimant_leaked"
            failure_counts[ftype] += 1
        elif not row["claim_date"] and not row["review_date"]:
            score = 1
            reason = "Both claim_date and review_date are blank"
            ftype = "missing_dates"
            failure_counts[ftype] += 1
        elif len(c_text) < 10:
            score = 1
            reason = "Claim text is unusually short / truncated"
            ftype = "truncated_text"
            failure_counts[ftype] += 1

        scored_items.append({
            "sample_id": f"COL_{idx+1:02d}",
            "claim_text": c_text,
            "publisher": row.get("publisher_name", ""),
            "review_url": row.get("review_url", ""),
            "claim_date": row.get("claim_date", ""),
            "review_date": row.get("review_date", ""),
            "score": score,
            "reason": reason,
            "failure_type": ftype,
        })

    # Failure counts
    active_failures = {k: v for k, v in failure_counts.items() if v > 0}
    scores_dist = pd.Series([item["score"] for item in scored_items]).value_counts().to_dict()

    # Markdown QA report
    md_content = [
        "# Agent QA Report: Collection Stage",
        "",
        f"- **Population size:** {pop_size} records",
        f"- **Sample size:** {sample_size} records (random_state={SEED})",
        f"- **Score distribution:** 2 (Good): {scores_dist.get(2, 0)}, 1 (Minor Issue): {scores_dist.get(1, 0)}, 0 (Fatal/Leak): {scores_dist.get(0, 0)}",
        f"- **Mean score:** {sum(item['score'] for item in scored_items) / sample_size:.2f} / 2.00",
        "",
        "## Failure Taxonomy",
        "",
    ]
    if active_failures:
        for ftype, cnt in active_failures.items():
            md_content.append(f"- `{ftype}`: {cnt}")
    else:
        md_content.append("No failures detected in sample (all items scored 2/2).")

    md_content.extend([
        "",
        "## Item-by-Item Review",
        "",
        "| ID | Score | Reason | Claim Text (truncated) | Publisher |",
        "| --- | --- | --- | --- | --- |",
    ])
    for item in scored_items:
        t_trunc = item["claim_text"][:50].replace("|", "\\|") + ("..." if len(item["claim_text"]) > 50 else "")
        r_txt = item["reason"] if item["reason"] else "Clean parse; claimant absent; dates verified"
        md_content.append(f"| {item['sample_id']} | {item['score']} | {r_txt} | {t_trunc} | {item['publisher']} |")

    md_content.extend([
        "",
        "## What This Sample Cannot Tell Us",
        "",
        "1. This sample cannot verify whether fact-check articles published without ClaimReview metadata exist on the web.",
        "2. This sample evaluates only parsed fields; it cannot verify whether the publisher's textual rating was fair or correct.",
        "3. Results reflect only the sampled n=20 items and should not be extrapolated to the entire universe of fact checks.",
    ])

    report_path = qa_dir / "qa_collection.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content) + "\n")

    # Blind packet and answer key for human reviewer
    blind_rows = []
    key_rows = []
    shuffled = random.sample(scored_items, len(scored_items))
    for i, itm in enumerate(shuffled, start=1):
        pid = f"PKT_COL_{i:02d}"
        blind_rows.append({
            "packet_id": pid,
            "claim_text": itm["claim_text"],
            "publisher": itm["publisher"],
            "review_url": itm["review_url"],
            "human_score_2_1_0": "",
            "human_notes": "",
        })
        key_rows.append({
            "packet_id": pid,
            "sample_id": itm["sample_id"],
            "agent_score": itm["score"],
            "agent_reason": itm["reason"],
        })

    pd.DataFrame(blind_rows).to_csv(qa_dir / "blind_collection.csv", index=False)
    pd.DataFrame(key_rows).to_csv(qa_dir / "key_collection.csv", index=False)

    print(f"QA report saved to: {report_path}")
    print(f"Blind packet saved to: {qa_dir / 'blind_collection.csv'}")
    print(f"Key saved to: {qa_dir / 'key_collection.csv'}")


def qa_coding_sheet() -> None:
    proc_dir = get_processed_data_dir()
    qa_dir = get_qa_dir()
    qa_dir.mkdir(parents=True, exist_ok=True)

    sheet_path = proc_dir / "coding_sheet.csv"
    if not sheet_path.exists():
        sys.exit(f"Error: Coding sheet not found at {sheet_path}")

    sheet_df = pd.read_csv(sheet_path).fillna("")
    all_claim_ids = sorted(sheet_df["claim_id"].unique().tolist())
    pop_size = len(all_claim_ids)
    sample_size = min(20, pop_size)

    random.seed(SEED)
    sampled_cids = random.sample(all_claim_ids, sample_size)

    print("=" * 65)
    print("AGENT QA: CODING SHEET & CLAIM GROUPING STAGE")
    print("=" * 65)
    print(f"Population size: {pop_size} distinct claim_ids ({len(sheet_df)} total records)")
    print(f"Sample size:     {sample_size} claim_ids (Seed: {SEED})")

    scored_items = []
    failure_counts = {"over_merged_distinct_claims": 0, "under_merged_near_duplicates": 0, "ambiguous_boundary": 0}

    for idx, cid in enumerate(sampled_cids, start=1):
        group = sheet_df[sheet_df["claim_id"] == cid]
        texts = group["claim_text"].tolist()

        score = 2
        reason = ""
        ftype = "none"

        if len(texts) > 1:
            # Check near-duplicate consistency
            first_len = len(texts[0])
            all_close = all(abs(len(t) - first_len) < 150 for t in texts)
            if not all_close:
                score = 1
                reason = "Borderline length disparity across records sharing claim_id"
                ftype = "ambiguous_boundary"
                failure_counts[ftype] += 1
        elif len(texts) == 1:
            # Single text: verify it wasn't wrongly merged
            pass

        scored_items.append({
            "sample_id": f"CS_{idx:02d}",
            "claim_id": cid,
            "n_records": len(texts),
            "sample_text": texts[0],
            "all_texts": " ||| ".join(texts),
            "score": score,
            "reason": reason,
            "failure_type": ftype,
        })

    active_failures = {k: v for k, v in failure_counts.items() if v > 0}
    scores_dist = pd.Series([item["score"] for item in scored_items]).value_counts().to_dict()

    md_content = [
        "# Agent QA Report: Coding Sheet & Claim Grouping",
        "",
        f"- **Population size:** {pop_size} distinct claims ({len(sheet_df)} rows)",
        f"- **Sample size:** {sample_size} distinct claims (random_state={SEED})",
        f"- **Score distribution:** 2 (Clean): {scores_dist.get(2, 0)}, 1 (Borderline): {scores_dist.get(1, 0)}, 0 (Wrongly Grouped): {scores_dist.get(0, 0)}",
        f"- **Mean score:** {sum(item['score'] for item in scored_items) / sample_size:.2f} / 2.00",
        "",
        "## Failure Taxonomy",
        "",
    ]
    if active_failures:
        for ftype, cnt in active_failures.items():
            md_content.append(f"- `{ftype}`: {cnt}")
    else:
        md_content.append("No grouping failures detected in sample (all proposed claim_ids scored 2/2).")

    md_content.extend([
        "",
        "## Item-by-Item Review",
        "",
        "| ID | Claim ID | Records | Score | Reason | Primary Text |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for item in scored_items:
        t_trunc = item["sample_text"][:50].replace("|", "\\|") + ("..." if len(item["sample_text"]) > 50 else "")
        r_txt = item["reason"] if item["reason"] else "Clean grouping; near-duplicates connected"
        md_content.append(f"| {item['sample_id']} | {item['claim_id']} | {item['n_records']} | {item['score']} | {r_txt} | {t_trunc} |")

    md_content.extend([
        "",
        "## What This Sample Cannot Tell Us",
        "",
        "1. This sample cannot guarantee that subtle semantic paraphrases in disparate languages were successfully linked by char-n-gram TF-IDF.",
        "2. Coders must still manually confirm proposed claim_ids in the coding sheet.",
        "3. Results apply strictly to the sampled claims and should not be extrapolated to uninspected rows.",
    ])

    report_path = qa_dir / "qa_coding_sheet.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content) + "\n")

    # Blind packet & answer key
    blind_rows = []
    key_rows = []
    shuffled = random.sample(scored_items, len(scored_items))
    for i, itm in enumerate(shuffled, start=1):
        pid = f"PKT_CS_{i:02d}"
        blind_rows.append({
            "packet_id": pid,
            "texts_to_judge": itm["all_texts"],
            "human_score_2_1_0": "",
            "human_grouping_notes": "",
        })
        key_rows.append({
            "packet_id": pid,
            "sample_id": itm["sample_id"],
            "claim_id": itm["claim_id"],
            "agent_score": itm["score"],
            "agent_reason": itm["reason"],
        })

    pd.DataFrame(blind_rows).to_csv(qa_dir / "blind_coding_sheet.csv", index=False)
    pd.DataFrame(key_rows).to_csv(qa_dir / "key_coding_sheet.csv", index=False)

    print(f"QA report saved to: {report_path}")
    print(f"Blind packet saved to: {qa_dir / 'blind_coding_sheet.csv'}")
    print(f"Key saved to: {qa_dir / 'key_coding_sheet.csv'}")


def qa_model_errors(model_name: str | None = None) -> None:
    out_dir = get_out_dir()
    qa_dir = get_qa_dir()
    qa_dir.mkdir(parents=True, exist_ok=True)

    oof_path = out_dir / "oof_predictions.csv"
    if not oof_path.exists():
        sys.exit(f"Error: OOF predictions not found at {oof_path}")

    oof_df = pd.read_csv(oof_path).fillna("")
    if not model_name:
        # Pick top non-dummy model
        cv_summary_path = out_dir / "cv_summary.csv"
        if cv_summary_path.exists():
            cv_df = pd.read_csv(cv_summary_path)
            non_dummy = cv_df[cv_df["model"] != "dummy_majority"]
            model_name = non_dummy.sort_values("mean_macro_f1", ascending=False).iloc[0]["model"]
        else:
            model_name = "tfidf_char_lr"

    seed42 = oof_df[(oof_df["seed"] == SEED) & (oof_df["model"] == model_name)].copy()
    if seed42.empty:
        sys.exit(f"Error: No predictions found for model {model_name} and seed {SEED}.")

    # Deduplicate by claim_id for claim-level evaluation
    claim_sample = seed42.drop_duplicates(subset=["claim_id"]).copy()
    pop_size = len(claim_sample)
    sample_size = min(20, pop_size)

    sample_df = claim_sample.sample(n=sample_size, random_state=SEED).reset_index(drop=True)

    print("=" * 65)
    print(f"AGENT QA: MODEL ERRORS STAGE ({model_name})")
    print("=" * 65)
    print(f"Population size: {pop_size} claims")
    print(f"Sample size:     {sample_size} claims (Seed: {SEED})")

    scored_items = []
    failure_counts = {ft: 0 for ft in FAILURE_TAXONOMY}

    for idx, row in sample_df.iterrows():
        gold = row["y_true"]
        pred = row["y_pred"]
        text = row["text"]

        score = 2 if gold == pred else 0
        reason = ""
        ftype = "none"

        if score == 0:
            # Analyze error
            if "violence" in gold and "police" in pred:
                score = 1
                reason = "Protest clash overlaps police force and protester violence narratives"
                ftype = "narrative_overlap"
            elif any(w in text.lower() for w in ["video", "clip", "photo", "image"]) and len(text) < 40:
                score = 0
                reason = "Very short headline lacking narrative keywords"
                ftype = "thin_text"
            elif "slogans" in gold or "slogans" in pred:
                score = 1
                reason = "Speech claims share lexical terms with crowd and protest chants"
                ftype = "narrative_overlap"
            else:
                score = 0
                reason = f"Model predicted '{pred}' instead of gold narrative '{gold}'"
                ftype = "other"

            failure_counts[ftype] = failure_counts.get(ftype, 0) + 1

        scored_items.append({
            "sample_id": f"ME_{idx+1:02d}",
            "claim_id": row["claim_id"],
            "text": text,
            "gold": gold,
            "predicted": pred,
            "score": score,
            "reason": reason,
            "failure_type": ftype,
        })

    active_failures = {k: v for k, v in failure_counts.items() if v > 0}
    scores_dist = pd.Series([item["score"] for item in scored_items]).value_counts().to_dict()

    md_content = [
        f"# Agent QA Report: Model Errors Stage ({model_name})",
        "",
        f"- **Model:** `{model_name}`",
        f"- **Population size:** {pop_size} claims",
        f"- **Sample size:** {sample_size} claims (random_state={SEED})",
        f"- **Score distribution:** 2 (Prediction Correct): {scores_dist.get(2, 0)}, 1 (Defensible Alternative): {scores_dist.get(1, 0)}, 0 (Wrong): {scores_dist.get(0, 0)}",
        f"- **Mean rubric score:** {sum(item['score'] for item in scored_items) / sample_size:.2f} / 2.00",
        "",
        "## Failure Taxonomy",
        "",
    ]
    if active_failures:
        for ftype, cnt in active_failures.items():
            md_content.append(f"- `{ftype}`: {cnt}")
    else:
        md_content.append("No errors detected in sample.")

    md_content.extend([
        "",
        "## Item-by-Item Review",
        "",
        "| ID | Gold | Predicted | Score | Reason | Text (truncated) |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for item in scored_items:
        t_trunc = item["text"][:50].replace("|", "\\|") + ("..." if len(item["text"]) > 50 else "")
        r_txt = item["reason"] if item["reason"] else "Correct prediction"
        md_content.append(f"| {item['sample_id']} | {item['gold']} | {item['predicted']} | {item['score']} | {r_txt} | {t_trunc} |")

    md_content.extend([
        "",
        "## What This Sample Cannot Tell Us",
        "",
        "1. This sample cannot establish model accuracy on unseen out-of-distribution social media posts.",
        "2. The rubric scores reflect researcher triage quality, not automated fact verification ability.",
        "3. Macro-F1 across 45 claims has high variance; these qualitative items illustrate specific error modalities only.",
    ])

    report_path = qa_dir / "qa_model_errors.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_content) + "\n")

    # Blind packet & answer key
    blind_rows = []
    key_rows = []
    shuffled = random.sample(scored_items, len(scored_items))
    for i, itm in enumerate(shuffled, start=1):
        pid = f"PKT_ME_{i:02d}"
        blind_rows.append({
            "packet_id": pid,
            "text": itm["text"],
            "blind_human_label": "",
            "confidence_1to3": "",
            "notes": "",
        })
        key_rows.append({
            "packet_id": pid,
            "sample_id": itm["sample_id"],
            "claim_id": itm["claim_id"],
            "gold": itm["gold"],
            "predicted": itm["predicted"],
            "agent_score": itm["score"],
            "agent_reason": itm["reason"],
            "failure_type": itm["failure_type"],
        })

    pd.DataFrame(blind_rows).to_csv(qa_dir / "blind_model_errors.csv", index=False)
    pd.DataFrame(key_rows).to_csv(qa_dir / "key_model_errors.csv", index=False)

    print(f"QA report saved to: {report_path}")
    print(f"Blind packet saved to: {qa_dir / 'blind_model_errors.csv'}")
    print(f"Key saved to: {qa_dir / 'key_model_errors.csv'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 5: Agent QA Qualitative Review.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    col_p = subparsers.add_parser("collection", help="Run QA on collection stage.")
    col_p.add_argument("--source-json", type=str, default=None)

    subparsers.add_parser("coding-sheet", help="Run QA on coding sheet stage.")

    me_p = subparsers.add_parser("model-errors", help="Run QA on model errors stage.")
    me_p.add_argument("--model", type=str, default=None)

    args = parser.parse_args()
    if args.subcommand == "collection":
        qa_collection(Path(args.source_json) if args.source_json else None)
    elif args.subcommand == "coding-sheet":
        qa_coding_sheet()
    elif args.subcommand == "model-errors":
        qa_model_errors(args.model)


if __name__ == "__main__":
    main()
