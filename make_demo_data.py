#!/usr/bin/env python3
"""Generates FAKE demo data for pipeline dry runs in isolated scratch directories.

Hard rules:
- All URLs use demo.example.
- Never mixed into real data/ or cited in reports.
- Tests filters (out-of-window dates, exact duplicates, second outlet reviewing same claim).

Subcommands:
  fake-api [--out PATH] [--truth-out PATH]
  simulate-coders [--sheet PATH] [--flip-rate FLOAT]
"""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Any
import pandas as pd

from config import (
    CONTENT_FORMS,
    DIRECTIONS,
    NARRATIVES,
    SEED,
    get_processed_data_dir,
    get_raw_data_dir,
)

# Demo claims designed to exercise all filters, languages, and narratives
DEMO_CLAIMS_BLUEPRINT = [
    # Narrative: police_force
    {
        "text": "Delhi police attacked peaceful students with baton charge and tear gas at Jantar Mantar",
        "date": "2026-07-21",
        "narrative": "police_force",
        "form": "old_or_out_of_context",
        "direction": "supports_protesters",
        "outlet2": True,
        "near_dup": "Police used lathicharge and tear gas shells on protesting students at Jantar Mantar Delhi",
    },
    {
        "text": "दिल्ली पुलिस ने शांतिपूर्ण प्रदर्शन कर रहे छात्रों पर बर्बर लाठीचार्ज किया",
        "date": "2026-07-21",
        "narrative": "police_force",
        "form": "ai_altered",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "Viral video shows water cannons deployed against women demonstrators at Jantar Mantar",
        "date": "2026-07-20",
        "narrative": "police_force",
        "form": "cropped_or_edited",
        "direction": "supports_protesters",
        "outlet2": True,
    },
    {
        "text": "Police brutally thrashing innocent NEET aspirants outside parliament street",
        "date": "2026-07-22",
        "narrative": "police_force",
        "form": "old_or_out_of_context",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "CJP protest turned violent when police blocked the march route",
        "date": "2026-07-20",
        "narrative": "police_force",
        "form": "disputed",
        "direction": "mixed",
        "outlet2": False,
    },
    {
        "text": "Police lathi charge visuals from 2020 falsely linked to recent student protest",
        "date": "2026-07-23",
        "narrative": "police_force",
        "form": "old_or_out_of_context",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "ye clip dekh lo police ne students ko peet dala jantarmantar par",
        "date": "2026-07-21",
        "narrative": "police_force",
        "form": "fabricated_text",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "Police officer assaulted female students during detention at Jantar Mantar",
        "date": "2026-07-24",
        "narrative": "police_force",
        "form": "not_established",
        "direction": "supports_protesters",
        "outlet2": True,
    },
    {
        "text": "Water cannons sprayed colored chemical water at young protesters",
        "date": "2026-07-22",
        "narrative": "police_force",
        "form": "ai_generated",
        "direction": "supports_protesters",
        "outlet2": False,
    },

    # Narrative: protester_violence
    {
        "text": "Protesters pelting stones at Delhi police personnel and setting barricades on fire",
        "date": "2026-07-21",
        "narrative": "protester_violence",
        "form": "old_or_out_of_context",
        "direction": "supports_police_government",
        "outlet2": True,
        "near_dup": "Violent demonstrators pelted heavy stones at police during Jantar Mantar rally",
    },
    {
        "text": "छात्रों ने पुलिस पर पथराव किया और सरकारी बसों में तोड़फोड़ की",
        "date": "2026-07-21",
        "narrative": "protester_violence",
        "form": "ai_generated",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Visuals show mob carrying petrol bombs near central Delhi protest site",
        "date": "2026-07-22",
        "narrative": "protester_violence",
        "form": "fabricated_text",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "ye dekho students ne barricade tod kar danga kiya aur police par hamla kiya",
        "date": "2026-07-21",
        "narrative": "protester_violence",
        "form": "old_or_out_of_context",
        "direction": "supports_police_government",
        "outlet2": True,
    },
    {
        "text": "Protesters armed with iron rods attacking security personnel in Delhi",
        "date": "2026-07-23",
        "narrative": "protester_violence",
        "form": "old_or_out_of_context",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "CJP protest mob vandalized public property and burnt two police motorcycles",
        "date": "2026-07-20",
        "narrative": "protester_violence",
        "form": "cropped_or_edited",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "प्रदर्शनकारियों ने संसद मार्ग पर पुलिस वैन पर हमला किया",
        "date": "2026-07-22",
        "narrative": "protester_violence",
        "form": "disputed",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Stones hurled from inside the crowd injuring three head constables",
        "date": "2026-07-21",
        "narrative": "protester_violence",
        "form": "not_established",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Video of clash in Bangladesh shared as Jantar Mantar violence by protesters",
        "date": "2026-07-24",
        "narrative": "protester_violence",
        "form": "old_or_out_of_context",
        "direction": "supports_protesters",
        "outlet2": True,
    },

    # Narrative: slogans_communal_loyalty
    {
        "text": "Pro-Pakistan anti-national slogans raised at Jantar Mantar student gathering",
        "date": "2026-07-22",
        "narrative": "slogans_communal_loyalty",
        "form": "ai_altered",
        "direction": "supports_police_government",
        "outlet2": True,
        "near_dup": "Audio doctored to claim anti-India slogans chanted at student demonstration",
    },
    {
        "text": "छात्र प्रदर्शन में देश विरोधी और साम्प्रदायिक नारे लगाए गए",
        "date": "2026-07-23",
        "narrative": "slogans_communal_loyalty",
        "form": "ai_altered",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Video of religious chants falsely captioned as anti-national slogans at Delhi protest",
        "date": "2026-07-21",
        "narrative": "slogans_communal_loyalty",
        "form": "cropped_or_edited",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "Hate speech slogans against minority community raised by counter-protesters",
        "date": "2026-07-24",
        "narrative": "slogans_communal_loyalty",
        "form": "genuine_wrongly_called_fake",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "Foreign funded extremist elements infiltrated the students protest shouting separatism",
        "date": "2026-07-22",
        "narrative": "slogans_communal_loyalty",
        "form": "fabricated_text",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Doctored audio added to protest footage to show communal chanting",
        "date": "2026-07-25",
        "narrative": "slogans_communal_loyalty",
        "form": "ai_altered",
        "direction": "supports_protesters",
        "outlet2": True,
    },
    {
        "text": "ye log desh ke khilaf narebazi kar rahe the jantar mantar par",
        "date": "2026-07-23",
        "narrative": "slogans_communal_loyalty",
        "form": "fabricated_text",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Khalistan flags waved during youth rally in central Delhi",
        "date": "2026-07-24",
        "narrative": "slogans_communal_loyalty",
        "form": "old_or_out_of_context",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Communal clashes broke out between students and locals near Connaught Place",
        "date": "2026-07-22",
        "narrative": "slogans_communal_loyalty",
        "form": "fabricated_text",
        "direction": "supports_police_government",
        "outlet2": False,
    },

    # Narrative: crowd_legitimacy
    {
        "text": "Over 500000 students gathered at Jantar Mantar breaking all historical records",
        "date": "2026-07-20",
        "narrative": "crowd_legitimacy",
        "form": "ai_generated",
        "direction": "supports_protesters",
        "outlet2": True,
        "near_dup": "AI generated aerial crowd image falsely claims five lakh students at protest",
    },
    {
        "text": "Empty chairs and nobody attended the flop demonstration called by opposition",
        "date": "2026-07-21",
        "narrative": "crowd_legitimacy",
        "form": "old_or_out_of_context",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "AI image showing sea of people at Jantar Mantar debunked as synthetic creation",
        "date": "2026-07-23",
        "narrative": "crowd_legitimacy",
        "form": "ai_generated",
        "direction": "supports_police_government",
        "outlet2": True,
    },
    {
        "text": "जंतर मंतर पर लाखों छात्रों की भीड़ का एआई जनरेटेड वीडियो वायरल",
        "date": "2026-07-21",
        "narrative": "crowd_legitimacy",
        "form": "ai_generated",
        "direction": "unclear",
        "outlet2": False,
    },
    {
        "text": "Paid actors were brought on buses to pretend to be protesting NEET candidates",
        "date": "2026-07-22",
        "narrative": "crowd_legitimacy",
        "form": "fabricated_text",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "International human rights observers arrived at Jantar Mantar to support crowd",
        "date": "2026-07-24",
        "narrative": "crowd_legitimacy",
        "form": "fabricated_text",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "Old concert gathering from Mumbai shared as historic student turnout",
        "date": "2026-07-22",
        "narrative": "crowd_legitimacy",
        "form": "old_or_out_of_context",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    {
        "text": "Drone video shows only twenty people present at protest venue",
        "date": "2026-07-21",
        "narrative": "crowd_legitimacy",
        "form": "cropped_or_edited",
        "direction": "supports_police_government",
        "outlet2": False,
    },
    {
        "text": "Synthetic photo showing massive crowd stretching across India Gate",
        "date": "2026-07-25",
        "narrative": "crowd_legitimacy",
        "form": "ai_generated",
        "direction": "supports_protesters",
        "outlet2": True,
    },

    # Narrative: other (or small narrative that tests rare-class merge)
    {
        "text": "NASA satellite captured thermal image of student gathering in Delhi",
        "date": "2026-07-23",
        "narrative": "other",
        "form": "fabricated_text",
        "direction": "unclear",
        "outlet2": False,
    },
    {
        "text": "Supreme Court ordered immediate suspension of all exams nationwide",
        "date": "2026-07-21",
        "narrative": "other",
        "form": "fabricated_text",
        "direction": "supports_protesters",
        "outlet2": True,
    },
    {
        "text": "Metro station completely shut down due to protest disruption",
        "date": "2026-07-20",
        "narrative": "other",
        "form": "old_or_out_of_context",
        "direction": "unclear",
        "outlet2": False,
    },
    {
        "text": "Opposition party leader resigned after protest speech controversy",
        "date": "2026-07-24",
        "narrative": "other",
        "form": "fabricated_text",
        "direction": "unclear",
        "outlet2": False,
    },

    # Testing date filters:
    # 1. Out-of-window date (before CLAIM_WINDOW_START)
    {
        "text": "Old claim from May 2026 before protest window started",
        "date": "2026-05-15",
        "review_date": "2026-05-18",
        "narrative": "other",
        "form": "old_or_out_of_context",
        "direction": "unclear",
        "outlet2": False,
    },
    # 2. Out-of-window date (after CLAIM_WINDOW_END)
    {
        "text": "Late claim from August 2026 after protest window closed",
        "date": "2026-08-10",
        "review_date": "2026-08-12",
        "narrative": "other",
        "form": "old_or_out_of_context",
        "direction": "unclear",
        "outlet2": False,
    },
    # 3. Missing claim date, but valid review date inside [start, cutoff]
    {
        "text": "Claim with missing claim date investigated in late August",
        "date": "",
        "review_date": "2026-08-28",
        "narrative": "police_force",
        "form": "old_or_out_of_context",
        "direction": "supports_protesters",
        "outlet2": False,
    },
    # 4. Missing claim date and review date after cutoff
    {
        "text": "Review published after report cutoff date",
        "date": "",
        "review_date": "2026-10-25",
        "narrative": "other",
        "form": "fabricated_text",
        "direction": "unclear",
        "outlet2": False,
    },
]


def make_fake_api_response() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Builds fake API response dict adhering strictly to Google Fact Check Tools API format."""
    claims_list: list[dict[str, Any]] = []
    ground_truth: list[dict[str, Any]] = []

    outlet_counter = 1
    for idx, item in enumerate(DEMO_CLAIMS_BLUEPRINT, start=1):
        claim_text = item["text"]
        claim_date = item["date"]
        rev_date = item.get("review_date") or "2026-07-28"
        narrative = item["narrative"]
        form = item["form"]
        direction = item["direction"]

        # Primary review
        pub1 = {
            "name": f"Demo Fact Checker {outlet_counter % 4 + 1}",
            "site": f"factcheck{outlet_counter % 4 + 1}.demo.example",
        }
        review1 = {
            "publisher": pub1,
            "url": f"https://factcheck{outlet_counter % 4 + 1}.demo.example/articles/review-{idx}-a",
            "title": f"Fact Check: {claim_text[:40]}...",
            "reviewDate": rev_date,
            "textualRating": "False",
            "languageCode": "hi" if any(ord(c) > 0x0900 and ord(c) < 0x097F for c in claim_text) else "en",
        }

        reviews = [review1]

        # Second outlet reviewing the same claim
        if item.get("outlet2"):
            pub2 = {
                "name": "Alternative Demo Checker",
                "site": "altcheck.demo.example",
            }
            review2 = {
                "publisher": pub2,
                "url": f"https://altcheck.demo.example/claims/debunk-{idx}-b",
                "title": f"Debunked: {claim_text[:35]}...",
                "reviewDate": rev_date,
                "textualRating": "Misleading",
                "languageCode": review1["languageCode"],
            }
            reviews.append(review2)

        claim_entry = {
            "text": claim_text,
            "claimant": f"DemoClaimant_{idx}",  # Test that stage 1 drops claimant
            "claimDate": f"{claim_date}T12:00:00Z" if claim_date else "",
            "claimReview": reviews,
        }
        claims_list.append(claim_entry)

        ground_truth.append({
            "claim_text": claim_text,
            "narrative": narrative,
            "content_form": form,
            "direction": direction,
        })

        # Near-duplicate claim if blueprint has one
        if "near_dup" in item:
            near_dup_text = item["near_dup"]
            claim_entry_dup = {
                "text": near_dup_text,
                "claimant": f"DemoClaimant_dup_{idx}",
                "claimDate": f"{claim_date}T15:00:00Z" if claim_date else "",
                "claimReview": [
                    {
                        "publisher": pub1,
                        "url": f"https://factcheck{outlet_counter % 4 + 1}.demo.example/articles/review-{idx}-dup",
                        "title": f"Fact Check Dup: {near_dup_text[:40]}...",
                        "reviewDate": rev_date,
                        "textualRating": "Manipulated Media",
                        "languageCode": "en",
                    }
                ],
            }
            claims_list.append(claim_entry_dup)
            ground_truth.append({
                "claim_text": near_dup_text,
                "narrative": narrative,
                "content_form": form,
                "direction": direction,
            })

        outlet_counter += 1

    # Exact duplicate claim to test exact deduping
    exact_dup = dict(claims_list[0])
    claims_list.append(exact_dup)

    api_response = {
        "claims": claims_list,
        "nextPageToken": None,
    }
    return api_response, ground_truth


def run_fake_api(out_path: Path | None = None, truth_path: Path | None = None) -> None:
    api_resp, truth = make_fake_api_response()
    if out_path is None:
        out_path = get_raw_data_dir() / "demo_api_response.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(api_resp, f, indent=2, ensure_ascii=False)

    if truth_path is None:
        truth_path = get_raw_data_dir() / "demo_ground_truth.json"
    truth_path.parent.mkdir(parents=True, exist_ok=True)
    with open(truth_path, "w", encoding="utf-8") as f:
        json.dump(truth, f, indent=2, ensure_ascii=False)

    print(f"Generated fake API response with {len(api_resp['claims'])} claims to: {out_path}")
    print(f"Saved demo ground truth to: {truth_path}")


def run_simulate_coders(sheet_path: Path | None = None, flip_rate: float = 0.10) -> None:
    """Reads coding_sheet.csv and produces coder_A.csv, coder_B.csv, and adjudicated.csv."""
    if sheet_path is None:
        sheet_path = get_processed_data_dir() / "coding_sheet.csv"
    if not sheet_path.exists():
        sys.exit(f"Error: {sheet_path} does not exist. Run Stage 2a first.")

    raw_dir = get_raw_data_dir()
    truth_path = raw_dir / "demo_ground_truth.json"
    truth_map = {}
    if truth_path.exists():
        with open(truth_path, "r", encoding="utf-8") as f:
            truth_items = json.load(f)
            for item in truth_items:
                truth_map[item["claim_text"]] = item

    sheet_df = pd.read_csv(sheet_path)
    random.seed(SEED)

    records_a = []
    records_b = []
    records_adj = []

    for _, row in sheet_df.iterrows():
        r_id = row["record_id"]
        c_text = row["claim_text"]
        truth_entry = truth_map.get(c_text, {})

        gold_narrative = truth_entry.get("narrative") or "police_force"
        gold_form = truth_entry.get("content_form") or "old_or_out_of_context"
        gold_direction = truth_entry.get("direction") or "supports_protesters"

        # Coder A labels with gold truth
        records_a.append({
            "record_id": r_id,
            "relevance": "on_topic",
            "narrative": gold_narrative,
            "content_form": gold_form,
            "direction": gold_direction,
            "origin": "documented_non_ai",
            "coder_notes": "Coder A demo label",
        })

        # Coder B has ~10% flipped narrative to simulate real human coder disagreement
        narr_b = gold_narrative
        form_b = gold_form
        direction_b = gold_direction
        is_flipped = random.random() < flip_rate
        if is_flipped:
            alt_narratives = [n for n in NARRATIVES if n != gold_narrative]
            narr_b = random.choice(alt_narratives)

        records_b.append({
            "record_id": r_id,
            "relevance": "on_topic",
            "narrative": narr_b,
            "content_form": form_b,
            "direction": direction_b,
            "origin": "documented_non_ai",
            "coder_notes": "Coder B demo label",
        })

        # If disagreed, simulate third coder resolving the disagreement
        if narr_b != gold_narrative:
            records_adj.append({
                "record_id": r_id,
                "narrative": gold_narrative,  # Adjudicator resolves back to gold
            })

    coder_a_df = pd.DataFrame(records_a)
    coder_b_df = pd.DataFrame(records_b)
    adj_df = pd.DataFrame(records_adj)

    coder_a_path = raw_dir / "coder_A.csv"
    coder_b_path = raw_dir / "coder_B.csv"
    adj_path = raw_dir / "adjudicated.csv"

    coder_a_df.to_csv(coder_a_path, index=False)
    coder_b_df.to_csv(coder_b_path, index=False)
    adj_df.to_csv(adj_path, index=False)

    print(f"Simulated coders generated across {len(sheet_df)} records:")
    print(f"  Coder A saved to: {coder_a_path}")
    print(f"  Coder B saved to: {coder_b_path} ({len(records_adj)} flipped records, {flip_rate*100:.1f}% rate)")
    print(f"  Adjudicated resolutions saved to: {adj_path} ({len(adj_df)} records)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate demo data for testing.")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    fake_p = subparsers.add_parser("fake-api", help="Create fake API response.")
    fake_p.add_argument("--out", type=str, default=None)
    fake_p.add_argument("--truth-out", type=str, default=None)

    sim_p = subparsers.add_parser("simulate-coders", help="Simulate human coder CSVs.")
    sim_p.add_argument("--sheet", type=str, default=None)
    sim_p.add_argument("--flip-rate", type=float, default=0.10)

    args = parser.parse_args()
    if args.subcommand == "fake-api":
        run_fake_api(
            out_path=Path(args.out) if args.out else None,
            truth_path=Path(args.truth_out) if args.truth_out else None,
        )
    elif args.subcommand == "simulate-coders":
        run_simulate_coders(
            sheet_path=Path(args.sheet) if args.sheet else None,
            flip_rate=args.flip_rate,
        )


if __name__ == "__main__":
    main()
