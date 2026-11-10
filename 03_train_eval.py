#!/usr/bin/env python3
"""Stage 3: Feature extraction, model training, cross-validation, and evaluation.

Models evaluated:
  - dummy_majority: Dummy baseline predicting the most frequent class
  - tfidf_char_lr: Character n-gram TF-IDF (2-5 char_wb) + Logistic Regression
  - tfidf_wordchar_lr: Char n-gram + Word n-gram (1-2) TF-IDF + Logistic Regression
  - tfidf_char_surface_lr: Char n-gram + 10 standardized surface features (Ablation)
  - xlmr_lr: Frozen XLM-RoBERTa embeddings + Logistic Regression (if available)
  - muril_lr: Frozen MuRIL embeddings + Logistic Regression (if available)

Grouped cross-validation by claim_id across repeated seeds.
Supports Scheme P (primary proposal mapping), Scheme N (secondary native),
and Sensitivity run (excluding Related records).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any
import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer

from config import (
    CV_SEEDS,
    EMBED_BATCH,
    HF_MODELS,
    MAX_LEN,
    MIN_ROWS_FOR_GROUP_SCORE,
    N_SPLITS,
    SEED,
    TIME_HOLDOUT_FRACTION,
    get_out_dir,
    get_processed_data_dir,
)
from utils import (
    SurfaceFeatureExtractor,
    normalize_text,
    split_tokenizer,
)

CAVEAT_SENTENCE = (
    "feasibility pilot on documented claim records; "
    "scores are unstable and are not evidence that AI propaganda can be detected"
)


def get_encoder_embeddings(
    model_name_or_path: str,
    texts: list[str],
    cache_dir: Path,
    batch_size: int = EMBED_BATCH,
    max_len: int = MAX_LEN,
) -> np.ndarray:
    """Extracts mean-pooled hidden state embeddings from a frozen Hugging Face transformer.

    Checks scratch/ and cache_dir for precomputed embeddings before downloading.
    """
    clean_model_key = model_name_or_path.replace("/", "_").replace("-", "_")
    scratch_dir = Path("scratch")
    candidate_paths = [
        scratch_dir / f"embed_{clean_model_key}.npy",
        scratch_dir / f"embed_{model_name_or_path.replace('/', '_')}.npy",
        scratch_dir / f"embed_{model_name_or_path}.npy",
    ]
    for p in candidate_paths:
        if p.exists():
            arr = np.load(p)
            if len(arr) == len(texts):
                return arr

    text_hash = hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    cache_file = cache_dir / f"embed_{clean_model_key}_{text_hash}.npy"
    if cache_file.exists():
        return np.load(cache_file)

    import torch
    from transformers import AutoModel, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name_or_path)
    try:
        model = AutoModel.from_pretrained(model_name_or_path, low_cpu_mem_usage=True)
    except TypeError:
        model = AutoModel.from_pretrained(model_name_or_path)
    model.eval()

    device = torch.device("mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu"))
    model.to(device)

    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i : i + batch_size]
        encoded = tokenizer(
            batch_texts,
            padding=True,
            truncation=True,
            max_length=max_len,
            return_tensors="pt",
        )
        encoded = {k: v.to(device) for k, v in encoded.items()}

        with torch.no_grad():
            outputs = model(**encoded)
            last_hidden = outputs.last_hidden_state
            mask = encoded["attention_mask"].unsqueeze(-1).expand(last_hidden.size()).float()
            sum_embeddings = torch.sum(last_hidden * mask, dim=1)
            sum_mask = torch.clamp(mask.sum(dim=1), min=1e-9)
            mean_pooled = sum_embeddings / sum_mask
            all_embeddings.append(mean_pooled.cpu().numpy())

    embed_array = np.vstack(all_embeddings)
    cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(cache_file, embed_array)
    return embed_array


def build_text_pipeline(model_type: str, random_state: int = SEED) -> Any:
    """Constructs sklearn Pipeline for text-based models with fixed hyperparameters."""
    lr = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        C=1.0,
        random_state=random_state,
    )

    if model_type == "dummy_majority":
        return DummyClassifier(strategy="most_frequent")

    elif model_type == "tfidf_char_lr":
        return Pipeline([
            ("tfidf_char", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                preprocessor=normalize_text,
            )),
            ("clf", lr),
        ])

    elif model_type == "tfidf_wordchar_lr":
        union = FeatureUnion([
            ("char_wb", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                preprocessor=normalize_text,
            )),
            ("word", TfidfVectorizer(
                analyzer="word",
                ngram_range=(1, 2),
                preprocessor=normalize_text,
                tokenizer=split_tokenizer,
                token_pattern=None,
            )),
        ])
        return Pipeline([
            ("union", union),
            ("clf", lr),
        ])

    elif model_type == "tfidf_char_surface_lr":
        union = FeatureUnion([
            ("char_wb", TfidfVectorizer(
                analyzer="char_wb",
                ngram_range=(2, 5),
                preprocessor=normalize_text,
            )),
            ("surface", Pipeline([
                ("ext", SurfaceFeatureExtractor()),
                ("scaler", StandardScaler()),
            ])),
        ])
        return Pipeline([
            ("union", union),
            ("clf", lr),
        ])

    raise ValueError(f"Unknown text model type: {model_type}")


def map_labels(
    df: pd.DataFrame,
    mapping_path: Path,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Applies Scheme P, Scheme N, and rare-class rules."""
    df = df.copy()

    # Fallbacks for legacy dataset.csv
    if "narrative_native" not in df.columns:
        df["narrative_native"] = df.get("narrative", "")
    if "lang_group" not in df.columns:
        df["lang_group"] = "english_likely"
    if "relevance" not in df.columns:
        df["relevance"] = "on_topic"

    # Load mapping
    cat_map: dict[str, str] = {}
    row_map: dict[str, str] = {}
    if mapping_path.exists():
        mapping_df = pd.read_csv(mapping_path)
        for _, r in mapping_df[mapping_df["level"] == "category"].iterrows():
            cat_map[str(r["native_label"]).strip()] = str(r["proposal_code"]).strip()
        for _, r in mapping_df[mapping_df["level"] == "row"].iterrows():
            pcode = str(r["proposal_code"]).strip()
            for rid in str(r["record_ids"]).split(";"):
                if rid.strip():
                    row_map[rid.strip()] = pcode

    # Fallback category map if file missing
    if not cat_map:
        cat_map = {
            "Endorsement / solidarity claim": "crowd_legitimacy",
            "Crowd size / legitimacy": "crowd_legitimacy",
            "Moral / cultural smear": "crowd_legitimacy",
            "Police brutality / state repression": "police_force",
            "Fabricated casualties": "police_force",
            "Communal / anti-national framing": "slogans_communal_loyalty",
            "Foreign / conspiracy link": "slogans_communal_loyalty",
            "Protester violence / vandalism": "protester_violence",
            "Personal smear of leader": "individual_targeting",
            "Pro-police counter-narrative": "other",
            "Political attack on govt/BJP": "other",
        }

    proposal_codes = {
        "police_force",
        "protester_violence",
        "slogans_communal_loyalty",
        "crowd_legitimacy",
        "individual_targeting",
        "other",
    }

    # 1. Scheme P Raw
    def _map_p(row: pd.Series) -> str:
        rid = str(row.get("record_id", "")).strip()
        if rid in row_map:
            return row_map[rid]
        native = str(row.get("narrative_native", "")).strip()
        if native in proposal_codes:
            return native
        return cat_map.get(native, "other")

    df["scheme_p_unmerged"] = df.apply(_map_p, axis=1)

    # Scheme P Rare-class threshold (< 8 distinct claims -> other)
    claims_p = df.groupby("scheme_p_unmerged")["claim_id"].nunique()
    rare_p = set(claims_p[claims_p < 8].index)
    df["scheme_p"] = df["scheme_p_unmerged"].apply(lambda x: "other" if x in rare_p else x)

    # 2. Scheme N Raw & Merged (< 8 distinct claims -> other_merged)
    claims_n = df.groupby("narrative_native")["claim_id"].nunique()
    rare_n = set(claims_n[claims_n < 8].index)
    df["scheme_n"] = df["narrative_native"].apply(lambda x: "other_merged" if x in rare_n else x)

    meta = {
        "scheme_p_rare_merged": sorted(list(rare_p)),
        "scheme_n_rare_merged": sorted(list(rare_n)),
    }
    return df, meta


