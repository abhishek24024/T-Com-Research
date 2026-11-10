# Agent Build Spec: Claim-Narrative Triage Pipeline

For a coding agent · Technical Communication study of synthetic content and the 2026 Jantar Mantar NEET protests · 7 Nov 2026

## 1. What you are building

Build a small, reproducible Python pipeline for a course research study. The study is a document analysis of fact-checked claims about the 20 July 2026 Jantar Mantar protests. The pipeline must (a) collect fact-checked claims, (b) turn them into a human-labelled dataset, (c) train and evaluate a small multilingual classifier that sorts claims by **narrative**, and (d) produce materials for a human qualitative review of its own outputs and the model's errors.

Priorities, in order: correctness and honest reporting, then reproducibility, then coverage of every stage below. Code elegance is not a goal. The classifier is a **feasibility pilot** that helps researchers sort documented claims into a review queue. It is not a detector.

### Hard rules (never violate)

1. **No spend.** Use only free APIs and free compute (CPU, or a free Colab/Kaggle GPU). Never call a paid API.
2. **No scraping**, no private messages, no X or Instagram collection. The only collection route is the Google Fact Check Tools API plus a manually filled CSV.
3. **Never predict AI vs human, "synthetic", or whether a claim is true.** Origin labels are recorded only by human coders from documentary evidence. The model predicts the narrative label only.
4. **Never generate propaganda or harmful text.** No text generator, no synthetic training data, no paraphrase augmentation.
5. **Privacy.** Never store claimant, account or user names. Use study IDs (`record_id`, `claim_id`). Never download or display abusive or doctored images.
6. **No score without its sample size.** Every reported number carries n rows and n distinct claims. Never describe a score as "detection" ability.
7. **No hyperparameter tuning** on the evaluation folds. Use the fixed values in section 7.
8. **Report honestly what you ran.** Your final message must separate "executed and verified" from "written but not executed". Never claim a step works if you did not run it.

## 2. Repository layout

```
project/
  README.md                 run order, how the team labels, how to run on Colab
  requirements.txt          pin: python>=3.10, pandas, numpy, scipy, scikit-learn>=1.5, requests; torch+transformers only for the encoder step
  config.py                 every constant (section 3); no constants inside scripts
  utils.py                  text normalisation, script detection, surface features
  01_collect_claims.py
  02_build_dataset.py       subcommands: make-sheet, finalize
  03_train_eval.py
  04_error_review.py        subcommands: make, score-blind, summarize
  05_qa_sample.py           agent QA sampler (section 9)
  make_demo_data.py         FAKE data for dry runs only (section 10)
  tests/                    pytest unit tests (section 10)
  data/raw/  data/processed/  outputs/  qa/
```

Scripts are numbered and run in order. Each reads the previous stage's files and fails with a clear message if one is missing.

## 3. Configuration (`config.py`)

- `SEED = 42`; `CV_SEEDS = [42,43,44,45,46]`; `N_SPLITS = 5`
- Window: `CLAIM_WINDOW_START = 2026-06-06`, `CLAIM_WINDOW_END = 2026-07-25`, `REPORT_CUTOFF = 2026-10-11`
- `SEARCH_TERMS` (placeholders: humans replace with terms taken from the cited fact-check reports), `LANGUAGES = [en, hi]`, `PUBLISHER_SITES = []` (empty means all publishers)
- `NARRATIVES = [police_force, protester_violence, slogans_communal_loyalty, crowd_legitimacy, individual_targeting, other]`
- `CONTENT_FORMS = [old_or_out_of_context, ai_generated, ai_altered, cropped_or_edited, fabricated_text, genuine_wrongly_called_fake, disputed, not_established]`
- `DIRECTIONS = [supports_protesters, supports_police_government, mixed, unclear]`
- `MIN_CLAIMS_PER_CLASS = 8`, `DUP_SIMILARITY = 0.80`, `MIN_ROWS_FOR_GROUP_SCORE = 30`, `TIME_HOLDOUT_FRACTION = 0.20`
- `HF_MODELS = {xlmr: xlm-roberta-base, muril: google/muril-base-cased}`, `MAX_LEN = 128`, `EMBED_BATCH = 16`
- `REVIEW_SAMPLE_SEED = 42`, `REVIEW_N = 30`, `FAILURE_TAXONOMY` (section 8)
- Environment variables: `GOOGLE_API_KEY` (free key), `PIPELINE_DATA_DIR` and `PIPELINE_OUT_DIR` (relocate all paths so dry runs never touch real data)

