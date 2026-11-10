# Model Card: CJP Protest Claim-Narrative Triage Model (`muril_lr`)

## Model Details
- **Model Name:** `muril_lr` (Frozen MuRIL `google/muril-base-cased` mean-pooled embeddings + StandardScaler + Logistic Regression)
- **Alternative Lightweight Baseline:** `tfidf_char_lr` (Sub-word character n-gram 2-5 TF-IDF + Logistic Regression, available at `outputs/final_model/tfidf_char_lr.joblib`)
- **Version:** 1.0 (November 2026)
- **Frameworks & Libraries:** Python 3.12, PyTorch 2.3.0, Hugging Face Transformers 4.40.0, Scikit-Learn 1.4.2, Pandas 2.2.2, NumPy 1.26.4
- **License / Usage:** Academic and research triage only.

## Intended Use
- **Primary Purpose:** Research triage and categorization of documented claim records extracted from Indian fact-checking organizations concerning the June–July 2026 CJP protests, addressing **Research Question 3 (RQ3)**:
  - **RQ1:** *What kinds of misleading or synthetic content were recorded, and what narratives did the claims back up?* (Partly addressed by descriptive cross-tabulations in Section 7 of the report).
  - **RQ2:** *How did fact-checkers and public agencies verify the claims, and where did their accounts disagree?* (**NOT answered by this model or dataset**; requires qualitative case studies).
  - **RQ3:** *Can a multilingual classifier help researchers sort claim narratives without replacing human judgement, and what errors does it make across English, Hindi and Hinglish?* (Directly addressed by this model and associated error analysis).
  - **RQ4:** *What human harms are documented, and what communication recommendations are supported by this evidence?* (**NOT answered by this model or dataset**; requires qualitative case studies).
- **Out-of-Scope & Prohibited Uses:**
  - **NOT for detection of AI-generated content or deepfakes.** The model predicts narrative framing of text claims; it does not predict whether media is synthetic or authentic.
  - **NOT for automated content moderation or account censorship.**
  - **NOT for live social media feed monitoring without human-in-the-loop verification.**

## Training Data
- **Dataset Version:** `data/processed/final_labels.csv`
- **SHA-256 Checksum:** `1b9076758b80006b3f950001ccd2f471576fd8fcaa4f92d75f40d6280c59a30f`
- **Size:** 97 total rows across 85 distinct claims (`claim_id`).
- **Temporal Span:** Documented claims from June 6, 2026 to July 25, 2026.
- **Target Vocabulary (Scheme P - 4 Classes):**
  - `crowd_legitimacy`: 44 rows (35 unique claims)
  - `other`: 24 rows (21 unique claims) — merges administrative claims and rare classes (`individual_targeting` [6 claims], `protester_violence` [5 claims])
  - `police_force`: 15 rows (15 unique claims)
  - `slogans_communal_loyalty`: 14 rows (14 unique claims)

## Performance & Validation
- **Evaluation Methodology:** 5-fold StratifiedGroupKFold grouped strictly on `claim_id` across 5 random seeds (`[42, 43, 44, 45, 46]`). No hyperparameter tuning was conducted on evaluation folds.
- **Model Selection Assessment:** `muril_lr` is the highest-scoring candidate under the pre-set rule; however, the candidates are not clearly separable, and no single model is demonstrably best.
- **Fold Independence Note:** Because the 25 evaluation folds represent 5 repeated splits on the same 85 claims, they are not statistically independent; beating the baseline across 25 of 25 folds is weaker evidence than 25 independent trials.
- **Cross-Validation Results (Scheme P):**
  - `muril_lr`: Mean Macro-F1 = **0.5900 ± 0.1377** (Seed 42 Pooled OOF Macro-F1 = 0.6608)
  - `dummy_majority` Baseline: Mean Macro-F1 = **0.1560 ± 0.0047**
  - Paired Difference vs Dummy: Mean paired difference = **+0.4340 ± 0.1369**, Fold Win Count = **25 / 25 folds**
- **Paired Differences Among Top 3 Candidates (25 Folds):**
  - `muril_lr` vs `xlmr_lr`: Mean difference = **+0.0310 ± 0.1311** (16 wins, 1 tie, 8 losses out of 25 folds)
  - `muril_lr` vs `tfidf_char_lr`: Mean difference = **+0.0540 ± 0.1041** (18 wins, 0 ties, 7 losses out of 25 folds)
  - `xlmr_lr` vs `tfidf_char_lr`: Mean difference = **+0.0230 ± 0.1159** (15 wins, 1 tie, 9 losses out of 25 folds)
- **Nested CV Estimate:** **0.5251 ± 0.1913** (Outer 5 folds, inner 3-fold model selection; accounts for candidate selection optimism). Outer fold selections selected 4 different models across 5 folds (`muril_lr`, `tfidf_char_lr`, `muril_lr`, `xlmr_lr`, `tfidf_wordchar_lr`).
- **Temporal Holdout Check (80% Earliest / 20% Latest):**
  - Train claims = 66, Test claims = 17.
  - Macro-F1 = **0.4056** (*single split, unstable*).
- **Subgroup & Language Performance:**
  - `english_likely` (n = 61 rows): Macro-F1 = **0.6960** (scored)
  - `hinglish_likely` (n = 22 rows): *Too few rows; describe errors qualitatively*
  - `devanagari` (n = 14 rows): *Too few rows; describe errors qualitatively*
  - Note: `lang_group` is an unverified heuristic (a short Romanized-Hindi word list) not confirmed by human annotators.

## Known Failure Modes & Limitations
1. **Dominant Class Over-prediction:** `crowd_legitimacy` accounts for 45% of rows, occasionally drawing borderline claims from other categories.
2. **Narrative Overlap:** Boundary cases between communal slogans and general protest chants, or between administrative rumors and crowd illegitimacy.
3. **Thin Text:** Short, telegraphic claims (e.g. 4-word social media captions) lack contextual grounding for semantic embeddings.
4. **Quoted / Ironical Content:** Sarcastic or quoted misinformation often confuses lexical polarity.

## Privacy & Ethical Considerations
- Zero personal social media usernames or private individuals' names are processed or stored in model artifacts.
- Training data is restricted strictly to claims investigated by accredited fact-checking organizations.
- Model decisions must never be used to penalize or moderate online users.

## Mandatory Notice
> **feasibility pilot on documented claim records; scores are unstable and are not evidence that AI propaganda can be detected**
