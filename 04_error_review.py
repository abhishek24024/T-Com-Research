#!/usr/bin/env python3
"""Stage 4: Prepare human error review packet and score blind reviews.

Subcommands:
  make [--model NAME]: Generates review_sheet.csv, blind_packet.csv, answer_key.csv, and review_meta.json.
  score-blind PATH: Scores a completed blind packet against answer_key.csv.
  summarize PATH: Summarizes review_sheet.csv ratings, reasons, and failure taxonomy.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any
import pandas as pd
from sklearn.metrics import cohen_kappa_score

from config import (
    FAILURE_TAXONOMY,
    NARRATIVES,
    REVIEW_N,
    REVIEW_SAMPLE_SEED,
    SEED,
    get_out_dir,
    get_review_dir,
)

SHEET_HEADER_INSTRUCTIONS = (
    "# REVIEW INSTRUCTIONS:\n"
    "# 1. Read the source fact-check report at review_url BEFORE looking at gold or predicted labels.\n"
    "# 2. Rubric: 2 = prediction correct; 1 = defensible alternative; 0 = wrong.\n"
    "# 3. Every row scored 0 or 1 MUST include a one-line reason and a valid failure_type from:\n"
    f"#    {', '.join(FAILURE_TAXONOMY)}\n"
)


def run_make(model_name: str | None = None) -> None:
    out_dir = get_out_dir()
    review_dir = get_review_dir()
    review_dir.mkdir(parents=True, exist_ok=True)

    cv_summary_path = out_dir / "cv_summary.csv"
    oof_path = out_dir / "oof_predictions.csv"

    if not cv_summary_path.exists() or not oof_path.exists():
        sys.exit(f"Error: Missing CV outputs. Run Stage 3 first. Checked {cv_summary_path} and {oof_path}.")

    cv_summary = pd.read_csv(cv_summary_path)
    oof_df = pd.read_csv(oof_path)

    # Select model
    if not model_name:
        non_dummy = cv_summary[cv_summary["model"] != "dummy_majority"]
        if non_dummy.empty:
            model_name = cv_summary.iloc[0]["model"]
        else:
            model_name = non_dummy.sort_values("mean_macro_f1", ascending=False).iloc[0]["model"]

    print(f"Generating error review packet for model: {model_name}")

    # Use first CV seed (seed 42)
    seed42_oof = oof_df[(oof_df["seed"] == SEED) & (oof_df["model"] == model_name)].copy()
    if seed42_oof.empty:
        sys.exit(f"Error: No OOF predictions found for seed {SEED} and model '{model_name}'.")

    # Sample at claim level: pick one random record per claim
    random.seed(REVIEW_SAMPLE_SEED)
    claim_groups = seed42_oof.groupby("claim_id")
    sampled_indices = []
    for _, group in claim_groups:
        idx = random.choice(group.index.tolist())
        sampled_indices.append(idx)

    claims_df = seed42_oof.loc[sampled_indices].copy()
    claims_df["is_error"] = claims_df["y_true"] != claims_df["y_pred"]

    errors_df = claims_df[claims_df["is_error"]]
    correct_df = claims_df[~claims_df["is_error"]]

    n_errors_avail = len(errors_df)
    n_correct_avail = len(correct_df)
    total_avail = len(claims_df)

    # Target: half errors, half correct up to REVIEW_N
    target_half = REVIEW_N // 2
    n_err_sample = min(target_half, n_errors_avail)
    n_corr_sample = min(REVIEW_N - n_err_sample, n_correct_avail)

    # If correct was short, top up with errors if available
    if n_err_sample + n_corr_sample < REVIEW_N and n_errors_avail > n_err_sample:
        top_up = min(REVIEW_N - (n_err_sample + n_corr_sample), n_errors_avail - n_err_sample)
        n_err_sample += top_up

    # Sample rows
    selected_errors = errors_df.sample(n=n_err_sample, random_state=REVIEW_SAMPLE_SEED) if n_err_sample > 0 else pd.DataFrame()
    selected_correct = correct_df.sample(n=n_corr_sample, random_state=REVIEW_SAMPLE_SEED) if n_corr_sample > 0 else pd.DataFrame()

    review_sample = pd.concat([selected_errors, selected_correct], ignore_index=True)

    # Load review_urls from dataset.csv or coding_sheet.csv
    proc_dir = out_dir.parent / "data" / "processed" if "scratch" not in str(out_dir) else out_dir.parent / "processed"
    if not proc_dir.exists():
        proc_dir = out_dir.parent / "demo_data" / "processed"

    dataset_path = proc_dir / "dataset.csv"
    review_url_map = {}
    if dataset_path.exists():
        ds = pd.read_csv(dataset_path)
        for _, r in ds.iterrows():
            review_url_map[r["record_id"]] = r.get("review_url", "")

    review_sample["review_url"] = review_sample["record_id"].map(lambda x: review_url_map.get(x, ""))
    review_sample["gold"] = review_sample["y_true"]
    review_sample["predicted"] = review_sample["y_pred"]
    review_sample["rubric_score"] = ""
    review_sample["reason"] = ""
    review_sample["failure_type"] = ""

    # Column order matters: text and URL come BEFORE gold and predicted
    cols_review_sheet = [
        "record_id",
        "claim_id",
        "review_url",
        "text",
        "gold",
        "predicted",
        "rubric_score",
        "reason",
        "failure_type",
    ]
    review_sheet_df = review_sample[cols_review_sheet]

    # Save review_sheet.csv
    sheet_path = review_dir / "review_sheet.csv"
    with open(sheet_path, "w", encoding="utf-8") as f:
        f.write(SHEET_HEADER_INSTRUCTIONS)
        review_sheet_df.to_csv(f, index=False)

    # Create shuffled blind packet (packet_id, review_url, text, blind_label, confidence_1to3, notes)
    # Must contain NO gold, NO predicted, NO record_id
    blind_sample = review_sample.sample(frac=1.0, random_state=REVIEW_SAMPLE_SEED).reset_index(drop=True)
    blind_sample["packet_id"] = [f"B{i+1:02d}" for i in range(len(blind_sample))]
    blind_sample["blind_label"] = ""
    blind_sample["confidence_1to3"] = ""
    blind_sample["notes"] = ""

    cols_blind = ["packet_id", "review_url", "text", "blind_label", "confidence_1to3", "notes"]
    blind_df = blind_sample[cols_blind]
    blind_path = review_dir / "blind_packet.csv"
    blind_df.to_csv(blind_path, index=False)

    # Answer key
    key_df = blind_sample[["packet_id", "record_id", "gold", "predicted"]]
    key_path = review_dir / "answer_key.csv"
    key_df.to_csv(key_path, index=False)

    # Save metadata
    meta = {
        "model": model_name,
        "cv_seed_used": SEED,
        "sample_seed": REVIEW_SAMPLE_SEED,
        "claims_available": total_avail,
        "errors_available": n_errors_avail,
        "correct_available": n_correct_avail,
        "n_sampled_errors": n_err_sample,
        "n_sampled_correct": n_corr_sample,
        "total_sampled": len(review_sample),
        "taxonomy": FAILURE_TAXONOMY,
        "allowed_labels": NARRATIVES,
        "sampling_note": (
            "The sample is deliberately enriched for errors; "
            "its accuracy is NOT the model's accuracy."
        ),
    }
    meta_path = review_dir / "review_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    print(f"\nReview packet generated successfully in: {review_dir}")
    print(f"  Claims available: {total_avail} (Errors: {n_errors_avail}, Correct: {n_correct_avail})")
    print(f"  Sampled: {len(review_sample)} items ({n_err_sample} errors, {n_corr_sample} correct)")
    print(f"  NOTE: {meta['sampling_note']}")
    print(f"  Files written: review_sheet.csv, blind_packet.csv, answer_key.csv, review_meta.json")


def run_score_blind(packet_path_str: str) -> None:
    packet_path = Path(packet_path_str)
    if not packet_path.exists():
        sys.exit(f"Error: Packet file not found: {packet_path}")

    review_dir = packet_path.parent
    key_path = review_dir / "answer_key.csv"
    if not key_path.exists():
        sys.exit(f"Error: Answer key not found: {key_path}")

    packet = pd.read_csv(packet_path).fillna("")
    key = pd.read_csv(key_path).fillna("")

    merged = pd.merge(packet, key, on="packet_id")
    labelled = merged[merged["blind_label"].str.strip() != ""]
    n_labelled = len(labelled)

    if n_labelled == 0:
        sys.exit("Error: No completed blind labels found in packet.")

    # Check for invalid labels
    invalid = set(labelled["blind_label"].unique()) - set(NARRATIVES)
    if invalid:
        print(f"WARNING: Invalid narrative labels found in blind packet: {invalid}")

    blind_labels = labelled["blind_label"].tolist()
    gold_labels = labelled["gold"].tolist()
    pred_labels = labelled["predicted"].tolist()

    blind_gold_matches = sum(1 for b, g in zip(blind_labels, gold_labels) if b == g)
    blind_pred_matches = sum(1 for b, p in zip(blind_labels, pred_labels) if b == p)
    pred_gold_matches = sum(1 for p, g in zip(pred_labels, gold_labels) if p == g)

    pct_blind_gold = (blind_gold_matches / n_labelled) * 100.0
    pct_blind_pred = (blind_pred_matches / n_labelled) * 100.0
    pct_pred_gold = (pred_gold_matches / n_labelled) * 100.0

    try:
        kappa_blind_gold = float(cohen_kappa_score(blind_labels, gold_labels))
    except Exception:
        kappa_blind_gold = 0.0

    print("=" * 65)
    print("BLIND REVIEW SCORING REPORT")
    print("=" * 65)
    print(f"Total items labelled: {n_labelled} / {len(merged)}")
    print(f"Blind vs Gold Agreement:  {blind_gold_matches}/{n_labelled} ({pct_blind_gold:.2f}%)")
    print(f"Blind vs Model Agreement: {blind_pred_matches}/{n_labelled} ({pct_blind_pred:.2f}%)")
    print(f"Model vs Gold Agreement:  {pred_gold_matches}/{n_labelled} ({pct_pred_gold:.2f}%)")
    print(f"Cohen's Kappa (Blind vs Gold): {kappa_blind_gold:.4f}")
    print("\nREADING GUIDE:")
    print("  - If blind matches model but both differ from gold, suspect the gold label.")
    print("  - If blind matches gold but the model differs, it is a model error.")
    print("  - Small n means describe errors qualitatively; do not generalise.")
    print("=" * 65)


def run_summarize(sheet_path_str: str) -> None:
    sheet_path = Path(sheet_path_str)
    if not sheet_path.exists():
        sys.exit(f"Error: Review sheet not found: {sheet_path}")

    # Read review sheet, ignoring comment lines starting with #
    df = pd.read_csv(sheet_path, comment="#").fillna("")
    if df.empty:
        sys.exit("Error: Review sheet is empty.")

    # Filter reviewed rows (rubric_score is not empty)
    reviewed = df[df["rubric_score"].astype(str).str.strip() != ""].copy()
    n_rev = len(reviewed)

    if n_rev == 0:
        sys.exit("Error: No reviewed rows found (rubric_score column is blank).")

    reviewed["rubric_score"] = pd.to_numeric(reviewed["rubric_score"], errors="coerce")
    score_counts = reviewed["rubric_score"].value_counts().to_dict()
    mean_score = reviewed["rubric_score"].mean()

    # Low scores: 0 or 1
    low_scores = reviewed[reviewed["rubric_score"].isin([0, 1])]
    failure_counts = low_scores["failure_type"].value_counts().to_dict()

    # Missing reason or failure type
    missing_info = []
    for _, r in low_scores.iterrows():
        reason = str(r["reason"]).strip()
        ftype = str(r["failure_type"]).strip()
        if not reason or not ftype or ftype not in FAILURE_TAXONOMY:
            missing_info.append(r["record_id"])

    print("=" * 65)
    print("REVIEW SHEET SUMMARY")
    print("=" * 65)
    print(f"Total rows reviewed: {n_rev} / {len(df)}")
    print(f"Score breakdown: 2: {score_counts.get(2, 0)}, 1: {score_counts.get(1, 0)}, 0: {score_counts.get(0, 0)}")
    print(f"Mean rubric score: {mean_score:.2f} / 2.00")
    print("\nFailure taxonomy among low scores (0 or 1):")
    for ftype in FAILURE_TAXONOMY:
        print(f"  {ftype}: {failure_counts.get(ftype, 0)}")

    if missing_info:
        print(f"\nWARNING: {len(missing_info)} low-score row(s) missing valid reason or failure type: {missing_info}")
    else:
        print("\nAll low-score rows include a valid reason and taxonomy label.")
    print("=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 4: Qualitative error review tools.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    make_p = subparsers.add_parser("make", help="Create review sheet, blind packet, and answer key.")
    make_p.add_argument("--model", type=str, default=None, help="Model name to sample errors from.")

    score_p = subparsers.add_parser("score-blind", help="Score completed blind packet.")
    score_p.add_argument("path", type=str, help="Path to completed blind_packet.csv.")

    sum_p = subparsers.add_parser("summarize", help="Summarize reviewed review_sheet.csv.")
    sum_p.add_argument("path", type=str, help="Path to reviewed review_sheet.csv.")

    args = parser.parse_args()
    if args.subcommand == "make":
        run_make(args.model)
    elif args.subcommand == "score-blind":
        run_score_blind(args.path)
    elif args.subcommand == "summarize":
        run_summarize(args.path)


if __name__ == "__main__":
    main()
