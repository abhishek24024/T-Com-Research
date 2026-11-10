"""Central configuration for the Claim-Narrative Triage Pipeline.

Every constant is defined here. No constants inside scripts.
"""

from __future__ import annotations

import os
from pathlib import Path

# Random Seeds & Splitting
SEED = 42
CV_SEEDS = [42, 43, 44, 45, 46]
N_SPLITS = 5

# Temporal Window
CLAIM_WINDOW_START = "2026-06-06"
CLAIM_WINDOW_END = "2026-07-25"
REPORT_CUTOFF = "2026-10-11"

# API Search Defaults
# Derived from cited fact-check reports (Quint WebQoof, BOOM, Alt News)
SEARCH_TERMS = [
    "CJP protest",
    "Cockroach Janta Party",
    "Jantar Mantar protest",
    "lathicharge protest Delhi",
    "NEET protest Delhi",
    "women CJP protesters",
    "CJP student protest",
]
LANGUAGES = ["en", "hi"]
PUBLISHER_SITES: list[str] = []  # Empty means query all publishers

# Controlled Vocabularies
NARRATIVES = [
    "police_force",
    "protester_violence",
    "slogans_communal_loyalty",
    "crowd_legitimacy",
    "individual_targeting",
    "other",
]

CONTENT_FORMS = [
    "old_or_out_of_context",
    "ai_generated",
    "ai_altered",
    "cropped_or_edited",
    "fabricated_text",
    "genuine_wrongly_called_fake",
    "disputed",
    "not_established",
]

DIRECTIONS = [
    "supports_protesters",
    "supports_police_government",
    "mixed",
    "unclear",
]

RELEVANCES = [
    "on_topic",
    "off_topic",
    "unsure",
]

ORIGINS = [
    "documented_ai",
    "documented_non_ai",
    "disputed",
    "unknown",
]

# Classification & Deduplication Thresholds
MIN_CLAIMS_PER_CLASS = 8
DUP_SIMILARITY = 0.80
MIN_ROWS_FOR_GROUP_SCORE = 30
TIME_HOLDOUT_FRACTION = 0.20

# Transformer Models & Embeddings
HF_MODELS = {
    "xlmr": "xlm-roberta-base",
    "muril": "google/muril-base-cased",
}
MAX_LEN = 128
EMBED_BATCH = 16

# Review & QA Sampling
REVIEW_SAMPLE_SEED = 42
REVIEW_N = 30
FAILURE_TAXONOMY = [
    "dialect_or_script",
    "protest_anger_read_as_violence",
    "quoted_text",
    "thin_text",
    "label_ambiguity",
    "narrative_overlap",
    "other",
]

# Environment Variables & Dynamic Paths
def get_google_api_key() -> str | None:
    return os.environ.get("GOOGLE_API_KEY")

def get_base_dir() -> Path:
    return Path(__file__).resolve().parent

def get_data_dir() -> Path:
    override = os.environ.get("PIPELINE_DATA_DIR")
    if override:
        return Path(override)
    return get_base_dir() / "data"

def get_raw_data_dir() -> Path:
    return get_data_dir() / "raw"

def get_processed_data_dir() -> Path:
    return get_data_dir() / "processed"

def get_out_dir() -> Path:
    override = os.environ.get("PIPELINE_OUT_DIR")
    if override:
        return Path(override)
    return get_base_dir() / "outputs"

def get_review_dir() -> Path:
    return get_out_dir() / "review"

def get_qa_dir() -> Path:
    override = os.environ.get("PIPELINE_QA_DIR")
    if override:
        return Path(override)
    return get_base_dir() / "qa"

# Static directory references for standard execution
BASE_DIR = get_base_dir()
DATA_DIR = get_data_dir()
RAW_DATA_DIR = get_raw_data_dir()
PROCESSED_DATA_DIR = get_processed_data_dir()
OUT_DIR = get_out_dir()
REVIEW_OUT_DIR = get_review_dir()
QA_DIR = get_qa_dir()