def run_cv_for_scheme(
    df: pd.DataFrame,
    target_col: str,
    scheme_name: str,
    models_to_run: list[str],
    encoder_features: dict[str, np.ndarray],
    out_dir: Path,
) -> tuple[pd.DataFrame, list[dict[str, Any]], dict[str, list[float]], dict[str, Any]]:
    """Runs 5-fold StratifiedGroupKFold across 5 seeds for a specific scheme."""
    n_rows = len(df)
    n_claims = df["claim_id"].nunique()
    classes = sorted(df[target_col].unique().tolist())
    claims_per_class = df.groupby(target_col)["claim_id"].nunique().to_dict()

    effective_n_splits = min(N_SPLITS, min(claims_per_class.values()))

    texts_list = df["text"].tolist()
    labels_list = df[target_col].tolist()
    groups_list = df["claim_id"].tolist()
    record_ids_list = df["record_id"].tolist()
    lang_groups_list = df["lang_group"].tolist()

    cv_summary_records: list[dict[str, Any]] = []
    oof_records: list[dict[str, Any]] = []
    all_fold_scores: dict[str, list[float]] = {m: [] for m in models_to_run}

    seed42_predictions: dict[str, list[str]] = {}

    for model_name in models_to_run:
        fold_macro_f1s: list[float] = []
        seed_oof_f1s: list[float] = []

        for seed_idx, seed in enumerate(CV_SEEDS):
            sgkf = StratifiedGroupKFold(
                n_splits=effective_n_splits,
                shuffle=True,
                random_state=seed,
            )

            oof_preds_for_seed = [""] * n_rows

            for fold_num, (train_idx, test_idx) in enumerate(sgkf.split(texts_list, labels_list, groups=groups_list)):
                y_train = [labels_list[i] for i in train_idx]
                y_test = [labels_list[i] for i in test_idx]

                if model_name in encoder_features:
                    X_feats = encoder_features[model_name]
                    X_train = X_feats[train_idx]
                    X_test = X_feats[test_idx]
                    scaler = StandardScaler()
                    X_train_scaled = scaler.fit_transform(X_train)
                    X_test_scaled = scaler.transform(X_test)

                    clf = LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                        C=1.0,
                        random_state=seed,
                    )
                    clf.fit(X_train_scaled, y_train)
                    preds = clf.predict(X_test_scaled)
                elif model_name == "dummy_majority":
                    clf = DummyClassifier(strategy="most_frequent")
                    clf.fit(train_idx, y_train)
                    preds = clf.predict(test_idx)
                else:
                    X_train = [texts_list[i] for i in train_idx]
                    X_test = [texts_list[i] for i in test_idx]
                    pipe = build_text_pipeline(model_name, random_state=seed)
                    pipe.fit(X_train, y_train)
                    preds = pipe.predict(X_test)

                fold_f1 = float(f1_score(y_test, preds, average="macro", zero_division=0))
                fold_macro_f1s.append(fold_f1)
                all_fold_scores[model_name].append(fold_f1)

                for pos, pred_val in zip(test_idx, preds):
                    oof_preds_for_seed[pos] = pred_val

            # Seed pooled out-of-fold macro-F1
            seed_f1 = float(f1_score(labels_list, oof_preds_for_seed, average="macro", zero_division=0))
            seed_oof_f1s.append(seed_f1)

            if seed == SEED:
                seed42_predictions[model_name] = oof_preds_for_seed

            # Store OOF records
            for idx in range(n_rows):
                oof_records.append({
                    "scheme": scheme_name,
                    "record_id": record_ids_list[idx],
                    "claim_id": groups_list[idx],
                    "seed": seed,
                    "model": model_name,
                    "y_true": labels_list[idx],
                    "y_pred": oof_preds_for_seed[idx],
                    "lang_group": lang_groups_list[idx],
                    "text": texts_list[idx],
                })

        mean_macro_f1 = float(np.mean(fold_macro_f1s))
        std_macro_f1 = float(np.std(fold_macro_f1s, ddof=1)) if len(fold_macro_f1s) > 1 else 0.0
        oof_seed42_f1 = seed_oof_f1s[0]

        cv_summary_records.append({
            "scheme": scheme_name,
            "model": model_name,
            "mean_macro_f1": round(mean_macro_f1, 4),
            "std_macro_f1": round(std_macro_f1, 4),
            "pooled_oof_macro_f1_seed42": round(oof_seed42_f1, 4),
            "n_rows": n_rows,
            "n_claims": n_claims,
            "n_splits": effective_n_splits,
        })

    summary_df = pd.DataFrame(cv_summary_records).sort_values("mean_macro_f1", ascending=False)
    return summary_df, oof_records, all_fold_scores, seed42_predictions


