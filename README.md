# CJP Protest Claim-Narrative Triage Pipeline

An empirical natural language processing and triage pipeline for classifying disinformation narratives in documented claim records from the June–July 2026 Cockroach Janata Party (CJP) student protests in New Delhi, India.

---

## What This Project Is and Is NOT

### What It IS:
- A scholarly natural language processing research pipeline evaluating the feasibility of automated narrative triage on documented fact-checked claim texts.
- An empirical investigation addressing the project proposal's Research Questions:
  - **RQ1:** *What kinds of misleading or synthetic content were recorded, and what narratives did the claims back up?* (Partly answered by content-form x narrative cross-tabulation in Section 7).
  - **RQ2:** *How did fact-checkers and public agencies verify the claims, and where did their accounts disagree?* (**NOT answered by the labelled sheet**; requires separate qualitative case studies).
  - **RQ3:** *Can a multilingual classifier help researchers sort claim narratives without replacing human judgement, and what errors does it make across English, Hindi and Hinglish?* (Answered by cross-validation benchmark and error analysis).
  - **RQ4:** *What human harms are documented, and what communication recommendations are supported by this evidence?* (**NOT answered by the labelled sheet**; requires separate qualitative case studies).
- A comparative benchmark of 6 model architectures (from majority-class baselines and character n-gram TF-IDF models to frozen multilingual transformer representations).

### What It is NOT:
- **NOT an AI or Deepfake Detector:** The model evaluates claim text only. It does not inspect images or videos, and cannot determine whether an attached file is synthetically generated.
- **NOT a Truth Arbiter or Fact-Checker:** The system assumes claims have been flagged for inquiry; it cannot independently assess empirical real-world veracity.
- **NOT for Automated Moderation or Account Enforcement:** Model outputs are research triage aids, not platform policy or automated content moderation tools.
- **NOT a Verification or Harm Study for RQ2 & RQ4:** The labelled sheet contains no verification-method taxonomy, correction timestamps, or quantified harm evidence; **RQ2 and RQ4 are explicitly not answered by the dataset** and require separate qualitative case-study write-ups from fact-check reports.

---

## Repository Layout

