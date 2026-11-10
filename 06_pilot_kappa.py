#!/usr/bin/env python3
"""06_pilot_kappa.py - Compute inter-coder reliability on pilot coding sample.

Reads pilot labels from two independent human coders (e.g. data/raw/pilot_A.csv, data/raw/pilot_B.csv),
computes percent agreement and Cohen's kappa across coding categories (narrative, content_form, direction),
and outputs disagreements to outputs/pilot_disagreements.csv.

Note: With N=16 (or small pilot batches), Cohen's kappa is very rough, carries high sampling
variance, and should be interpreted as a qualitative check on codebook clarity rather than
a conclusive reliability benchmark.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from sklearn.metrics import cohen_kappa_score

import config
from utils import compute_label_agreement


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate pilot inter-coder agreement.")
    parser.add_argument(
        "--coder-a",
        type=str,
        default="data/raw/pilot_A.csv",
        help="Path to Coder A pilot CSV (default: data/raw/pilot_A.csv)",
    )
    parser.add_argument(
        "--coder-b",
        type=str,
        default="data/raw/pilot_B.csv",
        help="Path to Coder B pilot CSV (default: data/raw/pilot_B.csv)",
    )
    parser.add_argument(
        "--output-disagreements",
        type=str,
        default="outputs/pilot_disagreements.csv",
        help="Path to save disagreement CSV (default: outputs/pilot_disagreements.csv)",
    )
    return parser.parse_args()


def evaluate_pilot(coder_a_path: Path, coder_b_path: Path, out_disagreements_path: Path) -> dict:
    if not coder_a_path.exists():
        print(f"Error: Coder A file not found: {coder_a_path}", file=sys.stderr)
        print("Please ensure human coders complete their pilot sheets before running.")
        sys.exit(1)

    if not coder_b_path.exists():
        print(f"Error: Coder B file not found: {coder_b_path}", file=sys.stderr)
        print("Please ensure Coder B completes data/raw/pilot_B.csv.")
        sys.exit(1)

    df_a = pd.read_csv(coder_a_path)
    df_b = pd.read_csv(coder_b_path)

    if "record_id" not in df_a.columns or "record_id" not in df_b.columns:
        raise ValueError("Both pilot files must contain 'record_id' column.")

    # Merge on record_id
    merged = pd.merge(df_a, df_b, on="record_id", suffixes=("_coder_A", "_coder_B"))
    n = len(merged)

    print("=" * 60)
    print("PILOT INTER-CODER RELIABILITY ASSESSMENT")
    print("=" * 60)
    print(f"Coder A file: {coder_a_path} (n={len(df_a)})")
    print(f"Coder B file: {coder_b_path} (n={len(df_b)})")
    print(f"Overlapping evaluated records: n={n}")
    print("\nCAVEAT ON SAMPLE SIZE:")
    print(f"  Note: With n={n}, Cohen's kappa is very rough and carries high")
    print("  sampling variance. Treat these values as qualitative diagnostics")
    print("  for codebook ambiguities, not final psychometric proof.")
    print("-" * 60)

    categories = ["relevance", "narrative", "content_form", "direction", "origin"]
    results = {"n": n}

    for cat in categories:
        col_a = f"{cat}_coder_A"
        col_b = f"{cat}_coder_B"

        if col_a in merged.columns and col_b in merged.columns:
            # Drop rows where either is NaN or empty
            valid = merged[merged[col_a].notna() & merged[col_b].notna() & (merged[col_a] != "") & (merged[col_b] != "")]
            cat_n = len(valid)
            if cat_n == 0:
                print(f"{cat.upper()}: No valid labeled pairs found.")
                continue

            labels_a = valid[col_a].astype(str).str.strip().tolist()
            labels_b = valid[col_b].astype(str).str.strip().tolist()

            metrics = compute_label_agreement(labels_a, labels_b)
            kappa = metrics["cohen_kappa"]
            pct_agree = metrics["percent_agreement"]
            results[cat] = {
                "n": cat_n,
                "cohen_kappa": kappa,
                "percent_agreement": pct_agree,
            }
            print(f"{cat.upper():<15} | n={cat_n:<3} | Agree: {pct_agree:>5.1f}% | Cohen's Kappa: {kappa:>6.3f}")

    print("-" * 60)

    # Disagreements on primary narrative
    if "narrative_coder_A" in merged.columns and "narrative_coder_B" in merged.columns:
        disagreements = merged[merged["narrative_coder_A"] != merged["narrative_coder_B"]].copy()
        print(f"Narrative disagreements count: {len(disagreements)} of {n} ({len(disagreements)/n*100:.1f}%)")

        disagreements["final_adjudication"] = ""
        disagreements["team_resolution_notes"] = ""

        out_disagreements_path.parent.mkdir(parents=True, exist_ok=True)
        cols_to_save = [
            "record_id",
            "narrative_coder_A",
            "narrative_coder_B",
            "content_form_coder_A",
            "content_form_coder_B",
            "direction_coder_A",
            "direction_coder_B",
            "final_adjudication",
            "team_resolution_notes",
        ]
        available_cols = [c for c in cols_to_save if c in disagreements.columns]
        disagreements[available_cols].to_csv(out_disagreements_path, index=False)
        print(f"Disagreements written to: {out_disagreements_path}")

    return results


def main() -> None:
    args = parse_args()
    evaluate_pilot(
        Path(args.coder_a),
        Path(args.coder_b),
        Path(args.output_disagreements),
    )


if __name__ == "__main__":
    main()
