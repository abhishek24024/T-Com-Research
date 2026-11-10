"""Utility functions for the Claim-Narrative Triage Pipeline.

Covers:
- Text normalisation (Devanagari matras/vowel preservation, punctuation & URL stripping)
- Script detection & Hinglish heuristic
- Surface feature extraction
- Fact Check Tools API response parsing (strictly drops claimant)
- Temporal filtering logic
- Near-duplicate claim_id proposal (TF-IDF char_wb cosine similarity + connected components)
- Inter-coder agreement metrics (Cohen's Kappa, percent agreement)
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
import numpy as np
import pandas as pd
from scipy.sparse import csgraph
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import cohen_kappa_score, f1_score
from sklearn.metrics.pairwise import cosine_similarity

from config import (
    CLAIM_WINDOW_END,
    CLAIM_WINDOW_START,
    DUP_SIMILARITY,
    REPORT_CUTOFF,
)

# Common Romanized-Hindi function words for the Hinglish heuristic
HINGLISH_FUNCTION_WORDS = {
    "hai", "hain", "ki", "ke", "ka", "ko", "se", "me", "mein", "par",
    "ye", "yeh", "woh", "wo", "kya", "nahi", "nahin", "ne", "aur",
    "bhi", "tha", "thi", "the", "kare", "karna", "raha", "rahi", "rahe",
    "gaya", "gayi", "gaye", "huye", "hua", "hui", "aaj", "ab", "kab",
    "jab", "log", "apne", "apna", "apni", "pe", "mat", "karo", "toh",
    "hi", "bhai", "sab", "wale", "wali", "wala", "kar", "diya", "liya"
}


def normalize_text(text: str) -> str:
    """Normalises text while preserving Devanagari vowel signs (matras/combining marks).

    Rules (Section 7):
    - Strip URLs
    - Lowercase
    - Keep Unicode categories L (letter), M (mark/vowel signs), N (number), and whitespace
    - Strip punctuation and symbols (replaced with space)
    - Collapse repeated whitespace and strip leading/trailing spaces
    """
    if not isinstance(text, str) or not text:
        return ""

    # Strip URLs
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)
    # Lowercase
    text = text.lower()

    # Retain Letters (L*), Marks (M* e.g. Devanagari vowel signs/matras), Numbers (N*), and whitespace
    filtered_chars = []
    for char in text:
        cat = unicodedata.category(char)
        if cat.startswith(("L", "M", "N")) or char.isspace():
            filtered_chars.append(char)
        else:
            filtered_chars.append(" ")

    cleaned = "".join(filtered_chars)
    # Collapse multiple whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def split_tokenizer(text: str) -> list[str]:
    """Tokenizer splitting on whitespace for pre-normalised text."""
    if not text:
        return []
    return text.split()


def is_devanagari_char(char: str) -> bool:
    """Returns True if the character belongs to the Devanagari Unicode blocks."""
    code = ord(char)
    return (0x0900 <= code <= 0x097F) or (0xA8E0 <= code <= 0xA8FF) or (0x1CD0 <= code <= 0x1CFF)


def is_latin_char(char: str) -> bool:
    """Returns True if the character belongs to basic Latin or Latin-1 letters."""
    code = ord(char)
    return (0x0041 <= code <= 0x005A) or (0x0061 <= code <= 0x007A) or (0x00C0 <= code <= 0x024F)


def detect_script(text: str) -> str:
    """Detects script as 'devanagari', 'latin', 'mixed', or 'other' based on letter ratios."""
    if not isinstance(text, str) or not text:
        return "other"

    dev_count = 0
    latin_count = 0
    other_letters = 0

    for char in text:
        if unicodedata.category(char).startswith("L"):
            if is_devanagari_char(char):
                dev_count += 1
            elif is_latin_char(char):
                latin_count += 1
            else:
                other_letters += 1

    total_letters = dev_count + latin_count + other_letters
    if total_letters == 0:
        return "other"

    dev_ratio = dev_count / total_letters
    latin_ratio = latin_count / total_letters

    if dev_ratio > 0.80:
        return "devanagari"
    if latin_ratio > 0.80:
        return "latin"
    if dev_count > 0 and latin_count > 0:
        return "mixed"
    return "other"


def detect_lang_group_heuristic(text: str, script: str | None = None) -> str:
    """Heuristic for language group: 'devanagari', 'hinglish_likely', or 'english_likely'.

    Devanagari script -> devanagari
    Latin/mixed script -> hinglish_likely if matching Romanized Hindi function words, else english_likely.
    """
    if script is None:
        script = detect_script(text)

    if script == "devanagari":
        return "devanagari"

    norm = normalize_text(text)
    words = norm.split()
    if not words:
        return "english_likely"

    match_count = sum(1 for w in words if w in HINGLISH_FUNCTION_WORDS)
    # If 2 or more function words match, or 1 match in very short text (<= 5 words)
    if match_count >= 2 or (len(words) <= 5 and match_count >= 1):
        return "hinglish_likely"

    return "english_likely"


class SurfaceFeatureExtractor(BaseEstimator, TransformerMixin):
    """Extracts 10 standardized surface features from raw text (ablation study).

    Features:
    1. log characters: np.log1p(len(text))
    2. log words: np.log1p(len(text.split()))
    3. Devanagari ratio: dev_chars / max(len(text), 1)
    4. Latin ratio: latin_chars / max(len(text), 1)
    5. Exclamation count: count of '!'
    6. Question count: count of '?'
    7. Uppercase ratio: uppercase letters / max(total letters, 1)
    8. Has-digit: 1.0 if any digit else 0.0
    9. Has-URL: 1.0 if contains http://, https://, or www. else 0.0
    10. Hashtags and mentions count: count of '#' and '@'
    """

    def fit(self, X: Any, y: Any = None) -> SurfaceFeatureExtractor:
        return self

    def transform(self, X: Any) -> np.ndarray:
        feats = []
        for text in X:
            if not isinstance(text, str):
                text = ""

            char_len = len(text)
            words = text.split()
            word_count = len(words)

            dev_chars = sum(1 for c in text if is_devanagari_char(c))
            latin_chars = sum(1 for c in text if is_latin_char(c))
            letters = [c for c in text if unicodedata.category(c).startswith("L")]
            letter_count = len(letters)
            upper_count = sum(1 for c in letters if c.isupper())

            f_log_chars = np.log1p(char_len)
            f_log_words = np.log1p(word_count)
            f_dev_ratio = dev_chars / max(char_len, 1)
            f_latin_ratio = latin_chars / max(char_len, 1)
            f_exclamations = float(text.count("!"))
            f_questions = float(text.count("?"))
            f_upper_ratio = upper_count / max(letter_count, 1)
            f_has_digit = 1.0 if any(c.isdigit() for c in text) else 0.0
            f_has_url = 1.0 if bool(re.search(r"https?://|www\.", text)) else 0.0
            f_hashtags_mentions = float(text.count("#") + text.count("@"))

            feats.append([
                f_log_chars,
                f_log_words,
                f_dev_ratio,
                f_latin_ratio,
                f_exclamations,
                f_questions,
                f_upper_ratio,
                f_has_digit,
                f_has_url,
                f_hashtags_mentions,
            ])
        return np.array(feats, dtype=np.float64)


def parse_api_response(api_response: dict[str, Any], query_term: str = "") -> list[dict[str, Any]]:
    """Flattens Google Fact Check Tools API response to rows.

    STRICT HARD RULE: Drops claimant field completely. Never logs or outputs claimant.
    """
    rows: list[dict[str, Any]] = []
    claims = api_response.get("claims", [])
    if not isinstance(claims, list):
        return rows

    for claim in claims:
        claim_text = (claim.get("text") or "").strip()
        claim_date = (claim.get("claimDate") or "").strip()
        # Parse ISO date if with timestamp to YYYY-MM-DD
        if "T" in claim_date:
            claim_date = claim_date.split("T")[0]

        claim_reviews = claim.get("claimReview", [])
        if not claim_reviews:
            continue

        for cr in claim_reviews:
            publisher = cr.get("publisher", {}) or {}
            pub_name = (publisher.get("name") or "").strip()
            pub_site = (publisher.get("site") or "").strip()
            rev_url = (cr.get("url") or "").strip()
            rev_title = (cr.get("title") or "").strip()
            rev_date = (cr.get("reviewDate") or "").strip()
            if "T" in rev_date:
                rev_date = rev_date.split("T")[0]
            rating = (cr.get("textualRating") or "").strip()
            lang = (cr.get("languageCode") or "").strip()

            rows.append({
                "source": "factcheck_api",
                "claim_text": claim_text,
                "claim_date": claim_date,
                "review_date": rev_date,
                "publisher_name": pub_name,
                "publisher_site": pub_site,
                "review_url": rev_url,
                "review_title": rev_title,
                "textual_rating": rating,
                "language_code": lang,
                "text_source": "unknown",
                "query_term": query_term,
            })
    return rows


def clean_date_str(val: Any) -> str:
    """Normalizes date string to YYYY-MM-DD if valid, else empty string."""
    if pd.isna(val) or not val:
        return ""
    val_str = str(val).strip()
    if "T" in val_str:
        val_str = val_str.split("T")[0]
    # Check YYYY-MM-DD format
    if re.match(r"^\d{4}-\d{2}-\d{2}$", val_str):
        return val_str
    return ""


def filter_claims_by_date(
    df: pd.DataFrame,
    start_date: str = CLAIM_WINDOW_START,
    end_date: str = CLAIM_WINDOW_END,
    cutoff_date: str = REPORT_CUTOFF,
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Applies temporal filter according to Stage 2a spec.

    - Keep if claim_date is inside [start_date, end_date].
    - If claim_date is missing and review_date is in [start_date, cutoff_date],
      keep and set date_check='needs_manual_date_check'.
    - Otherwise drop, tracking drop reasons.
    """
    df = df.copy()
    kept_rows = []
    drop_counts = {
        "empty_claim_text": 0,
        "claim_date_out_of_window": 0,
        "missing_claim_date_and_review_date_out_of_range": 0,
        "missing_both_dates": 0,
    }

    for idx, row in df.iterrows():
        claim_text = str(row.get("claim_text", "")).strip()
        if not claim_text or claim_text.lower() == "nan":
            drop_counts["empty_claim_text"] += 1
            continue

        c_date = clean_date_str(row.get("claim_date"))
        r_date = clean_date_str(row.get("review_date"))

        if c_date:
            if start_date <= c_date <= end_date:
                row_dict = row.to_dict()
                row_dict["claim_date"] = c_date
                row_dict["review_date"] = r_date
                row_dict["date_check"] = "ok"
                kept_rows.append(row_dict)
            else:
                drop_counts["claim_date_out_of_window"] += 1
        else:
            if r_date:
                if start_date <= r_date <= cutoff_date:
                    row_dict = row.to_dict()
                    row_dict["claim_date"] = ""
                    row_dict["review_date"] = r_date
                    row_dict["date_check"] = "needs_manual_date_check"
                    kept_rows.append(row_dict)
                else:
                    drop_counts["missing_claim_date_and_review_date_out_of_range"] += 1
            else:
                drop_counts["missing_both_dates"] += 1

    kept_df = pd.DataFrame(kept_rows)
    return kept_df, drop_counts