```text
.
├── C_final.xlsx                    <- Original human-annotated workbook (raw ground truth)
├── data/
│   ├── raw/
│   │   ├── C_final.xlsx            <- Copy of ground-truth workbook (97 records)
│   │   └── backup/                 <- Preserved workbook backups
│   └── processed/
│       ├── coding_sheet.csv        <- Canonical registry with claim_id and temporal metadata
│       └── final_labels.csv        <- Sanitized analysis dataset (97 rows, 85 distinct claims)
├── outputs/
│   ├── run_info.json               <- Run metadata and dataset SHA-256 checksum
│   ├── cv_summary_scheme_p.csv     <- Scheme P (Primary 4 classes) cross-validation results
│   ├── cv_summary_scheme_n.csv     <- Scheme N (Native 5 classes) cross-validation results
│   ├── cv_summary_sensitivity.csv  <- Sensitivity run excluding 4 Related records (93 rows)
│   ├── paired_diff_vs_dummy.csv    <- Paired difference vs dummy baseline across 25 folds
│   ├── per_class_metrics.csv       <- Precision, recall, F1, support per class
│   ├── confusion_muril_lr.csv      <- Seed 42 OOF confusion matrix (best model)
│   ├── group_scores.csv            <- Language subgroup evaluation (scored vs too few rows)
│   ├── time_holdout.csv            <- Chronological holdout evaluation (80% early / 20% late)
│   ├── nested_cv_results.json      <- Nested CV estimate of model selection procedure
│   ├── rq1_form_by_narrative_mapped.csv <- Content form vs. Scheme P cross-tabulation
│   ├── rq1_form_by_narrative_native.csv <- Content form vs. native narrative cross-tabulation
│   └── final_model/
│       ├── model.joblib            <- Serialized best model artifact (muril_lr)
│       ├── tfidf_char_lr.joblib    <- Lightweight fallback model artifact
│       └── model_card.md           <- Standard model documentation card
├── figures/                        <- High-resolution publication figures (300 DPI)
│   ├── class_distribution.png      <- Scheme P and Scheme N class distributions
│   ├── model_comparison.png        <- Model comparison bar chart with dummy baseline
│   ├── confusion_matrix.png        <- Annotated OOF confusion matrix heatmap
│   └── rq1_content_form_matrix.png <- Content Form x Narrative heatmap
├── qa/                             <- Qualitative review packets (blind and key files)
│   ├── qa_mapping_audit.md         <- Qualitative audit of narrative mapping rules
│   ├── qa_label_audit.md           <- Qualitative audit of human workbook labels
│   ├── qa_model_errors.md          <- Qualitative audit of model prediction errors
│   └── qa_report_check.md          <- Factual audit tracing REPORT.md numbers
├── tests/                          <- Automated pytest test suite
│   └── test_pipeline.py            <- Comprehensive pipeline and privacy validation tests
├── ingest_final.py                 <- Stage 2: Data ingestion, validation, and privacy scrub
├── 03_train_eval.py                <- Stage 3: Feature extraction, CV, and model serialization
├── build_report.py                 <- Stage 4: Figure generation and REPORT.md compilation
├── predict.py                      <- Standalone CLI inference tool with mandatory warning
├── colab_encoder_run.ipynb         <- Standalone Google Colab notebook for GPU execution
├── narrative_mapping.csv           <- Proposal-aligned narrative mapping rules
├── DECISIONS_NEEDED.md             <- Mapping decisions requiring human team approval
├── privacy_log.md                  <- Privacy audit ledger (counts only, zero handles)
├── requirements.txt                <- Pinned dependencies for reproducible execution
├── REPORT.md                       <- Comprehensive technical report (10 sections + appendices)
└── README.md                       <- Project documentation and instructions (this file)
```

---

## Environment Setup

- **Python Version:** Python 3.12 (compatible with Python >= 3.10)
- **Dependencies:** Install pinned requirements:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Reproduction Command Sequence

Execute the complete end-to-end pipeline from `C_final.xlsx` to `REPORT.md`:

```bash
# Step 1: Ingest, validate, and scrub privacy handles
python3 ingest_final.py

# Step 2: Train and evaluate models (5-seed x 5-fold StratifiedGroupKFold, nested CV)
python3 03_train_eval.py

# Step 3: Render publication figures and compile REPORT.md
python3 build_report.py

# Step 4: Run CLI inference smoke test (5 canonical examples)
python3 predict.py --smoke-test

# Step 5: Execute full pytest test suite
pytest tests/ -v
```

### Approximate Runtime:
- Data Ingestion & Privacy Scrub: ~1 second
- Cross-Validation & Model Training: ~15 seconds (using cached embeddings)
- Figure & Report Generation: ~3 seconds
- Total Runtime: **Under 30 seconds**

---

## Using `predict.py` for Inference

`predict.py` provides interactive and batch command-line inference with mandatory regulatory caveats:

```bash
# 1. Evaluate single claim with primary model (muril_lr)
python3 predict.py "Drone footage shows 1 million students gathering at Jantar Mantar demanding NEET re-exam."

# 2. Evaluate single claim with lightweight model (tfidf_char_lr, zero PyTorch dependency)
python3 predict.py --lightweight "Delhi police baton charged and critically injured peaceful student protesters."

# 3. Run built-in 5-example smoke test
python3 predict.py --smoke-test
```

### Example Output:
```text
Claim Text: "Delhi police baton charged and critically injured peaceful student protesters."
Predicted Narrative: police_force (99.97%)
Class Probabilities:
  - crowd_legitimacy         : 0.0000
  - other                    : 0.0001
  - police_force             : 0.9997
  - slogans_communal_loyalty : 0.0001

----------------------------------------------------------------------
WARNING: Feasibility pilot on documented claim records; not for detection or content moderation. Scores are unstable and are not evidence that AI propaganda can be detected.
----------------------------------------------------------------------
```