def run_nested_cv(
    df: pd.DataFrame,
    target_col: str,
    candidate_models: list[str],
    encoder_features: dict[str, np.ndarray],
) -> dict[str, Any]:
    """Runs nested cross-validation: outer 5 folds, inner 3-fold model selection."""
    texts = np.array(df["text"].tolist())
    labels = np.array(df[target_col].tolist())
    groups = np.array(df["claim_id"].tolist())

    outer_sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    outer_scores: list[float] = []
    outer_picks: list[str] = []

    for outer_fold, (train_idx, test_idx) in enumerate(outer_sgkf.split(texts, labels, groups=groups)):
        inner_texts = texts[train_idx]
        inner_labels = labels[train_idx]
        inner_groups = groups[train_idx]

        inner_sgkf = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=SEED)
        inner_scores = {m: [] for m in candidate_models}

        for in_train, in_val in inner_sgkf.split(inner_texts, inner_labels, groups=inner_groups):
            y_tr = inner_labels[in_train]
            y_va = inner_labels[in_val]

            for m in candidate_models:
                if m == "dummy_majority":
                    clf = DummyClassifier(strategy="most_frequent")
                    clf.fit(in_train, y_tr)
                    p = clf.predict(in_val)
                elif m in encoder_features:
                    sc = StandardScaler()
                    X_tr = sc.fit_transform(encoder_features[m][train_idx][in_train])
                    X_va = sc.transform(encoder_features[m][train_idx][in_val])
                    clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
                    clf.fit(X_tr, y_tr)
                    p = clf.predict(X_va)
                else:
                    pipe = build_text_pipeline(m, random_state=SEED)
                    pipe.fit(inner_texts[in_train], y_tr)
                    p = pipe.predict(inner_texts[in_val])

                inner_scores[m].append(float(f1_score(y_va, p, average="macro", zero_division=0)))

        # Pick candidate with highest inner mean macro-F1
        best_candidate = max(candidate_models, key=lambda m: float(np.mean(inner_scores[m])))
        outer_picks.append(best_candidate)

        # Train best candidate on entire outer train, evaluate on outer test
        y_train = labels[train_idx]
        y_test = labels[test_idx]

        if best_candidate == "dummy_majority":
            clf = DummyClassifier(strategy="most_frequent")
            clf.fit(train_idx, y_train)
            pred = clf.predict(test_idx)
        elif best_candidate in encoder_features:
            sc = StandardScaler()
            X_tr = sc.fit_transform(encoder_features[best_candidate][train_idx])
            X_te = sc.transform(encoder_features[best_candidate][test_idx])
            clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
            clf.fit(X_tr, y_train)
            pred = clf.predict(X_te)
        else:
            pipe = build_text_pipeline(best_candidate, random_state=SEED)
            pipe.fit(texts[train_idx], y_train)
            pred = pipe.predict(texts[test_idx])

        score = float(f1_score(y_test, pred, average="macro", zero_division=0))
        outer_scores.append(score)

    mean_score = float(np.mean(outer_scores))
    std_score = float(np.std(outer_scores, ddof=1)) if len(outer_scores) > 1 else 0.0

    return {
        "nested_mean_macro_f1": round(mean_score, 4),
        "nested_std_macro_f1": round(std_score, 4),
        "outer_fold_scores": [round(s, 4) for s in outer_scores],
        "outer_selected_models": outer_picks,
        "n_outer_folds": 5,
        "n_inner_folds": 3,
    }


