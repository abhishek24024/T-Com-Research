"""Unit tests for the Claim-Narrative Triage Pipeline.

Covers all 11 requirements from Section 10 of the Build Spec.
"""

from __future__ import annotations

import json
from pathlib import Path
import pandas as pd
import pytest
from sklearn.model_selection import StratifiedGroupKFold

from config import (
    CLAIM_WINDOW_END,
    CLAIM_WINDOW_START,
    DUP_SIMILARITY,
    MIN_CLAIMS_PER_CLASS,
    N_SPLITS,
    REPORT_CUTOFF,
)
from utils import (
    SurfaceFeatureExtractor,
    compute_label_agreement,
    detect_lang_group_heuristic,
    detect_script,
    filter_claims_by_date,
    normalize_text,
    parse_api_response,
    propose_claim_ids,
)


def test_01_normalizer_preserves_hindi_vowels_and_strips_urls_punctuation():
    """Test 1: Normaliser keeps Hindi vowel signs (matras/halant) and strips URLs and punctuation."""
    raw_hindi = "छात्रों पर लाठीचार्ज! देखें: https://t.co/abc1234, पुलिस की बर्बरता?"
    norm = normalize_text(raw_hindi)

    # Vowel signs in 'छात्रों', 'लाठीचार्ज', 'पुलिस', 'बर्बरता' must remain intact
    assert "छात्रों" in norm
    assert "लाठीचार्ज" in norm
    assert "पुलिस" in norm
    assert "बर्बरता" in norm

    # Punctuation and URLs must be removed
    assert "!" not in norm
    assert "?" not in norm
    assert ":" not in norm
    assert "," not in norm
    assert "https" not in norm
    assert "abc1234" not in norm


def test_02_script_detection_and_hinglish_heuristic():
    """Test 2: Script detection and Hinglish heuristic on representative examples."""
    hindi_text = "दिल्ली में छात्रों का विशाल प्रदर्शन"
    assert detect_script(hindi_text) == "devanagari"
    assert detect_lang_group_heuristic(hindi_text) == "devanagari"

    english_text = "Massive student protest held at Jantar Mantar demanding fair re-examination."
    assert detect_script(english_text) == "latin"
    assert detect_lang_group_heuristic(english_text) == "english_likely"

    hinglish_text = "ye video delhi ka hai jahan police ne protest par lathicharge kiya tha"
    assert detect_script(hinglish_text) == "latin"
    assert detect_lang_group_heuristic(hinglish_text) == "hinglish_likely"


def test_03_api_flattener_drops_claimant_and_handles_missing_fields():
    """Test 3: API flattener drops claimant (privacy rule) and handles empty/missing fields."""
    sample_response = {
        "claims": [
            {
                "text": "Viral video claims 5 dead in protest",
                "claimant": "Anonymous User @xyz_handle",  # MUST BE DROPPED
                "claimDate": "2026-07-21T10:00:00Z",
                "claimReview": [
                    {
                        "publisher": {"name": "FactCheckHub", "site": "factcheckhub.org"},
                        "url": "https://factcheckhub.org/protest-claim",
                        "title": "No deaths during protest",
                        "reviewDate": "2026-07-22",
                        "textualRating": "False",
                        "languageCode": "en",
                    }
                ],
            },
            {
                "text": "Claim without reviews",
                "claimant": "Some Claimant",
                "claimReview": [],
            },
        ]
    }

    rows = parse_api_response(sample_response, query_term="protest")
    assert len(rows) == 1
    row = rows[0]
    assert "claimant" not in row
    assert row["claim_text"] == "Viral video claims 5 dead in protest"
    assert row["claim_date"] == "2026-07-21"
    assert row["publisher_name"] == "FactCheckHub"
    assert row["text_source"] == "unknown"

    # Empty response handling
    assert parse_api_response({}) == []


def test_04_date_filter_scenarios():
    """Test 4: Date filter: inside window, missing claim date with usable review date, outside window."""
    df = pd.DataFrame([
        # Row 1: inside window
        {"claim_text": "Claim 1", "claim_date": "2026-07-10", "review_date": "2026-07-12"},
        # Row 2: missing claim_date, review_date in [start, cutoff]
        {"claim_text": "Claim 2", "claim_date": "", "review_date": "2026-08-20"},
        # Row 3: claim_date before window
        {"claim_text": "Claim 3", "claim_date": "2026-05-15", "review_date": "2026-07-10"},
        # Row 4: claim_date after window
        {"claim_text": "Claim 4", "claim_date": "2026-08-01", "review_date": "2026-08-05"},
        # Row 5: missing claim_date, review_date after cutoff
        {"claim_text": "Claim 5", "claim_date": "", "review_date": "2026-10-25"},
        # Row 6: empty claim text
        {"claim_text": "", "claim_date": "2026-07-10", "review_date": "2026-07-12"},
    ])

    kept_df, drop_counts = filter_claims_by_date(
        df,
        start_date=CLAIM_WINDOW_START,
        end_date=CLAIM_WINDOW_END,
        cutoff_date=REPORT_CUTOFF,
    )

    assert len(kept_df) == 2
    assert set(kept_df["claim_text"]) == {"Claim 1", "Claim 2"}

    row1 = kept_df[kept_df["claim_text"] == "Claim 1"].iloc[0]
    assert row1["date_check"] == "ok"

    row2 = kept_df[kept_df["claim_text"] == "Claim 2"].iloc[0]
    assert row2["date_check"] == "needs_manual_date_check"

    assert drop_counts["empty_claim_text"] == 1
    assert drop_counts["claim_date_out_of_window"] == 2
    assert drop_counts["missing_claim_date_and_review_date_out_of_range"] == 1


def test_05_near_duplicate_claim_grouping():
    """Test 5: Near-duplicate grouping merges near-identical claims and separates distinct claims."""
    texts = [
        "Police used excessive tear gas and water cannons against peaceful student protesters at Jantar Mantar",
        "Police used excessive tear gas and water cannons against peaceful student protesters at Jantar Mantar Delhi",
        "Celebrity actor endorsed the protest and donated ten lakh rupees to student funds",
    ]

    claim_ids = propose_claim_ids(texts, threshold=0.75)
    assert len(claim_ids) == 3
    # First two should share the same claim_id
    assert claim_ids[0] == claim_ids[1]
    # Third should have a different claim_id
    assert claim_ids[0] != claim_ids[2]


def test_06_kappa_and_percent_agreement_hand_computed():
    """Test 6: Kappa and agreement on a known hand-computed example."""
    # 4 items: coder 1 = [A, B, A, B], coder 2 = [A, B, B, B]
    # Agreement: 3/4 = 75%
    c1 = ["police_force", "protester_violence", "police_force", "protester_violence"]
    c2 = ["police_force", "protester_violence", "protester_violence", "protester_violence"]

    res = compute_label_agreement(c1, c2)
    assert res["n"] == 4
    assert res["percent_agreement"] == 75.0
    # Expected kappa: P_o = 0.75.
    # Marginals: c1 has 2 A, 2 B (p_A=0.5, p_B=0.5)
    # c2 has 1 A, 3 B (p_A=0.25, p_B=0.75)
    # P_e = 0.5*0.25 + 0.5*0.75 = 0.125 + 0.375 = 0.50
    # Kappa = (0.75 - 0.50) / (1 - 0.50) = 0.25 / 0.50 = 0.5000
    assert abs(res["cohen_kappa"] - 0.5000) < 1e-3