## 4. Data contracts

| File | Written by | Columns |
| --- | --- | --- |
| `data/raw/factcheck_api_claims.csv` | stage 1 | source, claim\_text, claim\_date, review\_date, publisher\_name, publisher\_site, review\_url, review\_title, textual\_rating, language\_code, text\_source, query\_term |
| `data/raw/manual_claims.csv` | humans (template from stage 1) | same columns; `source=manual`; `text_source` is `verbatim` or `summary` |
| `data/raw/search_terms_log.txt` | stage 1 | timestamp, terms, languages, sites, max age; written **before** any request |
| `data/processed/coding_sheet.csv` | stage 2 make-sheet | record\_id, claim\_id, claim\_date, review\_date, date\_check, publisher\_name, review\_url, text\_source, claim\_text, script, lang\_group\_heuristic, lang\_group\_manual, narrative, content\_form, direction, origin, coder\_notes |
| `data/raw/coder_A.csv`, `coder_B.csv` | two human coders | record\_id, narrative, content\_form, direction, coder\_notes |
| `data/raw/adjudicated.csv` | third coder | record\_id, narrative |
| `data/processed/dataset.csv` | stage 2 finalize | record\_id, claim\_id, claim\_date, text, text\_source, script, lang\_group, narrative, narrative\_original, content\_form, direction, label\_status, publisher\_name, review\_url |

One row is one (claim, report) pair. `claim_id` identifies the underlying post or claim, so several reports about the same post share one `claim_id`. **The number of claims is the number of distinct `claim_id`s, never the number of rows.**

## 5. Stage specifications

### Stage 1: collect claims (`01_collect_claims.py`)

- Endpoint: `GET https://factchecktools.googleapis.com/v1alpha1/claims:search`. Parameters: `query`, `languageCode`, `maxAgeDays`, `pageSize`, `pageToken`, `reviewPublisherSiteFilter`, `key`. **Check these parameter names against Google's official reference before coding**; do not rely on this list.
- Loop over every `SEARCH_TERMS` × `LANGUAGES` × (`PUBLISHER_SITES` or none). Page with `nextPageToken`. Default `maxAgeDays` = days from the window start to today plus 7.
- Retry on 429/5xx with exponential backoff; on any other error exit with a message that names the likely cause (bad key, API not enabled).
- Flatten to one row per (claim, review). Fields used: `claims[].text`, `claimDate`, `claimReview[].publisher.name/site`, `url`, `title`, `reviewDate`, `textualRating`, `languageCode`.
- **Drop `claimant`.** It can name accounts or people. Never write it to disk or logs.
- Drop exact duplicates on (claim\_text, review\_url). Set `text_source=unknown` for API rows.
- `--offline-json FILE` parses a saved response instead of calling the network (needed for tests).
- Create an empty `manual_claims.csv` template if absent. The API only covers publishers that use ClaimReview markup, so humans add the rest by hand.

### Stage 2a: build the coding sheet (`02_build_dataset.py make-sheet`)

1. Merge API and manual CSVs. Drop empty claim text.
2. Date filter: keep if `claim_date` is inside the window. If `claim_date` is missing and `review_date` is between the window start and `REPORT_CUTOFF`, keep and set `date_check=needs_manual_date_check`. Otherwise drop. Print counts dropped per reason.
3. Normalise text (section 7) and drop duplicates on (normalised text, review\_url).
4. **Propose `claim_id`s**: char-n-gram (3 to 5, `char_wb`) TF-IDF cosine similarity; pairs at or above `DUP_SIMILARITY` are linked; connected components become claim\_ids. This is a proposal that coders confirm or edit. Over-merging is safer than under-merging because shared claim\_ids keep near-duplicates on one side of every CV split.
5. Assign `record_id` (R0001...), `script` (devanagari/latin/mixed/other by letter ratios), and `lang_group_heuristic` (devanagari / hinglish\_likely / english\_likely). The heuristic uses a short list of Romanized-Hindi function words and is only a hint. Humans fill `lang_group_manual`.
6. Write `coding_sheet.csv` and a slim `coder_template.csv`.

### Stage 2b: finalize labels (`02_build_dataset.py finalize`)

