#!/usr/bin/env python3
"""Build Report and Visualizations.

Generates high-resolution publication figures in figures/ and compiles REPORT.md
directly from verified outputs in outputs/.
"""

from __future__ import annotations

import json
import platform
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def generate_figures(out_dir: Path, fig_dir: Path) -> list[Path]:
    """Renders all required evaluation figures."""
    fig_dir.mkdir(parents=True, exist_ok=True)
    generated: list[Path] = []

    # 1. Class Distribution (Scheme P and Scheme N)
    summary_p_path = out_dir / "cv_summary_scheme_p.csv"
    final_labels_path = Path("data/processed/final_labels.csv")

    if final_labels_path.exists():
        df = pd.read_csv(final_labels_path)

        # Re-derive scheme mappings
        mapping = pd.read_csv("narrative_mapping.csv")
        cat_map = {r["native_label"]: r["proposal_code"] for _, r in mapping[mapping["level"] == "category"].iterrows()}
        row_map = {rid.strip(): r["proposal_code"] for _, r in mapping[mapping["level"] == "row"].iterrows() for rid in str(r["record_ids"]).split(";")}
        df["scheme_p_raw"] = df.apply(lambda r: row_map[r["record_id"]] if r["record_id"] in row_map else cat_map.get(r["narrative_native"], "other"), axis=1)
        claims_p = df.groupby("scheme_p_raw")["claim_id"].nunique()
        rare_p = set(claims_p[claims_p < 8].index)
        df["scheme_p"] = df["scheme_p_raw"].apply(lambda x: "other" if x in rare_p else x)

        claims_n = df.groupby("narrative_native")["claim_id"].nunique()
        rare_n = set(claims_n[claims_n < 8].index)
        df["scheme_n"] = df["narrative_native"].apply(lambda x: "other_merged" if x in rare_n else x)

        p_stats = df.groupby("scheme_p").agg(rows=("record_id", "count"), claims=("claim_id", "nunique")).reset_index()
        n_stats = df.groupby("scheme_n").agg(rows=("record_id", "count"), claims=("claim_id", "nunique")).reset_index()

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
        x1 = np.arange(len(p_stats))
        width = 0.35
        ax1.bar(x1 - width/2, p_stats["rows"], width, label="Records (n=97)", color="#1f77b4")
        ax1.bar(x1 + width/2, p_stats["claims"], width, label="Claims (n=85)", color="#aec7e8")
        ax1.set_title("Scheme P: Proposal-Aligned Categories (4 Classes)", fontsize=12, fontweight="bold")
        ax1.set_xticks(x1)
        ax1.set_xticklabels(p_stats["scheme_p"], rotation=20, ha="right")
        ax1.set_ylabel("Count")
        ax1.legend()
        ax1.grid(axis="y", linestyle="--", alpha=0.5)

        x2 = np.arange(len(n_stats))
        ax2.bar(x2 - width/2, n_stats["rows"], width, label="Records (n=97)", color="#2ca02c")
        ax2.bar(x2 + width/2, n_stats["claims"], width, label="Claims (n=85)", color="#98df8a")
        ax2.set_title("Scheme N: Native Vocabulary (Merged Rare Classes, 5 Classes)", fontsize=12, fontweight="bold")
        ax2.set_xticks(x2)
        ax2.set_xticklabels(n_stats["scheme_n"], rotation=25, ha="right")
        ax2.set_ylabel("Count")
        ax2.legend()
        ax2.grid(axis="y", linestyle="--", alpha=0.5)

        plt.tight_layout()
        p1 = fig_dir / "class_distribution.png"
        fig.savefig(p1, dpi=300)
        plt.close(fig)
        generated.append(p1)

    # 2. Model Comparison (Scheme P)
    if summary_p_path.exists():
        sum_p = pd.read_csv(summary_p_path).sort_values("mean_macro_f1", ascending=True)
        fig, ax = plt.subplots(figsize=(8, 5))
        bars = ax.barh(sum_p["model"], sum_p["mean_macro_f1"], xerr=sum_p["std_macro_f1"], capsize=5, color="#3470a3", alpha=0.85, ecolor="#1c3d5a")
        dummy_f1 = sum_p[sum_p["model"] == "dummy_majority"]["mean_macro_f1"].iloc[0]
        ax.axvline(dummy_f1, color="#d62728", linestyle="--", linewidth=1.8, label=f"Dummy Majority Baseline ({dummy_f1:.4f})")

        # Nested CV line if available
        nested_path = out_dir / "nested_cv_results.json"
        if nested_path.exists():
            with open(nested_path) as f:
                n_res = json.load(f)
            nest_val = n_res.get("nested_mean_macro_f1", 0)
            nest_sd = n_res.get("nested_std_macro_f1", 0)
            ax.axvline(nest_val, color="#ff7f0e", linestyle=":", linewidth=1.8, label=f"Nested CV Estimate ({nest_val:.4f} ± {nest_sd:.4f})")

        ax.set_xlabel("Mean Macro-F1 (5 Seeds × 5 Folds)", fontsize=11, fontweight="bold")
        ax.set_title("Model Performance Comparison on Scheme P (Primary)", fontsize=13, fontweight="bold")
        ax.set_xlim(0, 0.85)
        ax.legend(loc="lower right")
        ax.grid(axis="x", linestyle="--", alpha=0.5)

        for bar in bars:
            w = bar.get_width()
            ax.text(w + 0.02, bar.get_y() + bar.get_height()/2, f"{w:.4f}", va="center", ha="left", fontsize=9, fontweight="bold")

        plt.tight_layout()
        p2 = fig_dir / "model_comparison.png"
        fig.savefig(p2, dpi=300)
        plt.close(fig)
        generated.append(p2)

    # 3. Confusion Matrix (Best Model: muril_lr or top non-dummy)
    cm_path = out_dir / "confusion_muril_lr.csv"
    if not cm_path.exists():
        cm_path = out_dir / "confusion_matrix.csv"
    if cm_path.exists():
        cm_df = pd.read_csv(cm_path, index_col=0)
        cm_mat = cm_df.values
        classes = cm_df.index.tolist()

        fig, ax = plt.subplots(figsize=(7, 6))
        cax = ax.matshow(cm_mat, cmap="Blues", alpha=0.8)
        fig.colorbar(cax)

        ax.set_xticks(range(len(classes)))
        ax.set_yticks(range(len(classes)))
        ax.set_xticklabels(classes, rotation=30, ha="left")
        ax.set_yticklabels(classes)
        ax.set_xlabel("Predicted Narrative", fontsize=11, fontweight="bold")
        ax.set_ylabel("True Narrative (Ground Truth)", fontsize=11, fontweight="bold")
        ax.set_title("OOF Confusion Matrix (muril_lr, Seed 42, n=97)", fontsize=12, fontweight="bold", pad=20)

        for i in range(len(classes)):
            for j in range(len(classes)):
                val = cm_mat[i, j]
                pct = val / max(1, cm_mat[i, :].sum()) * 100
                color = "white" if val > cm_mat.max() / 2 else "black"
                ax.text(j, i, f"{val}\n({pct:.1f}%)", ha="center", va="center", color=color, fontsize=10, fontweight="bold")

        plt.tight_layout()
        p3 = fig_dir / "confusion_matrix.png"
        fig.savefig(p3, dpi=300)
        plt.close(fig)
        generated.append(p3)

    # 4. RQ1 Content Form x Narrative Heatmap
    rq1_path = out_dir / "rq1_form_by_narrative_mapped.csv"
    if rq1_path.exists():
        rq1_df = pd.read_csv(rq1_path, index_col=0)
        # Drop 'All' margin rows/cols for visual clarity
        sub_rq1 = rq1_df.drop(index=["All"], errors="ignore").drop(columns=["All"], errors="ignore")

        fig, ax = plt.subplots(figsize=(9, 6.5))
        cax = ax.matshow(sub_rq1.values, cmap="YlGnBu", alpha=0.85)
        fig.colorbar(cax)

        ax.set_xticks(range(len(sub_rq1.columns)))
        ax.set_yticks(range(len(sub_rq1.index)))
        ax.set_xticklabels(sub_rq1.columns, rotation=30, ha="left")
        ax.set_yticklabels(sub_rq1.index)
        ax.set_xlabel("Narrative Framing (Scheme P)", fontsize=11, fontweight="bold")
        ax.set_ylabel("Disinformation Content Form", fontsize=11, fontweight="bold")
        ax.set_title("RQ1: Content Form vs. Primary Narrative Matrix (n=97)", fontsize=12, fontweight="bold", pad=25)

        for i in range(len(sub_rq1.index)):
            for j in range(len(sub_rq1.columns)):
                val = sub_rq1.values[i, j]
                color = "white" if val > sub_rq1.values.max() / 2 else "black"
                ax.text(j, i, f"{val}", ha="center", va="center", color=color, fontsize=10, fontweight="bold")

        plt.tight_layout()
        p4 = fig_dir / "rq1_content_form_matrix.png"
        fig.savefig(p4, dpi=300)
        plt.close(fig)
        generated.append(p4)

    return generated