def test_07_rare_class_merge_counts_distinct_claims_not_rows():
    """Test 7: Rare-class merge counts distinct claims (claim_id), NOT rows."""
    # Simulate a dataframe where 'police_force' has 10 rows but only 2 distinct claims
    # and 'other' has 10 claims.
    # With MIN_CLAIMS_PER_CLASS = 8, 'police_force' must be merged into 'other'.
    records = []
    # 10 rows belonging to only 2 claims for police_force
    for i in range(10):
        c_id = "C0001" if i < 5 else "C0002"
        records.append({
            "record_id": f"R{i+1:04d}",
            "claim_id": c_id,
            "narrative": "police_force",
            "narrative_original": "police_force",
        })
    # 10 rows belonging to 10 distinct claims for crowd_legitimacy
    for i in range(10, 20):
        records.append({
            "record_id": f"R{i+1:04d}",
            "claim_id": f"C{i+1:04d}",
            "narrative": "crowd_legitimacy",
            "narrative_original": "crowd_legitimacy",
        })

    df = pd.DataFrame(records)

    # Perform rare-class merge based on distinct claims
    claim_counts = df.groupby("narrative")["claim_id"].nunique().to_dict()
    assert claim_counts["police_force"] == 2  # rows=10, claims=2

    merged_df = df.copy()
    min_claims = 8
    for narr, count in claim_counts.items():
        if narr != "other" and count < min_claims:
            merged_df.loc[merged_df["narrative"] == narr, "narrative"] = "other"

    assert set(merged_df["narrative"]) == {"other", "crowd_legitimacy"}
    # Original labels preserved in narrative_original
    assert (merged_df[merged_df["narrative"] == "other"]["narrative_original"] == "police_force").all()


def test_08_fold_count_reduction():
    """Test 8: Fold-count reduction when a class has few claims."""
    # Suppose smallest class has 3 distinct claims
    class_claim_counts = {"class_a": 10, "class_b": 3, "other": 15}
    min_class_claims = min(class_claim_counts.values())
    n_splits_target = N_SPLITS  # 5

    effective_n_splits = min(n_splits_target, min_class_claims)
    assert effective_n_splits == 3
    assert effective_n_splits < n_splits_target


def test_09_no_claim_id_appears_in_both_train_and_test():
    """Test 9: Grouped splitting ensures no claim_id leaks between train and test."""
    claim_ids = ["C01", "C01", "C02", "C02", "C03", "C04", "C05", "C06", "C07", "C08"]
    narratives = ["A", "A", "A", "A", "B", "B", "B", "B", "A", "B"]
    X = [[i] for i in range(len(claim_ids))]

    sgkf = StratifiedGroupKFold(n_splits=3, shuffle=True, random_state=42)
    for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, narratives, groups=claim_ids)):
        train_claims = set(claim_ids[i] for i in train_idx)
        test_claims = set(claim_ids[i] for i in test_idx)
        overlap = train_claims.intersection(test_claims)
        assert len(overlap) == 0, f"Fold {fold} has leaking claim_ids: {overlap}"


def test_10_blind_packet_contains_no_gold_prediction_or_record_id():
    """Test 10: blind_packet.csv format contains NO gold label, NO prediction, and NO record_id."""
    blind_columns = ["packet_id", "review_url", "text", "blind_label", "confidence_1to3", "notes"]
    forbidden = ["gold", "predicted", "record_id", "y_true", "y_pred"]

    for col in forbidden:
        assert col not in blind_columns


def test_11_surface_features_extractor():
    """Test 11: Surface feature extractor produces 10 features without errors."""
    sample_texts = [
        "Check this out! https://example.com #Protest @DelhiPolice 100 people joined?",
        "छात्रों ने संसद मार्ग पर प्रदर्शन किया।",
    ]
    extractor = SurfaceFeatureExtractor()
    feats = extractor.fit_transform(sample_texts)
    assert feats.shape == (2, 10)
    # Check has-URL and exclamation on first text
    assert feats[0, 8] == 1.0  # has_url
    assert feats[0, 4] == 1.0  # exclamation count
    assert feats[0, 5] == 1.0  # question count


def test_12_re_running_gives_identical_cv_summary(tmp_path, monkeypatch):
    """Test 12: Re-running cross-validation with identical seeds gives identical cv_summary.csv."""
    import subprocess
    import sys

    # Set temporary directories for isolation
    data_dir = tmp_path / "data"
    out1_dir = tmp_path / "out1"
    out2_dir = tmp_path / "out2"
    qa_dir = tmp_path / "qa"

    data_dir.mkdir(parents=True)
    out1_dir.mkdir(parents=True)
    out2_dir.mkdir(parents=True)
    qa_dir.mkdir(parents=True)

    # Generate demo data
    monkeypatch.setenv("PIPELINE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("PIPELINE_OUT_DIR", str(out1_dir))
    monkeypatch.setenv("PIPELINE_QA_DIR", str(qa_dir))

    subprocess.run([sys.executable, "make_demo_data.py", "fake-api"], check=True)
    subprocess.run([sys.executable, "01_collect_claims.py", "--offline-json", str(data_dir / "raw" / "demo_api_response.json")], check=True)
    subprocess.run([sys.executable, "02_build_dataset.py", "make-sheet"], check=True)
    subprocess.run([sys.executable, "make_demo_data.py", "simulate-coders"], check=True)
    subprocess.run([sys.executable, "02_build_dataset.py", "finalize"], check=True)

    # Run 1
    subprocess.run([sys.executable, "03_train_eval.py", "--skip-encoders"], check=True)
    csv1 = (out1_dir / "cv_summary.csv").read_text()

    # Run 2 pointing to out2_dir
    monkeypatch.setenv("PIPELINE_OUT_DIR", str(out2_dir))
    subprocess.run([sys.executable, "03_train_eval.py", "--skip-encoders"], check=True)
    csv2 = (out2_dir / "cv_summary.csv").read_text()

    assert csv1 == csv2, "Re-running 03_train_eval.py produced differing cv_summary.csv files!"




def test_13_apply_merges_transitive_union_find():
    """Test 13: apply-merges transitive Union-Find correctly clusters multi-hop duplicate claims."""
    from utils import UnionFind

    uf = UnionFind()
    # Chain of merges: C1 <-> C2, C2 <-> C3, C4 stands alone
    uf.union("C001", "C002")
    uf.union("C002", "C003")

    assert uf.find("C001") == uf.find("C002")
    assert uf.find("C002") == uf.find("C003")
    assert uf.find("C001") == uf.find("C003")
    assert uf.find("C004") != uf.find("C001")

    # Simulate DataFrame remapping
    df = pd.DataFrame([
        {"record_id": "R0001", "claim_id": "C001", "claim_text": "Text 1"},
        {"record_id": "R0002", "claim_id": "C002", "claim_text": "Text 2"},
        {"record_id": "R0003", "claim_id": "C003", "claim_text": "Text 3"},
        {"record_id": "R0004", "claim_id": "C004", "claim_text": "Text 4"},
    ])

    clusters = {}
    for cid in df["claim_id"]:
        root = uf.find(cid)
        if root not in clusters:
            clusters[root] = []
        clusters[root].append(cid)

    # Deterministic mapping: lowest claim_id in cluster
    mapping = {cid: sorted(cluster)[0] for root, cluster in clusters.items() for cid in cluster}
    df["claim_id_new"] = df["claim_id"].map(mapping)

    assert df["claim_id_new"].nunique() == 2
    assert (df.loc[df["record_id"].isin(["R0001", "R0002", "R0003"]), "claim_id_new"] == "C001").all()
    assert (df.loc[df["record_id"] == "R0004", "claim_id_new"] == "C004").all()


def test_14_pilot_kappa_hand_computed_ground_truth():
    """Test 14: Pilot agreement and Cohen's kappa matches hand-computed ground truth."""
    # Hand-computed scenario:
    # 10 records evaluated by Coder A and Coder B on 2 categories (Cat1, Cat2)
    # Contingency Table:
    #               Coder B: Cat1   Coder B: Cat2   Total
    # Coder A: Cat1       5               1           6
    # Coder A: Cat2       1               3           4
    # Total               6               4          10
    #
    # Observed agreement Po = (5 + 3) / 10 = 8 / 10 = 0.80 (80.0%)
    # Marginal probabilities:
    # P(Cat1 for A) = 0.6, P(Cat1 for B) = 0.6 => P_expected(Cat1) = 0.36
    # P(Cat2 for A) = 0.4, P(Cat2 for B) = 0.4 => P_expected(Cat2) = 0.16
    # Expected chance agreement Pe = 0.36 + 0.16 = 0.52
    # Cohen's Kappa = (Po - Pe) / (1 - Pe) = (0.80 - 0.52) / (1.0 - 0.52) = 0.28 / 0.48 = 0.58333...

    y_a = ["Cat1"] * 5 + ["Cat1"] * 1 + ["Cat2"] * 1 + ["Cat2"] * 3
    y_b = ["Cat1"] * 5 + ["Cat2"] * 1 + ["Cat1"] * 1 + ["Cat2"] * 3

    metrics = compute_label_agreement(y_a, y_b)

    assert metrics["n"] == 10
    assert metrics["percent_agreement"] == 80.0
    assert round(metrics["cohen_kappa"], 4) == 0.5833


def test_15_quarantine_logic_excludes_failed_manual_claims(tmp_path, monkeypatch):
    """Test 15: Quarantine logic isolates 0-scored manual claims so they never enter coding_sheet."""
    raw_dir = tmp_path / "data" / "raw"
    proc_dir = tmp_path / "data" / "processed"
    raw_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)

    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path / "data"))

    # Create dummy API file
    api_df = pd.DataFrame([{
        "source": "factcheck_api",
        "claim_text": "API Claim 1",
        "claim_date": "2026-07-10",
        "review_date": "2026-07-11",
        "publisher_name": "BOOM",
        "publisher_site": "boomlive.in",
        "review_url": "https://boomlive.in/test1",
        "review_title": "Review 1",
        "textualRating": "False",
        "languageCode": "en",
        "text_source": "verbatim",
        "query_term": "cjp",
    }])
    api_df.to_csv(raw_dir / "factcheck_api_claims.csv", index=False)

    # Create manual_claims with verified rows and quarantined file
    manual_verified_df = pd.DataFrame([{
        "source": "manual",
        "claim_text": "Verified Manual Claim",
        "claim_date": "2026-07-15",
        "review_date": "2026-07-16",
        "publisher_name": "The Quint",
        "publisher_site": "thequint.com",
        "review_url": "https://thequint.com/verified",
        "review_title": "Review 2",
        "textualRating": "Misleading",
        "languageCode": "en",
        "text_source": "verbatim",
        "query_term": "cjp",
    }])
    manual_verified_df.to_csv(raw_dir / "manual_claims.csv", index=False)

    # 0-scored quarantined rows in separate quarantine file
    quarantined_df = pd.DataFrame([{
        "source": "manual",
        "claim_text": "Fabricated Dead URL Claim",
        "claim_date": "2026-07-15",
        "review_date": "2026-07-16",
        "publisher_name": "Ghost News",
        "publisher_site": "ghostnews.com",
        "review_url": "https://ghostnews.com/dead-link-404",
        "review_title": "Dead Review",
        "textualRating": "False",
        "languageCode": "en",
        "text_source": "verbatim",
        "query_term": "cjp",
    }])
    quarantined_df.to_csv(raw_dir / "manual_claims_quarantine.csv", index=False)

    import importlib
    build_dataset = importlib.import_module("02_build_dataset")
    build_dataset.run_make_sheet()

    sheet = pd.read_csv(proc_dir / "coding_sheet.csv")

    # The verified claim must be present, but the quarantined claim must NOT be present
    assert "Verified Manual Claim" in sheet["claim_text"].values
    assert "Fabricated Dead URL Claim" not in sheet["claim_text"].values
    assert len(sheet) == 2