1. Validate narrative codes against `NARRATIVES`; stop with the invalid values listed.
2. If coder B exists: compute Cohen's kappa and percent agreement on the narrative overlap (and on content\_form if present). **Report agreement before adjudication** to `outputs/label_agreement.json`. Write disagreements to `outputs/label_disagreements.csv` with an empty `final_third_coder` column.
3. Final label priority: adjudicated, then two coders agree, then single coder (flag `single_coder`). Unresolved disagreements are **excluded from modelling and logged** (`label_status=unresolved_disagreement`).
4. One narrative per claim: if records sharing a `claim_id` conflict, take the majority and log the conflict to `outputs/claim_label_conflicts.csv`.
5. **Rare-class merge**: any narrative (except `other`) with fewer than `MIN_CLAIMS_PER_CLASS` distinct claims is merged into `other`. Keep the original in `narrative_original` and print what was merged.
6. Write `dataset.csv` and `outputs/rq1_form_by_narrative.csv` (content\_form × narrative, counted at **claim** level).

### Stage 3: features, models, evaluation (`03_train_eval.py`)

Task: predict `narrative` from `text`. Group by `claim_id`.

**Models** (all with the fixed settings in section 7):

| Name | Features | Classifier |
| --- | --- | --- |
| `dummy_majority` | none | most frequent class (the "do nothing" reference; always report it) |
| `tfidf_char_lr` | char\_wb 2 to 5-gram TF-IDF | logistic regression |
| `tfidf_wordchar_lr` | char TF-IDF + word 1 to 2-gram TF-IDF | logistic regression |
| `tfidf_char_surface_lr` | char TF-IDF + 10 surface features, standardised | logistic regression (ablation only) |
| `xlmr_lr`, `muril_lr` | frozen encoder embeddings, mean-pooled, standardised | logistic regression |

Surface features: log characters, log words, Devanagari ratio, Latin ratio, count of `!`, count of `?`, uppercase ratio, has-digit, has-URL, count of hashtags/mentions. They can proxy outlet style, so treat as an ablation and never as a main result. **`text_source` and `publisher_name` must never be features.**

**Encoders:** frozen, no fine-tuning. Tokenise with truncation at `MAX_LEN`, mean-pool the last hidden state over real tokens using the attention mask, batch `EMBED_BATCH`. Cache embeddings on disk keyed by model id plus a hash of the texts. If torch, transformers or the model download is unavailable, **skip the encoder models loudly**, record them in `run_info.json` under `skipped`, and print a notice under the results table. Do not fail the run and do not hide the skip.

**Cross-validation:** `StratifiedGroupKFold(shuffle=True)` grouped by `claim_id`, repeated over `CV_SEEDS`. `StratifiedGroupKFold` needs enough groups per class: set the fold count to `min(N_SPLITS, smallest class's distinct-claim count)`, warn if reduced, and stop with a clear message if any class has fewer than 2 claims. The TF-IDF fitting must happen inside each training fold (use sklearn `Pipeline`).