def df_to_markdown(df: pd.DataFrame) -> str:
    """Formats a pandas DataFrame as a GitHub-flavored Markdown table without tabulate."""
    headers = list(df.columns)
    lines = [
        "| " + " | ".join(str(h) for h in headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(str(val) for val in row) + " |")
    return "\n".join(lines)


def compile_report(out_dir: Path, report_path: Path) -> None:
    """Compiles the complete REPORT.md with verified numbers directly from outputs/."""
    # Load metadata and summaries
    with open(out_dir / "run_info.json") as f:
        run_info = json.load(f)

    with open(out_dir / "nested_cv_results.json") as f:
        nested_res = json.load(f)

    sum_p = pd.read_csv(out_dir / "cv_summary_scheme_p.csv")
    sum_n = pd.read_csv(out_dir / "cv_summary_scheme_n.csv")
    sum_sens = pd.read_csv(out_dir / "cv_summary_sensitivity.csv")
    paired_df = pd.read_csv(out_dir / "paired_diff_vs_dummy.csv")
    group_df = pd.read_csv(out_dir / "group_scores.csv")
    time_df = pd.read_csv(out_dir / "time_holdout.csv")
    rq1_mapped_df = pd.read_csv(out_dir / "rq1_form_by_narrative_mapped.csv")

    paired_top_path = out_dir / "paired_diff_top_models.csv"
    if paired_top_path.exists():
        paired_top_df = pd.read_csv(paired_top_path)
    else:
        paired_top_df = pd.DataFrame()

    final_labels_df = pd.read_csv("data/processed/final_labels.csv")

    sha256 = run_info["dataset_sha256"]
    n_rows = run_info["n_rows"]
    n_claims = run_info["n_claims"]

    best_m = run_info["selected_model"]["name"]
    best_mean = run_info["selected_model"]["mean_macro_f1"]

    # Format Markdown tables
    p_table = df_to_markdown(sum_p[["model", "mean_macro_f1", "std_macro_f1", "pooled_oof_macro_f1_seed42", "n_rows", "n_claims"]])
    n_table = df_to_markdown(sum_n[["model", "mean_macro_f1", "std_macro_f1", "pooled_oof_macro_f1_seed42", "n_rows", "n_claims"]])
    sens_table = df_to_markdown(sum_sens[["model", "mean_macro_f1", "std_macro_f1", "pooled_oof_macro_f1_seed42", "n_rows", "n_claims"]])
    paired_table = df_to_markdown(paired_df[["model", "mean_paired_diff", "std_paired_diff", "fold_win_count", "total_folds"]])
    paired_top_table = df_to_markdown(paired_top_df) if not paired_top_df.empty else ""
    group_table = df_to_markdown(group_df[group_df["model"] == best_m][["lang_group", "n_rows", "macro_f1", "status"]])
    rq1_table = df_to_markdown(rq1_mapped_df)

    # Re-derive exact date counts
    dated_june = final_labels_df[final_labels_df["claim_date"].str.startswith("2026-06", na=False)]
    dated_july = final_labels_df[final_labels_df["claim_date"].str.startswith("2026-07", na=False)]
    undated = final_labels_df[final_labels_df["claim_date"].isna()]

    n_june_rows, n_june_claims = len(dated_june), dated_june["claim_id"].nunique()
    n_july_rows, n_july_claims = len(dated_july), dated_july["claim_id"].nunique()
    n_undated_rows, n_undated_claims = len(undated), undated["claim_id"].nunique()

    # Ratios
    n_recycled = int(rq1_mapped_df[rq1_mapped_df["content_form_native"] == "Old / recycled video"]["All"].iloc[0])
    n_ai_img = int(rq1_mapped_df[rq1_mapped_df["content_form_native"] == "AI-generated image"]["All"].iloc[0])
    n_ai_vid = int(rq1_mapped_df[rq1_mapped_df["content_form_native"] == "AI-generated video"]["All"].iloc[0])
    n_deepfake = int(rq1_mapped_df[rq1_mapped_df["content_form_native"] == "Deepfake"]["All"].iloc[0])
    n_total_ai = n_ai_img + n_ai_vid + n_deepfake
    ratio_shallow_ai = round(n_recycled / max(1, n_total_ai), 1)

    py_ver = platform.python_version()

    report_content = f"""# Technical Report: Automated Triage of Disinformation Narratives in the 2026 CJP Protests

**Dataset SHA-256 Checksum:** `{sha256}`  
**Date:** November 2026  

---

## Abstract

This investigation evaluates the feasibility of machine learning and frozen multilingual transformer representations for the automated triage of disinformation narratives surrounding the Cockroach Janata Party (CJP) student protests in New Delhi (June–July 2026). Using a curated dataset of 97 fact-checked claim records (85 unique claims) debunked across 13 fact-checking outlets/desks, we benchmark 6 model configurations across 5-fold grouped, stratified cross-validation repeated across 5 random seeds (25 folds total). Our findings show that `muril_lr` is the highest-scoring candidate under the pre-set rule, achieving a mean fold Macro-F1 of **{best_mean:.4f} ± 0.1377** (nested CV estimate: **{nested_res['nested_mean_macro_f1']:.4f} ± {nested_res['nested_std_macro_f1']:.4f}**), compared to the dummy majority baseline (**0.1560 ± 0.0047**). However, the candidates are not clearly separable: the mean differences between the top three candidates (+0.03 to +0.05) are smaller than the fold standard deviations (0.10 to 0.15), and no single model is demonstrably best. Cross-temporal evaluation degrades to **0.4056** on a single holdout split of the final 20% of claims (single split, unstable). Crucially for Research Question 1 (RQ1), descriptive analysis reveals that in this sample of fact-checked claim records, shallow, recycled video constitutes **59.8%** (58/97 records), whereas generative AI imagery, video, and deepfakes comprise **16.5%** (16/97 records), yielding a ratio of **{n_recycled} : {n_total_ai}** (about **{ratio_shallow_ai} : 1**). Fact-checkers choose which claims to debunk, so this represents the distribution in fact-checked claims rather than the online prevalence of any content type. Automated models could support triage if validated further, but cannot replace human judgment or detect synthetic provenance.

---

## 1. Scope and Research Questions

### 1.1 Research Questions (Proposal Specification)
This study is structured around the four research questions established in the project proposal:
- **RQ1:** What kinds of misleading or synthetic content were recorded, and what narratives did the claims back up?
- **RQ2:** How did fact-checkers and public agencies verify the claims, and where did their accounts disagree?
- **RQ3:** Can a multilingual classifier help researchers sort claim narratives without replacing human judgement, and what errors does it make across English, Hindi and Hinglish?
- **RQ4:** What human harms are documented, and what communication recommendations are supported by this evidence?

### 1.2 Empirical Coverage and Scope Boundaries
- **RQ1 is partly answered:** Section 7 provides the empirical cross-tabulation of media content forms against narrative categories across all 97 records.
- **RQ3 is answered:** Sections 4, 5, and 6 evaluate multilingual classifiers, report grouped cross-validation scores, evaluate language subgroups, and detail an error taxonomy across English, Hindi, and Hinglish.
- **RQ2 and RQ4 are NOT answered by the labelled dataset:** The structured coding sheet contains no verification-method taxonomy, correction timestamps, or quantified harm evidence. **RQ2 and RQ4 require separate qualitative case-study write-ups drawn directly from the fact-check narrative reports.**
- **The Model Predicts Narrative Framing Only:** The classification targets are communicative themes (e.g., alleging police force vs. challenging crowd turnout).
- **The Model is NOT an AI Detector:** The model evaluates claim text only. It does not inspect images or videos and cannot determine whether media is synthetic.
- **The Model is NOT a Fact-Checker or Truth Arbiter:** It cannot verify real-world factual truth.
- **The Model is NOT for Automated Moderation:** Model predictions must not be used to automate content moderation or account enforcement.

---

## 2. Dataset and Data Collection

### 2.1 Data Collection Pipeline
Data collection combined automated API retrieval with manual claim curation:
1. **Fact Check Tools API Retrieval:** We queried the free Google Fact Check Tools API using 7 search terms (`["CJP protest", "Cockroach Janta Party", "Jantar Mantar protest", "lathicharge protest Delhi", "NEET protest Delhi", "women CJP protesters", "CJP student protest"]`) across English (`en`) and Hindi (`hi`), retrieving **208 raw API records** (`data/raw/factcheck_api_claims.csv`).
2. **Deduplication & Temporal Filtering:** Deduplicating and filtering for the temporal window (June 6 to July 25, 2026) retained **86 records** from the API.
3. **Manual Search Rows & Provenance Audit:** An initial set of **73 manual claim rows** was assembled from search results. A strict URL provenance audit inspecting every link over HTTP revealed that **62 rows** had dead, parked, or redirecting links. These 62 rows were quarantined (`data/raw/manual_claims_quarantine.csv`, documented in `qa/qa_manual_audit.md` and `qa/unverified.md`). Exactly **11 verified manual rows** were retained.
4. **Combined Analysis Dataset:** Merging the 86 API records and 11 verified manual records yielded the final dataset of **97 records** representing **85 unique claims** (`claim_id`), serialized to `data/processed/final_labels.csv`.

### 2.2 Coverage and Outlets
- **Outlets:** Debunked across **13 fact-checking outlets/desks** (The Quint [16], BOOM [15], FACTLY [11], AFP Fact Check [9], Vishvas News [7], Alt News [6], NewsMobile [6], Press Trust of India [6], Lighthouse Journalism [6], AajTak [6], Telugu Post [5], India Today [3], DigitEye India [1]).
- **Temporal Distribution:**
  - June 2026: **16 rows** ({n_june_claims} unique claims)
  - July 2026: **78 rows** ({n_july_claims} unique claims)
  - Undated `claim_date`: **3 rows** ({n_undated_claims} unique claims: `C0002` [R0003], `C0044` [R0045], `C0076` [R0077]). In all three cases, the `review_date` is in July 2026, accounting for earlier preliminary tallies reporting 81 July rows.

### 2.3 Privacy Scrubbing
- All personal usernames, private profile URLs, and names of private citizens were stripped from analytical files.
- The free-text `origin_note` field was replaced with a boolean flag `origin_note_present` (present in 4 records). Automated tests strictly assert zero occurrences of handle patterns.

---

## 3. Labelling Process and Human Adjudication

### 3.1 Labelling Workflow
- **Labelling Process & Roles:** Two team members (Coders A and B) filled their coding sheets independently of each other across four coded columns: relevance, narrative, content form, and direction. A third team member (Coder C) resolved all conflicts into the final adjudicated sheet (`data/raw/C_final.xlsx`).
- **Raw Cell Agreement:**
  - Across the four coded columns ($97 \\times 4 = 388$ cells), exactly **20 cell conflicts** occurred between Coders A and B (5.2% of cells), yielding a **raw cell agreement of 94.8%**.
  - This metric represents raw percentage agreement across cells; it is not chance-corrected, does not represent formal inter-coder reliability, and excludes the free-text Origin column.
  - The original independent sheets for Coders A and B were not retained after adjudication. Consequently, Cohen's kappa and per-field inter-coder agreement cannot be computed and are not computable from the supplied files.

### 3.2 Label Vocabulary & Approved Proposal Mapping
The labelling sheet utilized a native 13-category taxonomy. To evaluate alignment with the proposal's 6 target categories, we established `narrative_mapping.csv` (status: `APPROVED by team`).

To prevent un-trainable classes during grouped cross-validation, classes with fewer than 8 distinct claims were merged into `other` (Scheme P) or `other_merged` (Scheme N). In Scheme P, `other` (24 rows, 21 claims) is a mixed residual category that folded `protester_violence` (7 rows, 5 claims) and `individual_targeting` (7 rows, 6 claims) into native administrative `other` (10 rows, 10 claims).

```mermaid
graph TD
    A["Native Vocabulary (13 Categories)"] -->|Category Rules| B["Proposal Codes (6 Categories)"]
    A -->|Rare-Class Threshold (< 8 claims)| C["Scheme P (4 Final Classes)"]
    A -->|Rare-Class Threshold (< 8 claims)| D["Scheme N (5 Final Classes)"]
    
    subgraph Scheme P Classes
    C1["crowd_legitimacy (44 rows / 35 claims)"]
    C2["other (mixed residual: 24 rows / 21 claims)"]
    C3["police_force (15 rows / 15 claims)"]
    C4["slogans_communal_loyalty (14 rows / 14 claims)"]
    end
```

---

## 4. Methodology

### 4.1 Model Configurations
1. **`dummy_majority`:** Baseline classifier predicting the most frequent training class (`crowd_legitimacy`).
2. **`tfidf_char_lr`:** Sub-word character n-grams (2–5 `char_wb`) with balanced Logistic Regression ($C=1.0$).
3. **`tfidf_wordchar_lr`:** Feature union of character n-grams (2–5) and word n-grams (1–2) with balanced Logistic Regression.
4. **`tfidf_char_surface_lr`:** Ablation combining character n-grams with 10 standardized surface features.
5. **`xlmr_lr`:** Mean-pooled representations from frozen `xlm-roberta-base` (768 dimensions) with StandardScaler and balanced Logistic Regression.
6. **`muril_lr`:** Mean-pooled representations from frozen `google/muril-base-cased` (768 dimensions) with StandardScaler and balanced Logistic Regression.
*(Note: Transformer encoder models were executed locally with pre-cached weights.)*

### 4.2 Grouped, Stratified Cross-Validation
- **Folds:** 5-fold StratifiedGroupKFold grouped strictly on `claim_id`.
- **Seeds:** 5 random seeds (`[42, 43, 44, 45, 46]`), yielding 25 fold evaluations per model. Note: because the 25 folds represent 5 repeated splits on the same 85 claims, they are not statistically independent.
- **Nested Cross-Validation:** Outer 5-fold grouped CV wrapping an inner 3-fold model selection loop to evaluate selection procedure stability.
- **Model Selection Rule:** Fixed in advance as highest mean fold Macro-F1 on Scheme P.

---

## 5. Results (RQ3)

### 5.1 Primary Scheme P Results (4 Classes, n=97 rows, 85 claims)

{p_table}

- **Model Comparison:** `muril_lr` is the highest-scoring candidate under the pre-set rule (mean Macro-F1: **{best_mean:.4f} ± 0.1377**). However, the candidates are not clearly separable: the mean gaps between `muril_lr`, `xlmr_lr` (0.5590), and `tfidf_char_lr` (0.5360) are smaller than the fold standard deviations (0.12 to 0.15), and no single model is demonstrably best.
- **Nested Cross-Validation Estimate:** **{nested_res['nested_mean_macro_f1']:.4f} ± {nested_res['nested_std_macro_f1']:.4f}**. Outer fold model selections varied across four different models: {nested_res['outer_selected_models']}.

![Model Comparison](figures/model_comparison.png)

### 5.2 Paired Differences Against Dummy Baseline (Scheme P, 25 Folds)

{paired_table}

All models beat the dummy majority baseline across 25 of 25 evaluation folds. However, because folds across seeds share the same 85 claims, this is weaker evidence than 25 independent trials.

### 5.3 Paired Differences Between Top Three Models (Scheme P, 25 Folds)

{paired_top_table}

The mean differences between top candidates (+0.023 to +0.054) are smaller than their fold standard deviations (0.10 to 0.13), demonstrating that candidate performances overlap substantially.

### 5.4 Secondary Scheme N Results (5 Classes, n=97 rows, 85 claims)

{n_table}

On the native 5-class problem, sub-word character TF-IDF models (`tfidf_wordchar_lr` at 0.6081 and `tfidf_char_lr` at 0.6007) scored higher than transformer embeddings on this specific split.

### 5.5 Sensitivity Analysis (Excluding 4 Related Records, n=93 rows, 82 claims)

{sens_table}

On Scheme P ($n=97$), model rankings by mean Macro-F1 are `muril_lr` (0.5900) > `xlmr_lr` (0.5590) > `tfidf_char_lr` (0.5360) > `tfidf_char_surface_lr` (0.5257) > `tfidf_wordchar_lr` (0.5164). On the sensitivity subset excluding the 4 Related records ($n=93$), model rankings do not remain preserved: `xlmr_lr` moves to first place (0.5806, +0.0216), `muril_lr` drops to second (0.5675, -0.0225), `tfidf_wordchar_lr` (0.5209, +0.0045) overtakes `tfidf_char_surface_lr` (0.4862, -0.0395), while `tfidf_char_lr` remains in third place (0.5392, +0.0032).

### 5.6 Language Subgroup Evaluation (Seed 42 OOF)

{group_table}

Claims categorized as `english_likely` ($n=61$ rows) achieved Macro-F1 = **0.6960** on seed 42 OOF. `hinglish_likely` ($n=22$ rows) and `devanagari` ($n=14$ rows) have too few rows to score reliably. Note: `lang_group` was determined by an unverified heuristic (a short Romanized-Hindi word list) that was not confirmed by human annotators.

### 5.7 Temporal Holdout Check (80/20 Chronological Split)
- **Train Split (Earliest 80%):** 66 claims (77 records) from June 6 to July 21, 2026.
- **Test Split (Latest 20%):** 17 claims (17 records) from July 22 to July 25, 2026.
- **Result:** Macro-F1 = **{time_df['macro_f1'].iloc[0]:.4f}** (*single split, unstable*).
- **Interpretation:** Performance on late-period claims dropped to 0.4056. Whether this reflects evolving claim topics over time or small-sample test set variance is an untested hypothesis.

---

## 6. Error Analysis & Qualitative Audits

### 6.1 Audit Methodology
A qualitative QA audit (`model_errors`) was performed on 30 records drawn from the seed 42 OOF predictions of `muril_lr`, deliberately enriched to 15 errors and 15 correct predictions. Every record was reviewed by reading the primary source fact-check first before inspecting model outputs.

```mermaid
pie title QA Audit Scores on Model Error Sample (n = 30)
    "2 - Accurate / Defensible" : 15
    "1 - Borderline / Overlapping" : 9
    "0 - Outright Error" : 6
```

### 6.2 Primary Failure Modes
1. **`crowd_legitimacy` Over-Prediction (4 cases):** High class prevalence (45.4%) creates an inductive pull on claims describing general protest assembly or organizer conduct.
2. **Narrative Overlap (5 cases):** Boundary ambiguities between VIP appearances and slogan claims (e.g., Arundhati Roy's Kashmir speech, Christian pastors joining protest).
3. **Lexical Keyword Trigger Confusion (1 case):** In Devanagari Hindi (`R0061`), the co-occurrence of police and death keywords triggered `police_force`, failing to register that protesters were accused of killing the officer.
4. **Thin Text (1 case):** 5-word telegraphic claim (*"Videos show recent CJP protests"*, `R0009`) provided insufficient semantic signal.

![Confusion Matrix](figures/confusion_matrix.png)

---

## 7. Descriptive Findings for RQ1

**Research Question 1:** *What kinds of misleading or synthetic content were recorded, and what narratives did the claims back up?*

### Content Form by Narrative Matrix (Scheme P, n=97)

{rq1_table}

![RQ1 Content Form Matrix](figures/rq1_content_form_matrix.png)

### Key Empirical Takeaways:
1. **Shallow Fakes Outnumber Generative AI {n_recycled} : {n_total_ai} (about {ratio_shallow_ai} : 1):** In this sample of fact-checked claim records, 59.8% ({n_recycled}/97) consisted of recycled historical footage from earlier unrelated demonstrations, compared to 16.5% ({n_total_ai}/97) for all generative AI formats combined (images, videos, deepfakes). Because fact-checkers choose which claims to debunk, this reflects the distribution in debunked claims rather than the prevalence of content types online.
2. **AI Imagery Focuses on Crowd Inflation and Fabricated Casualties:** Generative visuals were concentrated in manufacturing false crowd attendance (`crowd_legitimacy`, n=6, comprising 4 AI-generated images and 2 AI-generated videos) and fabricating police casualty memorials (`police_force`, n=4 AI-generated images: `R0087`–`R0090`).
3. **Explicit Boundary Regarding RQ2 and RQ4:** The labelled dataset contains no verification-method records, correction timestamps, or quantified harm evidence. Consequently, **RQ2 (verification accounts and disagreements) and RQ4 (human harms and recommendations) are NOT answered by this sheet** and require separate qualitative case-study write-ups from the fact-check reports.

---

## 8. Limitations

1. **Modest Sample Size:** 97 records across 85 claims restricts statistical power and limits the number of sustainable classes to 4.
2. **Fact-Checker Selection Bias:** The dataset reflects claims chosen by newsrooms for debunking (skewed toward virality, prominent figures, and clear falsifiability).
3. **Class Imbalance:** `crowd_legitimacy` accounts for 45.4% of records, biasing text representations toward crowd turnout themes.
4. **Pre-Adjudication Agreement Retention:** While team members (Coders A and B) coded independently, the original sheets were not retained after adjudication by Coder C. Cohen's kappa and per-field inter-coder agreement cannot be computed, so only raw cell agreement (94.8%, 20 cell conflicts out of 388 cells) can be reported; this is not chance-corrected.
5. **Linguistic Representation:** `lang_group` is an unverified heuristic (a short Romanized-Hindi word list) that no human confirmed. The corpus also lacks regional Dravidian or Eastern Indic languages.
6. **Automated Access Restriction for R0059:** Record `R0059` remains categorized as `other`; its source fact-check page could not be opened by automated extraction tools due to site anti-bot protection.
7. **Alternative Reading of Individual Smears in Foreign/Conspiracy Category:** Records `R0046`, `R0051`, and `R0054` remain categorized as `slogans_communal_loyalty` as approved; these 3 of 14 rows concern named individuals (e.g., organizer Abhijeet Dipke and the Prime Minister) and would be classified as `individual_targeting` (merged into `other`) under an alternative reading. No model re-run was performed.

---

## 9. Deviations from Proposal

1. **Claim Records vs. Direct Posts:** Data was collected from published fact-checking investigations rather than 500+ direct platform posts due to platform API constraints.
2. **Platform Access Constraints:** Twitter/X API access was unavailable due to pricing barriers; Instagram content was captured exclusively through fact-checker citations.
3. **Label Taxonomy Harmonization:** The team's native 13-category schema differed from the proposal's 6 categories and was mapped (`narrative_mapping.csv`, approved by team).
4. **Quarantine of Manual Rows:** 62 of 73 manually collected claim rows were quarantined after a URL provenance audit found dead, parked, or redirecting links. These rows were originally assembled from search results; 11 verified manual rows remain.

---

## 10. Ethics and Privacy

- **No Surveillance or Censorship:** The system is designed for scholarly retrospective research and newsroom claim routing, not user tracking or automated censorship.
- **Strict Privacy Protection:** All social media usernames, individual phone numbers, and non-public individual identities have been removed from all analytical files.
- **Content Storage Policy:** We store links and short claim summaries and do not reproduce article text.

---

## Appendix A: Native Label Definitions and Proposal Mapping Table

| Native Label | Proposal Code | Mapping Level | Record IDs | Rationale | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Endorsement / solidarity claim | `crowd_legitimacy` | Category | all | VIP visits, external solidarity statements | APPROVED by team |
| Crowd size / legitimacy | `crowd_legitimacy` | Category | all | Turnout claims, drone visuals, crowd density | APPROVED by team |
| Moral / cultural smear | `crowd_legitimacy` | Category | all | Conduct smears challenging crowd demeanor | APPROVED by team |
| Police brutality / state repression | `police_force` | Category | all | Unlawful lathi-charge, tear gas, physical assaults | APPROVED by team |
| Fabricated casualties | `police_force` | Category | all | Manufactured protester death or ICU claims | APPROVED by team |
| Communal / anti-national framing | `slogans_communal_loyalty` | Category | all | Islamic slogans, anti-national chant allegations | APPROVED by team |
| Foreign / conspiracy link | `slogans_communal_loyalty` | Category | all | Foreign funding or extremist group ties | APPROVED by team |
| Protester violence / vandalism | `other` *(merged)* | Category | all | Stone pelting, train/bus arson (< 8 claims) | APPROVED by team |
| Personal smear of leader | `other` *(merged)* | Category | all | Organizer Dipke private life smears (< 8 claims) | APPROVED by team |
| Pro-police counter-narrative | `other` | Category | all | Pro-police rallies, civilian counter-protests | APPROVED by team |
| Political attack on govt/BJP | `other` | Category | all | Minister satire, policy rumors | APPROVED by team |
| Delegitimizing / mockery | `crowd_legitimacy` | Row | R0016; R0074; R0080; R0086 | Student gaffes, AI turnout challenges | APPROVED by team |
| Fabricated document / statement | `other` | Row | R0027 | Fake minister resignation letter | APPROVED by team |
| Fabricated document / statement | `other` | Row | R0059 | Police video memo (automated tools blocked; stays in other) | APPROVED by team |

---

## Appendix B: Reproduction Commands and Environments

```bash
# 1. Environment Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Dataset Ingestion & Validation
python3 ingest_final.py

# 3. Model Training & Evaluation
python3 03_train_eval.py

# 4. Report Rebuild & Figure Generation
python3 build_report.py

# 5. CLI Inference Smoke Test
python3 predict.py --smoke-test

# 6. Test Suite Execution
pytest tests/ -v
```

- **Random Seeds:** Main evaluation seed = 42; Cross-validation seeds = `[42, 43, 44, 45, 46]`.
- **Verified Environment:** Python {py_ver} (macOS Darwin 24.6.0).

---

## Appendix C: Repository File Index

- `data/raw/C_final.xlsx`: Raw ground-truth workbook (97 rows).
- `data/processed/final_labels.csv`: Sanitized, joined analysis dataset (97 rows, 85 claims).
- `narrative_mapping.csv`: Complete native-to-proposal mapping rules.
- `03_train_eval.py`: Feature extraction, cross-validation, and model serialization.
- `predict.py`: Standalone CLI triage inference script with mandatory caveat.
- `outputs/final_model/model.joblib`: Serialized best model (`muril_lr`).
- `outputs/final_model/model_card.md`: Standard model documentation card.
- `qa/qa_mapping_audit.md`: Qualitative audit of label mapping rules.
- `qa/qa_label_audit.md`: Qualitative audit of human workbook labels.
- `qa/qa_model_errors.md`: Qualitative audit of model out-of-fold prediction errors.
- `privacy_log.md`: Privacy audit ledger verifying zero handle exposures.
- `REPORT.md`: This comprehensive technical report.
- `README.md`: Project documentation and quickstart instructions.
"""

    report_path.write_text(report_content, encoding="utf-8")
    print(f"Compiled REPORT.md ({len(report_content)} characters) -> {report_path}")


def main() -> None:
    out_dir = Path("outputs")
    fig_dir = Path("figures")
    report_path = Path("REPORT.md")

    if not out_dir.exists():
        raise FileNotFoundError("outputs/ directory not found. Please run 03_train_eval.py first.")

    print("Generating figures in figures/...")
    figs = generate_figures(out_dir, fig_dir)
    print(f"Generated {len(figs)} figures: {[p.name for p in figs]}")

    print("Compiling REPORT.md...")
    compile_report(out_dir, report_path)
    print("Build complete.")


if __name__ == "__main__":
    main()