def run_time_holdout(
    df: pd.DataFrame,
    target_col: str,
    best_model_name: str,
    encoder_features: dict[str, np.ndarray],
    out_dir: Path,
) -> dict[str, Any]:
    """Evaluates time-based holdout: earliest 80% claims for training, latest 20% for testing."""
    dated_df = df[df["claim_date"].astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")].copy()
    dated_claims = dated_df.drop_duplicates(subset=["claim_id"]).sort_values("claim_date")
    n_dated = len(dated_claims)

    if n_dated < 10:
        res = {
            "model": best_model_name,
            "train_claims": 0,
            "test_claims": 0,
            "macro_f1": None,
            "status": "skipped",
            "note": f"Fewer than 10 dated claims ({n_dated} found); unstable, descriptive only",
        }
        pd.DataFrame([res]).to_csv(out_dir / "time_holdout.csv", index=False)
        return res

    n_train_claims = int(np.floor((1.0 - TIME_HOLDOUT_FRACTION) * n_dated))
    train_cids = set(dated_claims.iloc[:n_train_claims]["claim_id"])
    test_cids = set(dated_claims.iloc[n_train_claims:]["claim_id"])

    train_data = dated_df[dated_df["claim_id"].isin(train_cids)]
    test_data = dated_df[dated_df["claim_id"].isin(test_cids)]

    train_classes = set(train_data[target_col])
    test_data_filtered = test_data[test_data[target_col].isin(train_classes)]

    if len(test_data_filtered) == 0:
        macro_f1 = 0.0
    else:
        if best_model_name in encoder_features:
            train_idx = train_data.index.to_numpy()
            test_idx = test_data_filtered.index.to_numpy()
            feats = encoder_features[best_model_name]
            sc = StandardScaler()
            X_tr = sc.fit_transform(feats[train_idx])
            X_te = sc.transform(feats[test_idx])
            clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
            clf.fit(X_tr, train_data[target_col])
            preds = clf.predict(X_te)
        elif best_model_name == "dummy_majority":
            clf = DummyClassifier(strategy="most_frequent")
            clf.fit(train_data.index, train_data[target_col])
            preds = clf.predict(test_data_filtered.index)
        else:
            pipe = build_text_pipeline(best_model_name, random_state=SEED)
            pipe.fit(train_data["text"], train_data[target_col])
            preds = pipe.predict(test_data_filtered["text"])

        macro_f1 = float(f1_score(test_data_filtered[target_col], preds, average="macro", zero_division=0))

    res = {
        "model": best_model_name,
        "train_claims": len(train_cids),
        "test_claims": len(test_cids),
        "macro_f1": round(macro_f1, 4),
        "status": "single split, unstable",
        "note": "feasibility pilot on documented claim records; single split, unstable",
    }
    pd.DataFrame([res]).to_csv(out_dir / "time_holdout.csv", index=False)
    with open(out_dir / "time_holdout_results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    return res


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage 3: Train and evaluate models.")
    parser.add_argument(
        "--encoders",
        nargs="*",
        default=["xlmr", "muril"],
        choices=["xlmr", "muril"],
        help="Specify which encoder models to run (e.g. --encoders xlmr or --encoders xlmr muril).",
    )
    parser.add_argument("--skip-encoders", action="store_true", help="Force skipping transformer encoder models.")
    args = parser.parse_args()

    proc_dir = get_processed_data_dir()
    out_dir = get_out_dir()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load dataset: prefer final_labels.csv if present
    final_labels_path = proc_dir / "final_labels.csv"
    dataset_path = proc_dir / "dataset.csv"
    if final_labels_path.exists():
        raw_df = pd.read_csv(final_labels_path)
    elif dataset_path.exists():
        raw_df = pd.read_csv(dataset_path)
    else:
        sys.exit(f"Error: Missing dataset. Looked for {final_labels_path} and {dataset_path}.")

    # Normalize text column
    if "text" not in raw_df.columns and "claim_text" in raw_df.columns:
        raw_df["text"] = raw_df["claim_text"]

    # Map labels to Scheme P and Scheme N
    mapping_path = Path("narrative_mapping.csv")
    if not mapping_path.exists():
        mapping_path = proc_dir / "narrative_mapping.csv"

    df, mapping_meta = map_labels(raw_df, mapping_path)

    # Ingest SHA-256
    dataset_bytes = final_labels_path.read_bytes() if final_labels_path.exists() else dataset_path.read_bytes()
    dataset_hash = hashlib.sha256(dataset_bytes).hexdigest()

    # Pre-extract or load encoder embeddings for full dataset
    selected_encoders = [] if args.skip_encoders else (args.encoders or [])
    skipped_models: dict[str, str] = {}
    encoder_features: dict[str, np.ndarray] = {}

    if not args.skip_encoders and selected_encoders:
        cache_dir = out_dir / ".cache_embeddings"
        for enc_opt in ["xlmr", "muril"]:
            enc_key = f"{enc_opt}_lr"
            if enc_opt not in selected_encoders:
                skipped_models[enc_key] = "Omitted from --encoders flag"
                continue
            hf_name = HF_MODELS[enc_opt]
            try:
                print(f"Loading/extracting encoder embeddings for {enc_key} ({hf_name})...")
                feats = get_encoder_embeddings(hf_name, df["text"].tolist(), cache_dir)
                encoder_features[enc_key] = feats
                print(f"  Successfully prepared embeddings for {enc_key}: shape {feats.shape}")
            except Exception as e:
                msg = f"Failed to load/extract encoder embeddings: {e}"
                print(f"  NOTICE: Skipping {enc_key}: {msg}")
                skipped_models[enc_key] = msg
    else:
        for enc_opt in ["xlmr", "muril"]:
            skipped_models[f"{enc_opt}_lr"] = "Flag --skip-encoders specified or model not in --encoders"

    text_models = [
        "dummy_majority",
        "tfidf_char_lr",
        "tfidf_wordchar_lr",
        "tfidf_char_surface_lr",
    ]
    all_models = text_models + [m for m in ["xlmr_lr", "muril_lr"] if m in encoder_features]

    print(f"\nEvaluating models: {all_models}")
    print(f"Skipped models: {list(skipped_models.keys())}")

    # 1. SCHEME P (PRIMARY)
    print("\n" + "=" * 70)
    print("EVALUATING SCHEME P (PRIMARY PROPOSAL MAPPING)")
    print("=" * 70)
    summary_p, oof_p, fold_scores_p, seed42_preds_p = run_cv_for_scheme(
        df=df,
        target_col="scheme_p",
        scheme_name="scheme_p",
        models_to_run=all_models,
        encoder_features=encoder_features,
        out_dir=out_dir,
    )
    summary_p.to_csv(out_dir / "cv_summary_scheme_p.csv", index=False)
    summary_p.to_csv(out_dir / "cv_summary.csv", index=False)
    print(summary_p.to_string(index=False))

    # 2. SCHEME N (SECONDARY)
    print("\n" + "=" * 70)
    print("EVALUATING SCHEME N (SECONDARY NATIVE LABELS)")
    print("=" * 70)
    summary_n, oof_n, fold_scores_n, _ = run_cv_for_scheme(
        df=df,
        target_col="scheme_n",
        scheme_name="scheme_n",
        models_to_run=all_models,
        encoder_features=encoder_features,
        out_dir=out_dir,
    )
    summary_n.to_csv(out_dir / "cv_summary_scheme_n.csv", index=False)
    print(summary_n.to_string(index=False))

    # 3. SENSITIVITY RUN (EXCLUDING RELATED ROWS)
    print("\n" + "=" * 70)
    print("EVALUATING SENSITIVITY RUN (SCHEME P WITHOUT RELATED ROWS)")
    print("=" * 70)
    df_sens = df[df["relevance"] != "Related"].copy().reset_index(drop=True)
    sens_idx = df[df["relevance"] != "Related"].index.to_numpy()
    sens_encoder_features = {k: v[sens_idx] for k, v in encoder_features.items()}

    summary_sens, oof_sens, fold_scores_sens, _ = run_cv_for_scheme(
        df=df_sens,
        target_col="scheme_p",
        scheme_name="sensitivity_no_related",
        models_to_run=all_models,
        encoder_features=sens_encoder_features,
        out_dir=out_dir,
    )
    summary_sens.to_csv(out_dir / "cv_summary_sensitivity.csv", index=False)
    print(summary_sens.to_string(index=False))

    # Save all OOF predictions
    all_oofs = oof_p + oof_n + oof_sens
    oof_df = pd.DataFrame(all_oofs)
    oof_df.to_csv(out_dir / "oof_predictions.csv", index=False)

    # 4. PAIRED DIFFERENCES VS DUMMY MAJORITY
    paired_rows: list[dict[str, Any]] = []
    dummy_scores_p = np.array(fold_scores_p["dummy_majority"])
    for m in all_models:
        m_scores = np.array(fold_scores_p[m])
        diffs = m_scores - dummy_scores_p
        wins = int(np.sum(diffs > 0))
        mean_diff = float(np.mean(diffs))
        std_diff = float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0
        paired_rows.append({
            "scheme": "scheme_p",
            "model": m,
            "mean_paired_diff": round(mean_diff, 4),
            "std_paired_diff": round(std_diff, 4),
            "fold_win_count": wins,
            "total_folds": len(diffs),
        })
    paired_df = pd.DataFrame(paired_rows)
    paired_df.to_csv(out_dir / "paired_diff_vs_dummy.csv", index=False)
    print("\nPAIRED DIFFERENCES VS DUMMY MAJORITY (SCHEME P):")
    print(paired_df.to_string(index=False))

    # Paired differences between top models
    top_paired_rows: list[dict[str, Any]] = []
    pairs = [
        ("muril_lr", "xlmr_lr"),
        ("muril_lr", "tfidf_char_lr"),
        ("xlmr_lr", "tfidf_char_lr"),
    ]
    for m_a, m_b in pairs:
        if m_a in fold_scores_p and m_b in fold_scores_p:
            s_a = np.array(fold_scores_p[m_a])
            s_b = np.array(fold_scores_p[m_b])
            diffs = s_a - s_b
            wins_a = int(np.sum(diffs > 0))
            ties = int(np.sum(diffs == 0))
            wins_b = int(np.sum(diffs < 0))
            top_paired_rows.append({
                "model_a": m_a,
                "model_b": m_b,
                "mean_paired_diff": round(float(np.mean(diffs)), 4),
                "std_paired_diff": round(float(np.std(diffs, ddof=1)) if len(diffs) > 1 else 0.0, 4),
                "model_a_wins": wins_a,
                "ties": ties,
                "model_b_wins": wins_b,
                "total_folds": len(diffs),
            })
    top_paired_df = pd.DataFrame(top_paired_rows)
    top_paired_df.to_csv(out_dir / "paired_diff_top_models.csv", index=False)
    print("\nPAIRED DIFFERENCES BETWEEN TOP MODELS (SCHEME P):")
    print(top_paired_df.to_string(index=False))

    # 5. PER-CLASS METRICS & CONFUSION MATRICES (SCHEME P, SEED 42)
    classes_p = sorted(df["scheme_p"].unique().tolist())
    all_class_rows: list[dict[str, Any]] = []
    y_true_p = df["scheme_p"].tolist()

    for m in all_models:
        preds = seed42_preds_p[m]
        rep = classification_report(y_true_p, preds, output_dict=True, zero_division=0)
        for c in classes_p:
            if c in rep:
                all_class_rows.append({
                    "model": m,
                    "class": c,
                    "precision": round(rep[c]["precision"], 4),
                    "recall": round(rep[c]["recall"], 4),
                    "f1": round(rep[c]["f1-score"], 4),
                    "support": int(rep[c]["support"]),
                })
        # Single model per-class CSV
        m_class_df = pd.DataFrame([r for r in all_class_rows if r["model"] == m])
        m_class_df.to_csv(out_dir / f"per_class_{m}.csv", index=False)

        # Confusion Matrix
        cm = confusion_matrix(y_true_p, preds, labels=classes_p)
        cm_df = pd.DataFrame(cm, index=classes_p, columns=classes_p)
        cm_df.to_csv(out_dir / f"confusion_{m}.csv")

    per_class_df = pd.DataFrame(all_class_rows)
    per_class_df.to_csv(out_dir / "per_class_metrics.csv", index=False)

    # 6. LANGUAGE GROUP SCORES (SCHEME P, SEED 42)
    group_rows: list[dict[str, Any]] = []
    for m in all_models:
        preds = seed42_preds_p[m]
        for lg in sorted(df["lang_group"].unique()):
            mask = (df["lang_group"] == lg).to_numpy()
            sub_true = [y_true_p[i] for i in range(len(df)) if mask[i]]
            sub_pred = [preds[i] for i in range(len(df)) if mask[i]]
            n_sub = len(sub_true)
            if n_sub >= MIN_ROWS_FOR_GROUP_SCORE:
                score = round(float(f1_score(sub_true, sub_pred, average="macro", zero_division=0)), 4)
                status = "scored"
            else:
                score = None
                status = "too few rows; describe errors qualitatively"
            group_rows.append({
                "model": m,
                "lang_group": lg,
                "n_rows": n_sub,
                "macro_f1": score,
                "status": status,
            })
    group_df = pd.DataFrame(group_rows)
    group_df.to_csv(out_dir / "group_scores.csv", index=False)
    print("\nLANGUAGE GROUP EVALUATION:")
    print(group_df.to_string(index=False))

    # 7. TIME HOLDOUT CHECK
    non_dummy = summary_p[summary_p["model"] != "dummy_majority"]
    best_candidate_name = non_dummy.iloc[0]["model"] if not non_dummy.empty else "tfidf_char_lr"
    time_results = run_time_holdout(df, "scheme_p", best_candidate_name, encoder_features, out_dir)
    print(f"\nTIME HOLDOUT CHECK ({best_candidate_name}): {time_results}")

    # 8. NESTED CV ESTIMATE (SCHEME P)
    print("\nRUNNING NESTED CV ON SCHEME P...")
    nested_res = run_nested_cv(df, "scheme_p", all_models, encoder_features)
    with open(out_dir / "nested_cv_results.json", "w", encoding="utf-8") as f:
        json.dump(nested_res, f, indent=2)
    print(f"NESTED CV RESULTS: {nested_res['nested_mean_macro_f1']} +/- {nested_res['nested_std_macro_f1']}")

    # 9. MODEL SELECTION & FIT FINAL ARTIFACT
    dummy_mean = float(summary_p[summary_p["model"] == "dummy_majority"]["mean_macro_f1"].iloc[0])
    dummy_sd = float(summary_p[summary_p["model"] == "dummy_majority"]["std_macro_f1"].iloc[0])

    selected_model_row = non_dummy.iloc[0]
    selected_model_name = selected_model_row["model"]
    selected_mean = float(selected_model_row["mean_macro_f1"])

    within_one_sd = (selected_mean <= dummy_mean + dummy_sd)
    selection_assessment = (
        "no demonstrated advantage over the baseline; best available"
        if within_one_sd else
        "demonstrated advantage over dummy baseline"
    )

    print(f"\nSELECTED BEST MODEL: {selected_model_name} (Mean Macro-F1 = {selected_mean:.4f})")
    print(f"Selection Assessment: {selection_assessment}")

    # Fit final model on all 97 rows of Scheme P
    final_model_dir = out_dir / "final_model"
    final_model_dir.mkdir(parents=True, exist_ok=True)

    if selected_model_name in encoder_features:
        scaler = StandardScaler()
        X_all_scaled = scaler.fit_transform(encoder_features[selected_model_name])
        final_clf = LogisticRegression(max_iter=2000, class_weight="balanced", C=1.0, random_state=SEED)
        final_clf.fit(X_all_scaled, df["scheme_p"])

        model_payload = {
            "model_type": selected_model_name,
            "architecture": "frozen_encoder_logistic_regression",
            "hf_model_name": HF_MODELS["muril" if "muril" in selected_model_name else "xlmr"],
            "scaler": scaler,
            "clf": final_clf,
            "classes": classes_p,
            "n_rows": len(df),
            "n_claims": df["claim_id"].nunique(),
            "caveat": CAVEAT_SENTENCE,
        }
    else:
        final_pipe = build_text_pipeline(selected_model_name, random_state=SEED)
        final_pipe.fit(df["text"], df["scheme_p"])
        model_payload = {
            "model_type": selected_model_name,
            "architecture": "pipeline",
            "pipeline": final_pipe,
            "classes": classes_p,
            "n_rows": len(df),
            "n_claims": df["claim_id"].nunique(),
            "caveat": CAVEAT_SENTENCE,
        }

    joblib.dump(model_payload, final_model_dir / "model.joblib")

    # Also fit and save tfidf_char_lr as fallback lightweight model
    pipe_tfidf = build_text_pipeline("tfidf_char_lr", random_state=SEED)
    pipe_tfidf.fit(df["text"], df["scheme_p"])
    joblib.dump({
        "model_type": "tfidf_char_lr",
        "pipeline": pipe_tfidf,
        "classes": classes_p,
        "n_rows": len(df),
        "n_claims": df["claim_id"].nunique(),
        "caveat": CAVEAT_SENTENCE,
    }, final_model_dir / "tfidf_char_lr.joblib")

    # 10. RQ1 DESCRIPTIVE CROSS-TABULATIONS
    if "content_form_native" in df.columns and "narrative_native" in df.columns:
        rq1_native = pd.crosstab(df["content_form_native"], df["narrative_native"], margins=True)
        rq1_native.to_csv(out_dir / "rq1_form_by_narrative_native.csv")

        rq1_mapped = pd.crosstab(df["content_form_native"], df["scheme_p"], margins=True)
        rq1_mapped.to_csv(out_dir / "rq1_form_by_narrative_mapped.csv")
        print("\nRQ1 Cross-tabulations saved.")

    # 11. SAVE RUN_INFO.JSON
    claims_per_class_p = df.groupby("scheme_p")["claim_id"].nunique().to_dict()
    rows_per_class_p = df.groupby("scheme_p").size().to_dict()
    effective_n_splits = min(N_SPLITS, min(claims_per_class_p.values()))

    run_info = {
        "dataset_sha256": dataset_hash,
        "n_rows": len(df),
        "n_claims": df["claim_id"].nunique(),
        "classes_scheme_p": classes_p,
        "claims_per_class_scheme_p": claims_per_class_p,
        "rows_per_class_scheme_p": rows_per_class_p,
        "rare_merged_p": mapping_meta["scheme_p_rare_merged"],
        "rare_merged_n": mapping_meta["scheme_n_rare_merged"],
        "cv_seeds": CV_SEEDS,
        "n_splits_used": effective_n_splits,
        "models_evaluated": all_models,
        "skipped_models": skipped_models,
        "selected_model": {
            "name": selected_model_name,
            "mean_macro_f1": selected_mean,
            "assessment": selection_assessment,
        },
        "nested_cv": nested_res,
        "time_holdout": time_results,
        "libraries": {
            "python": platform.python_version(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit-learn": __import__("sklearn").__version__,
            "joblib": joblib.__version__,
        },
        "caveat": CAVEAT_SENTENCE,
    }
    with open(out_dir / "run_info.json", "w", encoding="utf-8") as f:
        json.dump(run_info, f, indent=2)

    print(f"\nStage 3 training & evaluation complete. Outputs saved in {out_dir}")


if __name__ == "__main__":
    main()