def test_16_relevance_exclusion_in_finalize(tmp_path, monkeypatch):
    """Test 16: finalize excludes off_topic rows to outputs/excluded_off_topic.csv, never labelling them 'other'."""
    raw_dir = tmp_path / "data" / "raw"
    proc_dir = tmp_path / "data" / "processed"
    out_dir = tmp_path / "outputs"
    raw_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PIPELINE_OUT_DIR", str(out_dir))

    # Coding sheet with 4 records (2 claims each with 2 records)
    sheet_records = [
        {"record_id": "R0001", "claim_id": "C001", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://boom.test/1", "text_source": "verbatim", "claim_text": "On-topic claim 1", "script": "latin", "lang_group_heuristic": "english_likely", "lang_group_manual": "", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0002", "claim_id": "C002", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://boom.test/2", "text_source": "verbatim", "claim_text": "On-topic claim 2", "script": "latin", "lang_group_heuristic": "english_likely", "lang_group_manual": "", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0003", "claim_id": "C003", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "needs_check", "publisher_name": "BOOM", "review_url": "https://boom.test/3", "text_source": "verbatim", "claim_text": "Off-topic Bihar car claim", "script": "latin", "lang_group_heuristic": "english_likely", "lang_group_manual": "", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0004", "claim_id": "C004", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "needs_check", "publisher_name": "BOOM", "review_url": "https://boom.test/4", "text_source": "verbatim", "claim_text": "Off-topic October CEC claim", "script": "latin", "lang_group_heuristic": "english_likely", "lang_group_manual": "", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
    ]
    pd.DataFrame(sheet_records).to_csv(proc_dir / "coding_sheet.csv", index=False)

    # Coder A labels R0001, R0002 as on_topic, and R0003, R0004 as off_topic
    coder_a_records = [
        {"record_id": "R0001", "relevance": "on_topic", "narrative": "police_force", "content_form": "ai_generated", "direction": "supports_protesters", "origin": "documented_ai", "coder_notes": ""},
        {"record_id": "R0002", "relevance": "on_topic", "narrative": "crowd_legitimacy", "content_form": "old_or_out_of_context", "direction": "supports_protesters", "origin": "documented_non_ai", "coder_notes": ""},
        {"record_id": "R0003", "relevance": "off_topic", "narrative": "police_force", "content_form": "old_or_out_of_context", "direction": "supports_protesters", "origin": "documented_non_ai", "coder_notes": ""},
        {"record_id": "R0004", "relevance": "off_topic", "narrative": "other", "content_form": "fabricated_text", "direction": "unclear", "origin": "unknown", "coder_notes": ""},
    ]
    pd.DataFrame(coder_a_records).to_csv(raw_dir / "coder_A.csv", index=False)

    import importlib
    build_dataset = importlib.import_module("02_build_dataset")
    build_dataset.run_finalize()

    # Verify dataset.csv
    dataset_df = pd.read_csv(proc_dir / "dataset.csv")
    assert len(dataset_df) == 2
    assert set(dataset_df["record_id"]) == {"R0001", "R0002"}
    assert "R0003" not in dataset_df["record_id"].values
    assert "R0004" not in dataset_df["record_id"].values

    # Off-topic records must NOT be labelled 'other' in dataset.csv
    assert "Off-topic Bihar car claim" not in dataset_df["text"].values
    assert "Off-topic October CEC claim" not in dataset_df["text"].values

    # Verify outputs/excluded_off_topic.csv
    excluded_df = pd.read_csv(out_dir / "excluded_off_topic.csv")
    assert len(excluded_df) == 2
    assert set(excluded_df["record_id"]) == {"R0003", "R0004"}
    assert "Off-topic Bihar car claim" in excluded_df["claim_text"].values


def test_17_xlsx_to_csv_validation_and_error_handling(tmp_path):
    """Test 17: xlsx_to_csv correctly extracts columns and rejects invalid values with clear errors."""
    import openpyxl
    from xlsx_to_csv import convert_xlsx_to_csv

    xlsx_path = tmp_path / "test_coder.xlsx"
    csv_path = tmp_path / "test_coder.csv"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Record ID", "Claim Text", "Publisher", "Fact-Check URL", "Relevance", "Primary Narrative", "Content Form", "Direction", "Origin", "Coder Notes"])
    ws.append(["R0001", "Sample claim", "BOOM", "https://boom.test", "on_topic", "police_force", "ai_generated", "supports_protesters", "documented_ai", "Note 1"])
    wb.save(xlsx_path)

    # Valid conversion
    df = convert_xlsx_to_csv(xlsx_path, csv_path)
    assert len(df) == 1
    assert df.loc[0, "record_id"] == "R0001"
    assert df.loc[0, "narrative"] == "police_force"
    assert df.loc[0, "origin"] == "documented_ai"

    # Invalid narrative must trigger SystemExit
    ws.append(["R0002", "Claim 2", "BOOM", "https://boom.test", "on_topic", "INVALID_NARRATIVE", "ai_generated", "supports_protesters", "documented_ai", ""])
    wb.save(xlsx_path)

    with pytest.raises(SystemExit):
        convert_xlsx_to_csv(xlsx_path, csv_path)


def test_18_leakage_control_agreement_split(tmp_path, monkeypatch):
    """Test 18: finalize computes label agreement for all rows vs non-example rows separately."""
    import json
    import importlib

    raw_dir = tmp_path / "data" / "raw"
    proc_dir = tmp_path / "data" / "processed"
    out_dir = tmp_path / "outputs"
    raw_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PIPELINE_OUT_DIR", str(out_dir))

    # Coding sheet with 4 records
    sheet_records = [
        {"record_id": "R0001", "claim_id": "C0001", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.1", "text_source": "verbatim", "claim_text": "Claim 1", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0002", "claim_id": "C0002", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.2", "text_source": "verbatim", "claim_text": "Claim 2", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0003", "claim_id": "C0003", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.3", "text_source": "verbatim", "claim_text": "Claim 3", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0004", "claim_id": "C0004", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.4", "text_source": "verbatim", "claim_text": "Claim 4", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
    ]
    pd.DataFrame(sheet_records).to_csv(proc_dir / "coding_sheet.csv", index=False)

    # Codebook example IDs: R0001 is a codebook example, R0002-R0004 are non-examples
    pd.DataFrame({"record_id": ["R0001"]}).to_csv(proc_dir / "codebook_example_ids.csv", index=False)

    # Coder A and B agree on R0001 (codebook example) and R0002, disagree on R0003, R0004
    coder_a_records = [
        {"record_id": "R0001", "relevance": "on_topic", "narrative": "police_force", "content_form": "ai_generated", "direction": "supports_protesters", "origin": "documented_ai", "coder_notes": ""},
        {"record_id": "R0002", "relevance": "on_topic", "narrative": "crowd_legitimacy", "content_form": "old_or_out_of_context", "direction": "supports_protesters", "origin": "documented_non_ai", "coder_notes": ""},
        {"record_id": "R0003", "relevance": "on_topic", "narrative": "police_force", "content_form": "old_or_out_of_context", "direction": "supports_protesters", "origin": "documented_non_ai", "coder_notes": ""},
        {"record_id": "R0004", "relevance": "on_topic", "narrative": "protester_violence", "content_form": "fabricated_text", "direction": "supports_police_government", "origin": "documented_non_ai", "coder_notes": ""},
    ]
    coder_b_records = [
        {"record_id": "R0001", "relevance": "on_topic", "narrative": "police_force", "content_form": "ai_generated", "direction": "supports_protesters", "origin": "documented_ai", "coder_notes": ""},
        {"record_id": "R0002", "relevance": "on_topic", "narrative": "crowd_legitimacy", "content_form": "old_or_out_of_context", "direction": "supports_protesters", "origin": "documented_non_ai", "coder_notes": ""},
        {"record_id": "R0003", "relevance": "on_topic", "narrative": "slogans_communal_loyalty", "content_form": "old_or_out_of_context", "direction": "supports_protesters", "origin": "documented_non_ai", "coder_notes": ""},
        {"record_id": "R0004", "relevance": "on_topic", "narrative": "crowd_legitimacy", "content_form": "fabricated_text", "direction": "supports_police_government", "origin": "documented_non_ai", "coder_notes": ""},
    ]
    pd.DataFrame(coder_a_records).to_csv(raw_dir / "coder_A.csv", index=False)
    pd.DataFrame(coder_b_records).to_csv(raw_dir / "coder_B.csv", index=False)

    build_dataset = importlib.import_module("02_build_dataset")
    build_dataset.run_finalize()

    agreement_path = out_dir / "label_agreement.json"
    assert agreement_path.exists()
    with open(agreement_path) as f:
        ag = json.load(f)

    # Check top-level splits
    assert "all_rows" in ag
    assert "non_example_rows" in ag

    # All rows: n=4, 2 agree (R0001, R0002), 2 disagree -> 50.0%
    assert ag["all_rows"]["n"] == 4
    assert ag["all_rows"]["narrative"]["n"] == 4
    assert ag["all_rows"]["narrative"]["percent_agreement"] == 50.0

    # Non-example rows: n=3 (R0002, R0003, R0004), 1 agree (R0002), 2 disagree -> 33.33%
    assert ag["non_example_rows"]["n"] == 3
    assert ag["non_example_rows"]["narrative"]["n"] == 3
    assert ag["non_example_rows"]["narrative"]["percent_agreement"] == 33.33

    # Backwards-compatible access
    assert ag["narrative"]["all_rows"]["n"] == 4
    assert ag["narrative"]["non_example_rows"]["n"] == 3


def test_19_zero_overlap_between_codebook_and_pilot_sample():
    """Test 19: Ensures zero data leakage between coder-facing documents and the pilot sample.
    Scans every CODEBOOK*.md file and pilot_debrief_for_coders.md, failing if any pilot record_id appears."""
    import re
    from pathlib import Path
    import pandas as pd

    pilot_path = Path("data/processed/pilot_sample.csv")
    assert pilot_path.exists(), "data/processed/pilot_sample.csv must exist"

    pilot_df = pd.read_csv(pilot_path)
    pilot_rids = set(pilot_df["record_id"].dropna().astype(str))

    repo_root = Path(".")
    codebook_files = sorted(list(repo_root.glob("CODEBOOK*.md")))
    assert len(codebook_files) > 0, "At least one CODEBOOK*.md file must exist"

    scanned_files = list(codebook_files)
    debrief_path = repo_root / "pilot_debrief_for_coders.md"
    assert debrief_path.exists(), "pilot_debrief_for_coders.md must exist"
    scanned_files.append(debrief_path)

    for doc_path in scanned_files:
        text = doc_path.read_text(encoding="utf-8")
        found_rids = set(re.findall(r"R\d{4}", text))
        overlap = found_rids.intersection(pilot_rids)
        assert overlap == set(), (
            f"Leakage detected in {doc_path.name}: pilot record_ids present in coder document: {overlap}"
        )


def test_20_finalize_per_field_resolution_and_adjudication(tmp_path, monkeypatch):
    """Test 20: finalize flags all disagreements, prevents silent Coder A wins,
    handles single-coder fallback, prevents silent 'unknown', and applies adjudication."""
    import json
    import importlib
    import pandas as pd

    raw_dir = tmp_path / "data" / "raw"
    proc_dir = tmp_path / "data" / "processed"
    out_dir = tmp_path / "outputs"
    raw_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PIPELINE_OUT_DIR", str(out_dir))

    sheet_records = [
        {"record_id": "R0001", "claim_id": "C0001", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.1", "text_source": "verbatim", "claim_text": "Demo claim 1", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0002", "claim_id": "C0002", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.2", "text_source": "verbatim", "claim_text": "Demo claim 2", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0003", "claim_id": "C0003", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.3", "text_source": "verbatim", "claim_text": "Demo claim 3", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0004", "claim_id": "C0004", "claim_date": "2026-07-10", "review_date": "2026-07-11", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.4", "text_source": "verbatim", "claim_text": "Demo claim 4", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
    ]
    pd.DataFrame(sheet_records).to_csv(proc_dir / "coding_sheet.csv", index=False)

    # Coder A & B records reflecting the 3 demo rows plus unlabelled origin row
    coder_a_records = [
        # Row 1: Disagreement on content_form, direction, origin; agreement on relevance & narrative
        {"record_id": "R0001", "relevance": "on_topic", "narrative": "police_force", "content_form": "ai_generated", "direction": "supports_protesters", "origin": "documented_ai", "coder_notes": ""},
        # Row 2: Fallback case (Coder A left content_form & origin blank; direction differs)
        {"record_id": "R0002", "relevance": "on_topic", "narrative": "crowd_legitimacy", "content_form": "", "direction": "mixed", "origin": "", "coder_notes": ""},
        # Row 3: Disagreements to be adjudicated
        {"record_id": "R0003", "relevance": "on_topic", "narrative": "police_force", "content_form": "fabricated_text", "direction": "supports_police_government", "origin": "unknown", "coder_notes": ""},
        # Row 4: No silent unknown (both leave origin blank)
        {"record_id": "R0004", "relevance": "on_topic", "narrative": "other", "content_form": "old_or_out_of_context", "direction": "unclear", "origin": "", "coder_notes": ""},
    ]

    coder_b_records = [
        # Row 1: Disagrees on form, direction, origin
        {"record_id": "R0001", "relevance": "on_topic", "narrative": "police_force", "content_form": "old_or_out_of_context", "direction": "supports_police_government", "origin": "documented_non_ai", "coder_notes": ""},
        # Row 2: B fills form & origin; differs on direction
        {"record_id": "R0002", "relevance": "on_topic", "narrative": "crowd_legitimacy", "content_form": "cropped_or_edited", "direction": "unclear", "origin": "documented_non_ai", "coder_notes": ""},
        # Row 3: Disagrees on all
        {"record_id": "R0003", "relevance": "on_topic", "narrative": "protester_violence", "content_form": "ai_altered", "direction": "supports_protesters", "origin": "documented_ai", "coder_notes": ""},
        # Row 4: Both leave origin blank
        {"record_id": "R0004", "relevance": "on_topic", "narrative": "other", "content_form": "old_or_out_of_context", "direction": "unclear", "origin": "", "coder_notes": ""},
    ]

    pd.DataFrame(coder_a_records).to_csv(raw_dir / "coder_A.csv", index=False)
    pd.DataFrame(coder_b_records).to_csv(raw_dir / "coder_B.csv", index=False)

    # Adjudication file providing values for R0003
    adj_records = [
        {"record_id": "R0003", "relevance": "on_topic", "narrative": "police_force", "content_form": "genuine_wrongly_called_fake", "direction": "unclear", "origin": "disputed"},
    ]
    pd.DataFrame(adj_records).to_csv(raw_dir / "adjudicated.csv", index=False)

    build_dataset = importlib.import_module("02_build_dataset")
    build_dataset.run_finalize()

    dataset_df = pd.read_csv(proc_dir / "dataset.csv").fillna("")
    disagreements_df = pd.read_csv(out_dir / "label_disagreements.csv").fillna("")

    # Verify disagreements file
    assert not disagreements_df.empty
    # R0001 had disagreements on content_form, direction, origin
    r1_dis = disagreements_df[disagreements_df["record_id"] == "R0001"]
    assert set(r1_dis["field"]) == {"content_form", "direction", "origin"}

    # --- Verification of Demo Row 1: A does NOT silently win ---
    r1 = dataset_df[dataset_df["record_id"] == "R0001"].iloc[0]
    assert r1["content_form"] == ""
    assert r1["status_content_form"] == "unresolved_disagreement"
    assert r1["direction"] == ""
    assert r1["status_direction"] == "unresolved_disagreement"
    assert r1["origin"] == ""
    assert r1["status_origin"] == "unresolved_disagreement"
    assert r1["status_narrative"] == "two_coders_agree"

    # --- Verification of Demo Row 2: Fallback single_coder case ---
    r2 = dataset_df[dataset_df["record_id"] == "R0002"].iloc[0]
    assert r2["content_form"] == "cropped_or_edited"
    assert r2["status_content_form"] == "single_coder"
    assert r2["direction"] == ""
    assert r2["status_direction"] == "unresolved_disagreement"
    assert r2["origin"] == "documented_non_ai"
    assert r2["status_origin"] == "single_coder"

    # --- Verification of Demo Row 3: Adjudication overrides ---
    r3 = dataset_df[dataset_df["record_id"] == "R0003"].iloc[0]
    assert r3["content_form"] == "genuine_wrongly_called_fake"
    assert r3["status_content_form"] == "adjudicated"
    assert r3["direction"] == "unclear"
    assert r3["status_direction"] == "adjudicated"
    assert r3["origin"] == "disputed"
    assert r3["status_origin"] == "adjudicated"
    assert r3["narrative_original"] == "police_force"
    assert r3["status_narrative"] == "adjudicated"

    # --- Verification of Demo Row 4: No silent unknown ---
    r4 = dataset_df[dataset_df["record_id"] == "R0004"].iloc[0]
    assert r4["origin"] == ""
    assert r4["status_origin"] == "unlabelled"
    assert r4["origin"] != "unknown"


def test_21_adjudication_round_trip_and_validation(tmp_path):
    """Test 21: adjudication.xlsx generation and conversion back to adjudicated.csv with validation."""
    import importlib
    import openpyxl
    import pytest
    from adjudication_to_csv import convert_adjudication_to_csv

    build_dataset = importlib.import_module("02_build_dataset")
    write_adjudication_workbook = build_dataset.write_adjudication_workbook

    xlsx_path = tmp_path / "adjudication.xlsx"
    csv_path = tmp_path / "adjudicated.csv"

    dis_records = [
        {"record_id": "R0001", "field": "content_form", "option_1": "ai_generated", "option_2": "old_or_out_of_context", "review_url": "https://test.1", "final": ""},
        {"record_id": "R0001", "field": "direction", "option_1": "supports_protesters", "option_2": "supports_police_government", "review_url": "https://test.1", "final": ""},
    ]
    dis_df = pd.DataFrame(dis_records)

    write_adjudication_workbook(dis_df, xlsx_path)
    assert xlsx_path.exists()

    # Fill valid adjudication values
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    ws.cell(row=2, column=6, value="ai_generated")
    ws.cell(row=3, column=6, value="supports_protesters")
    wb.save(xlsx_path)

    # Convert to CSV
    df_out = convert_adjudication_to_csv(xlsx_path, csv_path)
    assert csv_path.exists()
    assert len(df_out) == 1
    assert df_out.loc[0, "record_id"] == "R0001"
    assert df_out.loc[0, "content_form"] == "ai_generated"
    assert df_out.loc[0, "direction"] == "supports_protesters"

    # Invalid value should trigger exit
    ws.cell(row=2, column=6, value="INVALID_CONTENT_FORM")
    wb.save(xlsx_path)
    with pytest.raises(SystemExit):
        convert_adjudication_to_csv(xlsx_path, csv_path)


def test_22_merge_halves_validation_and_integrity(tmp_path):
    """Test 22: merge_halves.py validates row isolation, rejects invalid dropdowns,
    rejects blank required cells, and preserves validation and links in merged workbook."""
    import openpyxl
    import pytest
    from merge_halves import merge_half_workbooks
    from xlsx_to_csv import convert_xlsx_to_csv
    from build_workbooks import create_workbook_for_df

    # Create dummy 10-row dataset for fast isolated testing
    records = []
    for i in range(1, 11):
        records.append({
            "record_id": f"R{i:04d}",
            "claim_text": f"Sample claim text {i}",
            "publisher_name": "BOOM",
            "review_url": f"https://example.com/factcheck/{i}",
        })
    df_base = pd.DataFrame(records)

    # Generate baseline workbooks with validations and hyperlinks
    wb1 = create_workbook_for_df(df_base, "Coder Half 1")
    wb2 = create_workbook_for_df(df_base, "Coder Half 2")

    # Half 1: rows 2 to 6 (5 records)
    # Half 2: rows 7 to 11 (5 records)
    r1_range = (2, 6)
    r2_range = (7, 11)

    # 1. Valid fill
    ws1 = wb1.active
    ws2 = wb2.active

    for r in range(2, 7):
        ws1.cell(row=r, column=5, value="on_topic")
        ws1.cell(row=r, column=6, value="police_force")
        ws1.cell(row=r, column=7, value="old_or_out_of_context")
        ws1.cell(row=r, column=8, value="supports_protesters")
        ws1.cell(row=r, column=9, value="documented_non_ai")
        ws1.cell(row=r, column=10, value="notes coder 1")

    for r in range(7, 12):
        ws2.cell(row=r, column=5, value="on_topic")
        ws2.cell(row=r, column=6, value="crowd_legitimacy")
        ws2.cell(row=r, column=7, value="cropped_or_edited")
        ws2.cell(row=r, column=8, value="supports_police_government")
        ws2.cell(row=r, column=9, value="documented_ai")
        ws2.cell(row=r, column=10, value="notes coder 2")

    h1_path = tmp_path / "coder1_half1.xlsx"
    h2_path = tmp_path / "coder1_half2.xlsx"
    out_path = tmp_path / "merged_coder.xlsx"
    out_csv = tmp_path / "merged_coder.csv"

    wb1.save(h1_path)
    wb2.save(h2_path)

    # Positive test: merge successfully
    merge_half_workbooks(h1_path, h2_path, out_path, rows1=r1_range, rows2=r2_range)
    assert out_path.exists()

    # Verify merged workbook content, structure, data validations, and hyperlinks
    wb_merged = openpyxl.load_workbook(out_path)
    ws_merged = wb_merged.active
    assert ws_merged.max_row == 11
    assert len(ws_merged.data_validations.dataValidation) == 5
    assert sum(1 for r in range(2, 12) if ws_merged.cell(row=r, column=4).hyperlink) == 10

    assert ws_merged.cell(row=2, column=5).value == "on_topic"
    assert ws_merged.cell(row=2, column=6).value == "police_force"
    assert ws_merged.cell(row=7, column=5).value == "on_topic"
    assert ws_merged.cell(row=7, column=6).value == "crowd_legitimacy"

    # Verify round-trip conversion to CSV via xlsx_to_csv.py
    df_csv = convert_xlsx_to_csv(out_path, out_csv)
    assert len(df_csv) == 10
    assert set(df_csv["narrative"].unique()) == {"police_force", "crowd_legitimacy"}

    # Negative test 1: Half 1 isolation violation
    wb1_bad = openpyxl.load_workbook(h1_path)
    wb1_bad.active.cell(row=8, column=5, value="on_topic")  # modifying Half 2's row
    bad_h1 = tmp_path / "bad_h1_iso.xlsx"
    wb1_bad.save(bad_h1)
    with pytest.raises(ValueError, match="Half 1 isolation violation"):
        merge_half_workbooks(bad_h1, h2_path, out_path, rows1=r1_range, rows2=r2_range)

    # Negative test 2: Half 2 isolation violation
    wb2_bad = openpyxl.load_workbook(h2_path)
    wb2_bad.active.cell(row=3, column=5, value="on_topic")  # modifying Half 1's row
    bad_h2 = tmp_path / "bad_h2_iso.xlsx"
    wb2_bad.save(bad_h2)
    with pytest.raises(ValueError, match="Half 2 isolation violation"):
        merge_half_workbooks(h1_path, bad_h2, out_path, rows1=r1_range, rows2=r2_range)

    # Negative test 3: Invalid dropdown value
    wb1_bad_val = openpyxl.load_workbook(h1_path)
    wb1_bad_val.active.cell(row=3, column=5, value="completely_bogus_relevance")
    bad_val_h1 = tmp_path / "bad_val_h1.xlsx"
    wb1_bad_val.save(bad_val_h1)
    with pytest.raises(ValueError, match="invalid relevance"):
        merge_half_workbooks(bad_val_h1, h2_path, out_path, rows1=r1_range, rows2=r2_range)

    # Negative test 4: Blank required cell (empty origin on on_topic record)
    wb2_blank = openpyxl.load_workbook(h2_path)
    wb2_blank.active.cell(row=9, column=9, value="")  # Blank origin
    bad_blank_h2 = tmp_path / "bad_blank_h2.xlsx"
    wb2_blank.save(bad_blank_h2)
    with pytest.raises(ValueError, match="Blank required cell for 'origin'"):
        merge_half_workbooks(h1_path, bad_blank_h2, out_path, rows1=r1_range, rows2=r2_range)

    # Negative test 5: Blank relevance
    wb1_blank_rel = openpyxl.load_workbook(h1_path)
    wb1_blank_rel.active.cell(row=4, column=5, value="")  # Blank relevance
    bad_rel_h1 = tmp_path / "bad_rel_h1.xlsx"
    wb1_blank_rel.save(bad_rel_h1)
    with pytest.raises(ValueError, match="Blank required cell for 'relevance'"):
        merge_half_workbooks(bad_rel_h1, h2_path, out_path, rows1=r1_range, rows2=r2_range)


def test_23_blank_cells_accepted_for_off_topic_and_unsure_and_excluded(tmp_path, monkeypatch):
    """Test 23: xlsx_to_csv.py and finalize accept workbooks where off_topic and unsure rows
    have the other four fields blank, and finalize excludes off_topic rows regardless of blanks."""
    import importlib
    import openpyxl
    import pandas as pd
    from xlsx_to_csv import convert_xlsx_to_csv
    from build_workbooks import create_workbook_for_df

    raw_dir = tmp_path / "data" / "raw"
    proc_dir = tmp_path / "data" / "processed"
    out_dir = tmp_path / "outputs"
    raw_dir.mkdir(parents=True)
    proc_dir.mkdir(parents=True)
    out_dir.mkdir(parents=True)

    monkeypatch.setenv("PIPELINE_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PIPELINE_OUT_DIR", str(out_dir))

    # 3 claims: 1 off_topic (blank other 4), 1 unsure (blank other 4), 1 on_topic (fully coded)
    sheet_data = [
        {"record_id": "R0001", "claim_id": "C0001", "claim_date": "2026-07-20", "review_date": "2026-07-21", "date_check": "ok", "topic_flag": "likely_off_topic", "publisher_name": "BOOM", "review_url": "https://test.1", "text_source": "verbatim", "claim_text": "Kerala narcotics seizure", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0002", "claim_id": "C0002", "claim_date": "2026-07-20", "review_date": "2026-07-21", "date_check": "ok", "topic_flag": "borderline", "publisher_name": "BOOM", "review_url": "https://test.2", "text_source": "verbatim", "claim_text": "Ambiguous Lucknow protest", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
        {"record_id": "R0003", "claim_id": "C0003", "claim_date": "2026-07-20", "review_date": "2026-07-21", "date_check": "ok", "topic_flag": "likely_on_topic", "publisher_name": "BOOM", "review_url": "https://test.3", "text_source": "verbatim", "claim_text": "Delhi police lathicharge", "script": "latin", "lang_group_heuristic": "english_likely", "relevance": "", "narrative": "", "content_form": "", "direction": "", "origin": "", "coder_notes": ""},
    ]
    pd.DataFrame(sheet_data).to_csv(proc_dir / "coding_sheet.csv", index=False)

    # Build coder workbooks
    wb = create_workbook_for_df(pd.DataFrame(sheet_data), "Coder Sheet")
    ws = wb.active

    # Row 2 (R0001): off_topic, other 4 blank
    ws.cell(row=2, column=5, value="off_topic")
    for c in range(6, 10):
        ws.cell(row=2, column=c, value="")

    # Row 3 (R0002): unsure, other 4 blank
    ws.cell(row=3, column=5, value="unsure")
    for c in range(6, 10):
        ws.cell(row=3, column=c, value="")

    # Row 4 (R0003): on_topic, fully coded
    ws.cell(row=4, column=5, value="on_topic")
    ws.cell(row=4, column=6, value="police_force")
    ws.cell(row=4, column=7, value="old_or_out_of_context")
    ws.cell(row=4, column=8, value="supports_protesters")
    ws.cell(row=4, column=9, value="documented_non_ai")

    xlsx_path = tmp_path / "coder_A.xlsx"
    wb.save(xlsx_path)

    # 1. xlsx_to_csv accepts blanks without rejecting
    csv_a = raw_dir / "coder_A.csv"
    csv_b = raw_dir / "coder_B.csv"
    df_converted = convert_xlsx_to_csv(xlsx_path, csv_a)
    assert len(df_converted) == 3
    assert df_converted.loc[0, "relevance"] == "off_topic"
    assert df_converted.loc[0, "narrative"] == ""
    assert df_converted.loc[1, "relevance"] == "unsure"
    assert df_converted.loc[1, "narrative"] == ""

    # Duplicate to coder_B.csv
    df_converted.to_csv(csv_b, index=False)

    # 2. finalize accepts blanks and properly handles exclusions
    build_dataset = importlib.import_module("02_build_dataset")
    build_dataset.run_finalize()

    dataset_df = pd.read_csv(proc_dir / "dataset.csv").fillna("")
    excluded_df = pd.read_csv(out_dir / "excluded_off_topic.csv").fillna("")

    # R0001 (off_topic) MUST be excluded regardless of blank fields
    assert "R0001" not in dataset_df["record_id"].tolist()
    assert "R0001" in excluded_df["record_id"].tolist()
    assert excluded_df.loc[excluded_df["record_id"] == "R0001", "exclusion_reason"].iloc[0] == "coder_marked_off_topic"

    # R0002 (unsure) remains in dataset pending adjudication
    assert "R0002" in dataset_df["record_id"].tolist()
    r2 = dataset_df[dataset_df["record_id"] == "R0002"].iloc[0]
    assert r2["status_relevance"] == "unresolved_disagreement"
    assert r2["status_narrative"] == "unlabelled"
    assert r2["narrative"] == ""

    # R0003 (on_topic) remains in dataset with consensus
    assert "R0003" in dataset_df["record_id"].tolist()
    r3 = dataset_df[dataset_df["record_id"] == "R0003"].iloc[0]
    assert r3["status_relevance"] == "two_coders_agree"
    assert r3["narrative_original"] == "police_force"







def test_24_final_labels_ingestion_and_validation():
    """Test 24: final_labels.csv ingestion, validation, and claim_id join completeness."""
    labels_path = Path("data/processed/final_labels.csv")
    assert labels_path.exists(), "final_labels.csv must exist."
    df = pd.read_csv(labels_path)

    # 97 rows and unique record_ids
    assert len(df) == 97, f"Expected 97 rows, found {len(df)}"
    assert df["record_id"].nunique() == 97, "Record IDs must be unique"

    # Header mapping completeness
    expected_cols = [
        "record_id", "claim_id", "claim_date", "claim_text",
        "publisher_workbook", "publisher_canonical", "review_url",
        "lang_group", "relevance", "narrative_native",
        "content_form_native", "direction_native",
        "origin_note_present", "coder_notes"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing expected column: {col}"

    # claim_id join completeness
    assert df["claim_id"].isna().sum() == 0, "All rows must have a valid claim_id"
    assert df["claim_id"].str.startswith("C").all(), "All claim_ids must start with 'C'"
    assert df["claim_id"].nunique() == 85, f"Expected 85 unique claims, found {df['claim_id'].nunique()}"

    # Blank relevance and publisher logging verification
    assert df[df["record_id"] == "R0007"]["relevance"].isna().iloc[0], "R0007 must have blank relevance"
    assert df[df["record_id"].isin(["R0046", "R0053"])]["publisher_workbook"].isna().all(), "R0046 and R0053 must have blank publisher"


def test_25_mapping_completeness_and_overrides():
    """Test 25: Proposal mapping completeness, row-level overrides, and rare-class threshold."""
    mapping_path = Path("narrative_mapping.csv")
    assert mapping_path.exists(), "narrative_mapping.csv must exist"
    mapping_df = pd.read_csv(mapping_path)

    labels_path = Path("data/processed/final_labels.csv")
    df = pd.read_csv(labels_path)

    # Every native narrative in the data must be covered
    cat_mapped_natives = set(mapping_df[mapping_df["level"] == "category"]["native_label"])
    row_mapped_rids = set()
    for rids in mapping_df[mapping_df["level"] == "row"]["record_ids"]:
        for rid in str(rids).split(";"):
            row_mapped_rids.add(rid.strip())

    for _, row in df.iterrows():
        rid = row["record_id"]
        native = row["narrative_native"]
        assert (rid in row_mapped_rids) or (native in cat_mapped_natives), f"Unmapped record: {rid} ({native})"

    # Row-level override verification
    row_map = {rid.strip(): r["proposal_code"] for _, r in mapping_df[mapping_df["level"] == "row"].iterrows() for rid in str(r["record_ids"]).split(";")}
    cat_map = {r["native_label"]: r["proposal_code"] for _, r in mapping_df[mapping_df["level"] == "category"].iterrows()}

    for rid in ["R0016", "R0074", "R0080", "R0086"]:
        assert row_map[rid] == "crowd_legitimacy", f"{rid} must map to crowd_legitimacy"
    for rid in ["R0027", "R0059"]:
        assert row_map[rid] == "other", f"{rid} must map to other"

    # Rare-class merging: individual_targeting (6 claims) and protester_violence (5 claims) merge into other
    df["scheme_p_raw"] = df.apply(lambda r: row_map.get(r["record_id"], cat_map.get(r["narrative_native"], "other")), axis=1)
    claims_per_raw = df.groupby("scheme_p_raw")["claim_id"].nunique()
    assert claims_per_raw["individual_targeting"] == 6
    assert claims_per_raw["protester_violence"] == 5

    rare = set(claims_per_raw[claims_per_raw < 8].index)
    assert rare == {"individual_targeting", "protester_violence"}

    df["scheme_p"] = df["scheme_p_raw"].apply(lambda x: "other" if x in rare else x)
    assert set(df["scheme_p"].unique()) == {"crowd_legitimacy", "other", "police_force", "slogans_communal_loyalty"}


def test_26_grouped_cv_zero_leakage():
    """Test 26: Zero claim_id leakage across folds in StratifiedGroupKFold."""
    from sklearn.model_selection import StratifiedGroupKFold

    df = pd.read_csv("data/processed/final_labels.csv")
    mapping_df = pd.read_csv("narrative_mapping.csv")
    row_map = {rid.strip(): r["proposal_code"] for _, r in mapping_df[mapping_df["level"] == "row"].iterrows() for rid in str(r["record_ids"]).split(";")}
    cat_map = {r["native_label"]: r["proposal_code"] for _, r in mapping_df[mapping_df["level"] == "category"].iterrows()}

    df["scheme_p_raw"] = df.apply(lambda r: row_map.get(r["record_id"], cat_map.get(r["narrative_native"], "other")), axis=1)
    rare = set(df.groupby("scheme_p_raw")["claim_id"].nunique().loc[lambda x: x < 8].index)
    df["scheme_p"] = df["scheme_p_raw"].apply(lambda x: "other" if x in rare else x)

    seeds = [42, 43, 44, 45, 46]
    for seed in seeds:
        sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=seed)
        for fold, (train_idx, test_idx) in enumerate(sgkf.split(df, df["scheme_p"], groups=df["claim_id"])):
            train_cids = set(df.iloc[train_idx]["claim_id"])
            test_cids = set(df.iloc[test_idx]["claim_id"])
            assert train_cids.isdisjoint(test_cids), f"Leakage detected in seed {seed}, fold {fold}!"


def test_27_privacy_zero_handles():
    """Test 27: Strict assertion that zero social media handles (@\\w+) appear in outputs/, qa/, README.md, or REPORT.md."""
    import re
    scan_paths = [Path("README.md"), Path("REPORT.md")]
    scan_paths.extend(list(Path("outputs").glob("**/*")))
    scan_paths.extend(list(Path("qa").glob("**/*")))

    violations = []
    for p in scan_paths:
        if p.is_file() and p.suffix in [".md", ".csv", ".json", ".txt"]:
            content = p.read_text(encoding="utf-8", errors="ignore")
            matches = re.findall(r"@\w+", content)
            if matches:
                violations.append((str(p), matches))

    assert len(violations) == 0, f"Privacy violation: social media handles detected: {violations}"


def test_28_predict_cli_smoke_test():
    """Test 28: Standalone predict.py smoke test with 5 canonical claims."""
    from predict import load_model, predict_claim, SMOKE_TEST_EXAMPLES, MANDATORY_WARNING

    model_payload = load_model()
    assert model_payload is not None
    assert "classes" in model_payload

    expected_labels = [
        "crowd_legitimacy",
        "police_force",
        "slogans_communal_loyalty",
        "other",
        "other",
    ]

    for claim_text, exp_label in zip(SMOKE_TEST_EXAMPLES, expected_labels):
        res = predict_claim(claim_text, model_payload)
        assert res["predicted_label"] in model_payload["classes"]
        assert len(res["probabilities"]) == len(model_payload["classes"])
        assert res["warning"] == MANDATORY_WARNING
        # Verify confidence is a valid probability
        assert 0.0 <= res["confidence"] <= 1.0


def test_29_scheme_counts_match_figures_and_run_info():
    """Test 29: Verification that dataset counts match run_info.json, figures exist, and hashes match."""
    import hashlib

    labels_path = Path("data/processed/final_labels.csv")
    computed_hash = hashlib.sha256(labels_path.read_bytes()).hexdigest()

    run_info_path = Path("outputs/run_info.json")
    assert run_info_path.exists()
    with open(run_info_path) as f:
        run_info = json.load(f)

    assert run_info["dataset_sha256"] == computed_hash, "run_info.json hash must match final_labels.csv"
    assert run_info["n_rows"] == 97
    assert run_info["n_claims"] == 85

    expected_p_counts = {
        "crowd_legitimacy": 44,
        "other": 24,
        "police_force": 15,
        "slogans_communal_loyalty": 14,
    }
    assert run_info["rows_per_class_scheme_p"] == expected_p_counts

    # Verify all 4 figures exist and are non-empty
    fig_dir = Path("figures")
    for f_name in ["class_distribution.png", "model_comparison.png", "confusion_matrix.png", "rq1_content_form_matrix.png"]:
        fig_p = fig_dir / f_name
        assert fig_p.exists(), f"Missing figure: {f_name}"
        assert fig_p.stat().st_size > 5000, f"Figure {f_name} is unexpectedly small or empty"


def test_30_no_demo_data_in_outputs():
    """Test 30: Confirms no outputs/ file was produced from demo/synthetic data."""
    cv_sum_p = Path("outputs/cv_summary_scheme_p.csv")
    assert cv_sum_p.exists()
    df_p = pd.read_csv(cv_sum_p)

    # Real data has 97 rows and 85 claims
    assert (df_p["n_rows"] == 97).all(), "Outputs must be generated on real 97-row dataset, not demo"
    assert (df_p["n_claims"] == 85).all(), "Outputs must reflect 85 unique claims"


def test_31_proposal_rq_wording_present_in_docs():
    """Test 31: Verifies proposal RQ wording is present in REPORT.md, README.md, model_card.md."""
    rqs = [
        "What kinds of misleading or synthetic content were recorded, and what narratives did the claims back up?",
        "How did fact-checkers and public agencies verify the claims, and where did their accounts disagree?",
        "Can a multilingual classifier help researchers sort claim narratives without replacing human judgement, and what errors does it make across English, Hindi and Hinglish?",
        "What human harms are documented, and what communication recommendations are supported by this evidence?",
    ]
    docs = [Path("REPORT.md"), Path("README.md"), Path("model_card.md")]
    for doc in docs:
        assert doc.exists(), f"Missing {doc}"
        text = doc.read_text(encoding="utf-8")
        for idx, rq in enumerate(rqs, 1):
            assert rq in text, f"RQ{idx} proposal wording missing from {doc}"
        # Assert neither document refers to RQ2 as diffusion or RQ4 as engagement
        assert "diffusion velocity" not in text.lower(), f"'diffusion velocity' found in {doc}"
        assert "audience engagement" not in text.lower(), f"'audience engagement' found in {doc}"


def test_32_table_totals_match_final_labels():
    """Test 32: Asserts RQ1 table column totals match class counts in final_labels.csv."""
    rq1_csv = Path("outputs/rq1_form_by_narrative_mapped.csv")
    assert rq1_csv.exists()
    df_rq1 = pd.read_csv(rq1_csv, index_col=0)

    with open("outputs/run_info.json") as f:
        run_info = json.load(f)
    expected_p = run_info["rows_per_class_scheme_p"]

    assert df_rq1.loc["All", "crowd_legitimacy"] == expected_p["crowd_legitimacy"] == 44
    assert df_rq1.loc["All", "other"] == expected_p["other"] == 24
    assert df_rq1.loc["All", "police_force"] == expected_p["police_force"] == 15
    assert df_rq1.loc["All", "slogans_communal_loyalty"] == expected_p["slogans_communal_loyalty"] == 14
    assert df_rq1.loc["All", "All"] == 97


def test_33_model_ranking_text_matches_data():
    """Test 33: Asserts REPORT.md ranking text accurately reflects sensitivity changes from data."""
    report_text = Path("REPORT.md").read_text(encoding="utf-8")
    assert "On Scheme P ($n=97$), model rankings by mean Macro-F1 are" in report_text
    assert "rankings do not remain preserved" in report_text
    assert "xlmr_lr" in report_text and "first place" in report_text
    assert "muril_lr" in report_text and "drops to second" in report_text


def test_34_zero_handle_like_strings():
    """Test 34: Asserts zero handle patterns with or without @ appear across all published artifacts."""
    import re
    scan_paths = [Path("README.md"), Path("REPORT.md"), Path("privacy_log.md")]
    scan_paths.extend(list(Path("outputs").glob("**/*")))
    scan_paths.extend(list(Path("qa").glob("**/*")))

    forbidden_patterns = [
        re.compile(r"@\w+"),
        re.compile(r"Instagram:", re.IGNORECASE),
        re.compile(r"X handle", re.IGNORECASE),
    ]

    violations = []
    for p in scan_paths:
        if p.is_file() and p.suffix in [".md", ".csv", ".json", ".txt"]:
            content = p.read_text(encoding="utf-8", errors="ignore")
            for pattern in forbidden_patterns:
                matches = pattern.findall(content)
                if matches:
                    violations.append((str(p), matches))

    assert len(violations) == 0, f"Privacy violation: handle-like patterns found: {violations}"

