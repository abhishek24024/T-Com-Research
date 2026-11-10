#!/usr/bin/env python3
"""Stage 1: Collect claims via Google Fact Check Tools API or offline JSON.

Usage:
  python3 01_collect_claims.py [--offline-json PATH] [--max-age-days N]
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
import pandas as pd
import requests

from config import (
    CLAIM_WINDOW_START,
    LANGUAGES,
    PUBLISHER_SITES,
    SEARCH_TERMS,
    get_google_api_key,
    get_raw_data_dir,
)
from utils import parse_api_response

API_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"


def calculate_default_max_age_days() -> int:
    """Calculates days from CLAIM_WINDOW_START to today plus 7 days."""
    try:
        start = datetime.date.fromisoformat(CLAIM_WINDOW_START)
        today = datetime.date.today()
        diff = (today - start).days
        return max(diff + 7, 30)
    except Exception:
        return 180


def log_search_terms(
    log_path: Path,
    terms: list[str],
    languages: list[str],
    sites: list[str],
    max_age_days: int,
) -> None:
    """Logs query parameters to search_terms_log.txt BEFORE executing any requests."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    entry = (
        f"Timestamp: {ts}\n"
        f"Terms: {json.dumps(terms, ensure_ascii=False)}\n"
        f"Languages: {json.dumps(languages)}\n"
        f"Sites: {json.dumps(sites)}\n"
        f"MaxAgeDays: {max_age_days}\n"
        f"{'-' * 60}\n"
    )
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry)


def fetch_api_page(
    query: str,
    language_code: str,
    site: str | None,
    max_age_days: int,
    api_key: str,
    page_token: str | None = None,
) -> dict[str, Any]:
    """Fetches a single page with exponential backoff on 429/5xx."""
    params: dict[str, Any] = {
        "query": query,
        "languageCode": language_code,
        "maxAgeDays": max_age_days,
        "pageSize": 10,
        "key": api_key,
    }
    if site:
        params["reviewPublisherSiteFilter"] = site
    if page_token:
        params["pageToken"] = page_token

    delays = [1.0, 2.0, 4.0, 8.0]
    for attempt, delay in enumerate(delays, start=1):
        try:
            resp = requests.get(API_URL, params=params, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(delay)
                continue
            elif resp.status_code == 400:
                sys.exit(f"API Error 400: Bad Request. Check parameters or API configuration. Detail: {resp.text}")
            elif resp.status_code in (401, 403):
                sys.exit(
                    "API Error (401/403): Authentication or permission failure. "
                    "Likely cause: Invalid GOOGLE_API_KEY or Fact Check Tools API is not enabled in Google Cloud Console."
                )
            else:
                sys.exit(f"API Error HTTP {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            if attempt == len(delays):
                sys.exit(f"Network error after multiple retries: {e}")
            time.sleep(delay)

    sys.exit(f"API failed after {len(delays)} retries due to rate limiting or server errors.")


def ensure_manual_template(raw_dir: Path) -> None:
    """Creates empty data/raw/manual_claims.csv template if absent."""
    manual_path = raw_dir / "manual_claims.csv"
    if not manual_path.exists():
        columns = [
            "source",
            "claim_text",
            "claim_date",
            "review_date",
            "publisher_name",
            "publisher_site",
            "review_url",
            "review_title",
            "textual_rating",
            "language_code",
            "text_source",
            "query_term",
        ]
        df_empty = pd.DataFrame(columns=columns)
        df_empty.to_csv(manual_path, index=False)
        print(f"Created empty manual claims template: {manual_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect claims via Fact Check Tools API.")
    parser.add_argument("--offline-json", type=str, help="Parse saved JSON file instead of calling network.")
    parser.add_argument("--max-age-days", type=int, default=None, help="Override default maxAgeDays.")
    args = parser.parse_args()

    raw_dir = get_raw_data_dir()
    raw_dir.mkdir(parents=True, exist_ok=True)
    ensure_manual_template(raw_dir)

    max_age_days = args.max_age_days or calculate_default_max_age_days()
    log_path = raw_dir / "search_terms_log.txt"

    # Log query parameters BEFORE any request is made
    log_search_terms(log_path, SEARCH_TERMS, LANGUAGES, PUBLISHER_SITES, max_age_days)

    all_rows: list[dict[str, Any]] = []

    if args.offline_json:
        json_path = Path(args.offline_json)
        if not json_path.exists():
            sys.exit(f"Offline JSON file not found: {json_path}")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Parse either single response dict or list of response dicts
        if isinstance(data, list):
            for item in data:
                all_rows.extend(parse_api_response(item, query_term="offline_json"))
        elif isinstance(data, dict):
            all_rows.extend(parse_api_response(data, query_term="offline_json"))
        else:
            sys.exit(f"Invalid JSON format in {json_path}")
        print(f"Parsed {len(all_rows)} raw records from offline JSON: {json_path}")
    else:
        api_key = get_google_api_key()
        if not api_key:
            sys.exit(
                "Error: GOOGLE_API_KEY environment variable is not set. "
                "Set it, or use --offline-json <path> for dry runs."
            )

        sites = PUBLISHER_SITES if PUBLISHER_SITES else [None]
        for term in SEARCH_TERMS:
            for lang in LANGUAGES:
                for site in sites:
                    page_token: str | None = None
                    while True:
                        resp_data = fetch_api_page(
                            query=term,
                            language_code=lang,
                            site=site,
                            max_age_days=max_age_days,
                            api_key=api_key,
                            page_token=page_token,
                        )
                        rows = parse_api_response(resp_data, query_term=term)
                        all_rows.extend(rows)
                        page_token = resp_data.get("nextPageToken")
                        if not page_token:
                            break

    # Convert to DataFrame
    df = pd.DataFrame(all_rows)
    if df.empty:
        df = pd.DataFrame(columns=[
            "source", "claim_text", "claim_date", "review_date",
            "publisher_name", "publisher_site", "review_url",
            "review_title", "textual_rating", "language_code",
            "text_source", "query_term",
        ])

    initial_count = len(df)
    # Deduplicate exact (claim_text, review_url)
    df = df.drop_duplicates(subset=["claim_text", "review_url"])
    dedup_count = len(df)

    out_csv = raw_dir / "factcheck_api_claims.csv"
    df.to_csv(out_csv, index=False)

    print(f"Stage 1 complete: Collected {initial_count} rows, {dedup_count} distinct (claim, review) rows.")
    print(f"Saved to: {out_csv}")


if __name__ == "__main__":
    main()