**Metrics:** macro-F1 per fold (default label set = classes present in the fold's truth or predictions, `zero_division=0`), summarised as mean and standard deviation over all folds and seeds; pooled out-of-fold macro-F1 per seed; per-class precision, recall, F1 and support; confusion matrix pooled from the first seed.

**Language-group scores:** per `lang_group`, on the first seed's out-of-fold predictions. Report a score only if the group has at least `MIN_ROWS_FOR_GROUP_SCORE` rows; otherwise write the row with a null score and the status "too few rows; describe errors qualitatively".

**Time check (secondary):** order claims by earliest `claim_date`, train on the earliest 80% of claims, test on the latest 20%. Single split; label it "unstable, descriptive only". Skip with a note if fewer than 10 dated claims.

**Outputs** in `outputs/`: `cv_folds.csv`, `cv_summary.csv` (columns include n\_rows, n\_claims, n\_splits), `oof_predictions.csv` (record\_id, claim\_id, seed, model, y\_true, y\_pred, lang\_group, text), `per_class_<model>.csv`, `confusion_<model>.csv`, `group_scores.csv`, `time_holdout.csv`, `run_info.json` (sizes, claims per class, seeds, folds used, models run, skipped models, library versions, and the caveat sentence "feasibility pilot on documented claim records; scores are unstable and are not evidence that AI propaganda can be detected").

### Stage 4: human error review (`04_error_review.py`)

See section 8.

## 6. Expected shape of the real data (design for it)

- Expect roughly 60 to 150 claims. After the rare-class merge, **likely only two or three narrative classes remain**, and `other` may dominate. The pipeline must handle this gracefully and the report must state which narratives were merged. Do not lower `MIN_CLAIMS_PER_CLASS` to keep classes alive.
- Most fact-checker text is English. Hindi and Hinglish rows exist only where a report quotes the post or a Hindi edition was collected, so per-language scores will often be "too few rows".
- Several rows per claim are near-duplicates. They do not add independent information, so effective sample size is the number of claims.
- Expect noisy, modest scores and large fold-to-fold spread. TF-IDF may beat frozen encoders. Report what happens; do not tune to change it.

## 7. Fixed settings and known pitfalls

- Logistic regression: `max_iter=2000`, `class_weight="balanced"`, `C=1.0`. Embedding pipeline: `StandardScaler` then logistic regression. Dummy: `most_frequent`.
- **Devanagari handling.** Python's `\w` and scikit-learn's default token pattern treat Hindi vowel signs as non-word characters and split words apart. Normalise by keeping Unicode categories L, M and N (and whitespace), lowercase, strip URLs and punctuation, collapse whitespace. Use a custom tokenizer (`str.split` on the normalised text) for word n-grams. Add a unit test that a Hindi word with vowel signs survives normalisation intact.
- Pass the normaliser as the vectoriser's `preprocessor` so train and test are treated identically.
- Write code that works with pandas 3 and scikit-learn 1.5 or later (for example `groupby(...).apply(..., include_groups=False)`), and do not depend on pandas string-dtype behaviour.
- Unresolved label disagreements and unlabelled rows never enter training or evaluation.
- Fixed seeds everywhere a random choice is made (CV, sampling, shuffling).

## 8. Human-style qualitative review (mandatory)

Numbers alone do not show whether the pipeline's output is any good, so every data-producing stage gets a read-through like a human reviewer would do. Two parts: the model-error review the study needs (stage 4), and your own QA (section 9).

### Stage 4 outputs (`outputs/review/`)

`04_error_review.py make [--model NAME]` (default: best non-dummy model by mean fold macro-F1):

- Use the first CV seed's out-of-fold predictions. **Sample at claim level** (one random record per claim) with `REVIEW_SAMPLE_SEED`, so items are independent claims.
- Draw about half errors and half correct predictions up to `REVIEW_N`, topping up with whichever type is short. The sample is deliberately enriched for errors, so its accuracy is **not** the model's accuracy; say this in `review_meta.json` and in the printed output.
- `review_meta.json` records: model, CV seed used, sample seed, claims available, errors available, correct available, number sampled of each, taxonomy, allowed labels.
- `review_sheet.csv`: record\_id, claim\_id, review\_url, text, gold, predicted, `rubric_score`, `reason`, `failure_type`. Column order matters: text and URL come **before** gold and predicted.
- `blind_packet.csv`: shuffled, with packet IDs (B01...), review\_url, text, `blind_label`, `confidence_1to3`, `notes`. It must contain **no** gold label, no prediction and no record\_id.
- `answer_key.csv`: packet\_id, record\_id, gold, predicted. Keep it separate from the packet.

### Review rules (put them in the README and the sheet header)

1. A teammate who did not code those items fills the blind packet **first**, reading the source report at `review_url` before the text.
2. The reviewer then opens `review_sheet.csv` and reads the source report **before** looking at gold or predicted.
3. Rubric: 2 = prediction correct; 1 = defensible alternative; 0 = wrong.
4. **Every row scored 0 or 1 needs a one-line reason and a failure type.**
5. `FAILURE_TAXONOMY`: `dialect_or_script`, `protest_anger_read_as_violence`, `quoted_text`, `thin_text`, `label_ambiguity`, `narrative_overlap`, `other`.

`score-blind PATH` joins the filled packet to the answer key and prints: n labelled; blind-vs-gold agreement; blind-vs-model agreement; model-vs-gold agreement on the same items; Cohen's kappa for blind vs gold; and the reading guide (if blind matches model but both differ from gold, suspect the gold label; if blind matches gold but the model differs, it is a model error; small n means describe, do not generalise). Warn on invalid labels.

`summarize PATH` prints n reviewed, score counts, mean score, failure types among low scores, and the list of rows missing a reason or a valid failure type.

## 9. Agent QA of your own outputs (`05_qa_sample.py`)

After each stage below runs on **real or demo data**, review a sample the way a careful human would, and write `qa/qa_<stage>.md`. Never skip this because the code ran without errors.

| Stage | Source to read first | Output to judge | Rubric (2 / 1 / 0) |
| --- | --- | --- | --- |
| Collection | raw API JSON record | its row in the claims CSV | fields parsed correctly, claimant absent, date and language right / minor field error / wrong or lost data |
| Coding sheet | the claim texts | proposed `claim_id` groups | same claim grouped, distinct claims apart / borderline / wrongly merged or split |
| Model errors | the report at `review_url` | prediction | as section 8 |

For every QA run:

1. Draw a random sample with a fixed seed (`SEED = 42`), size 20 or the whole set if smaller. **Print the sample size and population size**, and never extrapolate beyond them.
2. For each item, **read the source first, then the processed output**, then score.
3. Give a one-line reason for **every** item scored below 2.
4. Build a failure taxonomy from what you saw (names are free-form per stage) and count each type.
5. State plainly what the sample cannot tell you.
6. For the human: write `qa/blind_<stage>.csv` with the source only (processed output hidden, shuffled, packet IDs) and `qa/key_<stage>.csv` separately, so a person can review blind and compare with your scores.

## 10. Testing and acceptance

**Dry run on fake data.** `make_demo_data.py fake-api` writes a fake API response and a hidden truth file; `simulate-coders` writes `coder_A.csv` and `coder_B.csv` (B with about 10% flipped labels). Run it with `PIPELINE_DATA_DIR` and `PIPELINE_OUT_DIR` pointing to scratch folders. Fake data must use `demo.example` URLs and must never be mixed into the real `data/` or quoted in the report. Include out-of-window dates, exact duplicates and a second outlet reviewing the same claim, to exercise the filters and claim grouping.

**Unit tests (pytest):**

- Normaliser keeps Hindi vowel signs and strips URLs and punctuation
- Script detection and the Hinglish hint on small examples
- API flattener drops `claimant` and handles missing fields and empty responses
- Date filter: inside window, missing claim date with usable review date, outside window
- Near-duplicate grouping merges the same claim and keeps different claims apart
- Kappa and agreement on a hand-computed example
- Rare-class merge counts **distinct claims**, not rows
- Fold-count reduction when a class has few claims
- No claim\_id appears in both train and test of any fold
- `blind_packet.csv` contains no gold, prediction or record\_id
- Re-running with the same seeds gives identical `cv_summary.csv`

**Acceptance criteria:**

1. The full chain (stages 1 to 4) runs end to end on the demo data with the encoder step skipped, and every output file in section 5 exists.
2. All unit tests pass.
3. The encoder path (XLM-R, MuRIL) is either run on a machine with torch and model access, or explicitly reported as **not executed**. Never mark it verified without running it.
4. `run_info.json` lists any skipped models.
5. QA files from section 9 exist for the demo run.
6. The README covers: run order, the team's labelling workflow (coder A and B, the 10% overlap, the third coder), the Colab command sequence for the encoder step, and a "Deviations from the proposal" paragraph. That paragraph must say: the classifier is trained on claim records rather than the 500 or more posts the proposal required; Instagram is covered only through claims reported by fact-checkers; per-language results are limited.

## 11. How outputs map to the report

| Research question | Evidence produced |
| --- | --- |
| RQ1: kinds of content and narratives | `rq1_form_by_narrative.csv`, descriptive counts (claim level) |
| RQ2: how claims were verified, where sources disagree | coding-sheet fields (textual rating, publisher, dates), disagreement cases |
| RQ3: can a multilingual classifier help, with what errors | `cv_summary.csv` (with dummy reference), per-class and confusion files, `group_scores.csv`, review outputs, failure taxonomy |
| RQ4: documented harms and recommendations | documentary evidence only; the pipeline does not measure harm or trust |

## 12. Inputs the humans must supply

- A free Google Cloud API key with the Fact Check Tools API enabled
- `SEARCH_TERMS` taken from the cited fact-check reports, and optional `PUBLISHER_SITES` (confirm each domain is correct)
- Manual claims from outlets the API misses, and the labels from coders A, B and the third coder

If anything here conflicts with the hard rules in section 1, the hard rules win. If something is ambiguous, state your assumption in the README rather than guessing silently.