def propose_claim_ids(texts: list[str], threshold: float = DUP_SIMILARITY) -> list[str]:
    """Proposes claim_ids using char-n-gram (3 to 5, char_wb) TF-IDF cosine similarity.

    Pairs with similarity >= threshold are connected. Connected components form claim_ids.
    """
    if not texts:
        return []

    if len(texts) == 1:
        return ["C0001"]

    vectorizer = TfidfVectorizer(
        analyzer="char_wb",
        ngram_range=(3, 5),
        preprocessor=normalize_text,
    )
    X = vectorizer.fit_transform(texts)
    sim_matrix = cosine_similarity(X)

    # Adjacency matrix for connected components
    adj = (sim_matrix >= threshold).astype(int)
    n_components, labels = csgraph.connected_components(adj, directed=False)

    return [f"C{label + 1:04d}" for label in labels]


class UnionFind:
    """Disjoint Set Union (Union-Find) with path compression for transitive claim merges."""

    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, i: str) -> str:
        if i not in self.parent:
            self.parent[i] = i
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: str, j: str) -> None:
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            # Deterministic tie-breaking: prefer alphabetically smaller canonical root
            if root_i < root_j:
                self.parent[root_j] = root_i
            else:
                self.parent[root_i] = root_j


def compute_label_agreement(y1: list[str], y2: list[str]) -> dict[str, float | int]:
    """Computes Cohen's kappa and percent agreement for two coders."""
    if len(y1) != len(y2) or len(y1) == 0:
        return {"n": len(y1), "percent_agreement": 0.0, "cohen_kappa": 0.0}

    agreed = sum(1 for a, b in zip(y1, y2) if a == b)
    pct = (agreed / len(y1)) * 100.0

    # Calculate Cohen's kappa
    # Note: if all labels are identical, kappa is 1.0 or NaN in some versions of sklearn
    try:
        if len(set(y1).union(set(y2))) <= 1:
            kappa = 1.0 if agreed == len(y1) else 0.0
        else:
            kappa = float(cohen_kappa_score(y1, y2))
            if np.isnan(kappa):
                kappa = 1.0 if agreed == len(y1) else 0.0
    except Exception:
        kappa = 0.0

    return {
        "n": len(y1),
        "percent_agreement": round(pct, 2),
        "cohen_kappa": round(kappa, 4),
    }


def compute_macro_f1(y_true: list[str], y_pred: list[str]) -> float:
    """Computes macro-F1 with zero_division=0."""
    return float(f1_score(y_true, y_pred, average="macro", zero_division=0))