---

## Privacy Notes

In accordance with ethics guidelines:
- **Zero personal usernames, phone numbers, or account handles are retained or stored.**
- The free-text `origin_note` field was completely removed and replaced with a boolean `origin_note_present`.
- Automated test `test_privacy_zero_handles` verifies that zero social media handle patterns appear anywhere in `outputs/`, `qa/`, `README.md`, or `REPORT.md`.

---

## Google Colab Instructions

For environments without local transformer support or GPU acceleration:
1. Open `colab_encoder_run.ipynb` in Google Colab.
2. Select a GPU runtime (Runtime > Change runtime type > T4 GPU).
3. Upload `data/processed/final_labels.csv` and `narrative_mapping.csv`.
4. Run all cells to compute embeddings and cross-validation scores.
5. Transfer generated outputs to `outputs/` and run `python build_report.py` to rebuild the report locally.

---

## Pipeline Test Suite

Run unit and integration tests using `pytest`:

```bash
pytest tests/ -v
```

Tests verify:
- Complete 97-row ingestion and metadata joining on `claim_id`
- Proposal mapping completeness and row-level override rules
- Grouped cross-validation integrity (zero `claim_id` leakage across folds)
- Privacy enforcement (zero account handle patterns across artifacts)
- `predict.py` smoke test execution
- Category count consistency between datasets and generated figures

---

## Honest Status List

### Executed and Verified:
- Data collection waterfall: 208 raw Google Fact Check Tools API records -> 86 deduplicated windowed claims; 73 initial manual claims -> 62 quarantined after URL audit -> 11 verified manual claims; total 97 records across 85 unique claims.
- Full ingestion, sanitization, and SHA-256 verification of `data/raw/C_final.xlsx` (97 rows, 85 claims).
- Privacy scrub removing account handles and authoring `privacy_log.md` (counts only, zero handles).
- Label scheme mapping authoring (`narrative_mapping.csv`, `DECISIONS_NEEDED.md`, status: `APPROVED by team`).
- Qualitative QA Audits (`qa_mapping_audit.md`, `qa_label_audit.md`, `qa_model_errors.md`, `qa_report_check.md`, `qa_report_check_v2.md`) with corresponding blind review packets and keys.
- Complete 25-fold grouped cross-validation across 6 model configurations for Scheme P, Scheme N, and Sensitivity runs.
- Model evaluation and selection: `muril_lr` is the highest-scoring candidate under the pre-set rule; the candidates are not clearly separable; no single model is demonstrably best. Nested cross-validation estimate: 0.5251 ± 0.1913. Full model serialization (`outputs/final_model/model.joblib`).
- Standalone inference tool `predict.py` with 5-claim smoke test.
- Figure generation (`figures/`) and dynamic compilation of `REPORT.md`.

### Not Executed (with Reasons):
- **Verification Accounts & Disagreements (RQ2) and Human Harms & Recommendations (RQ4):** The underlying dataset consists of fact-checking claim records and contains zero verification-method taxonomy, correction timestamps, or quantified harm evidence; these questions are NOT answered by the labelled sheet and require separate qualitative case-study write-ups drawn directly from the fact-check narrative reports.
- **In-the-wild Social Media Scraping:** Excluded due to platform API access restrictions and privacy constraints.

---

## Team Confirmed Facts

1. **Coder Independence & Roles:** Team members (Coders A and B) filled sheets independently; a third team member (Coder C) resolved all conflicts into `data/raw/C_final.xlsx`.
2. **Conflict Unit & Agreement:** Conflicts were 20 cell conflicts across 388 cells ($97 \times 4$), yielding 94.8% raw cell agreement (5.2% conflict rate). Raw pre-adjudication sheets were not retained; chance-corrected Cohen's kappa is not computable.
3. **Record Decisions:** Record `R0059` remains in `other` (automated access restricted). Records `R0046`, `R0051`, and `R0054` remain in `slogans_communal_loyalty` as approved.
