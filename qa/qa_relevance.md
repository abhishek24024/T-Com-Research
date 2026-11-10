# Agent QA Report: Topic Relevance Audit of API Claims

**Audit Date:** 2026-11-07  
**Auditor:** Antigravity Autonomous Research Agent  
**Sampling Configuration:** `random_state = 42`, $N_{\text{sample}} = 40$, $N_{\text{population}} = 208$ API records

---

## 1. Executive Summary

The Google Fact Check Tools API retrieves claims matching lexical keywords (`SEARCH_TERMS`), which capture a broader corpus than the specific **20 July 2026 Jantar Mantar NEET protests** defined in the course build specification.

An audit was conducted on 40 sampled API records to assess on-topic relevance:
* **Population Size:** 208 Fact Check API records
* **Sample Size Audited:** 40 records (Seed 42)
* **Relevance Breakdown:**
  * **On-Topic (`yes`):** 27 / 40 (**67.5%**)
  * **Off-Topic (`no`):** 12 / 40 (**30.0%**)
  * **Ambiguous / Unclear (`unclear`):** 1 / 40 (**2.5%**)

### Observed Off-Topic Rate
Approximately **32.5%** of API records returned for generic protest terms relate to events outside the core study focus (e.g., separate October 2026 demonstrations in other cities, personal controversies surrounding the movement's founder, or unrelated regional protests).

---

## 2. Failure Taxonomy: Why Off-Topic Rows Matched

| Failure Type | Count | Reason for Search Query Match |
| --- | --- | --- |
| `different_city_date_protest` | 4 | Protests, rallies, or clashes in Mumbai (Shivaji Park), Jaipur, Jharkhand, or Kolkata matched queries like "CJP protest". |
| `autumn_october_demonstration` | 3 | CJP organized a second wave of demonstrations on 10 October 2026 demanding the CEC's resignation, matching "CJP protest". |
| `founder_personal_controversy` | 2 | Satirical memes and personal attacks against CJP founder Abhijeet Dipke matched "Cockroach Janta Party". |
| `celebrity_endorsement_unrelated` | 1 | Misattributed video of actor Nana Patekar speaking to a film producer matched search keywords. |
| `unrelated_crime_case` | 1 | Report on Lakhimpur Kheri witness murder mentioned the CJP protest solely as an incidental timeline reference. |
| `political_party_meeting` | 1 | Video of political delegation meetings in Jharkhand matched the movement's name. |
| `generic_political_harassment` | 1 | Domestic dispute video captioned with generic anti-government hashtags. |
| **Total Non-Core Rows (`no` or `unclear`)** | **13** | |

---

## 3. Topic Flagging Implementation in `coding_sheet.csv`

To assist human coders without auto-dropping rows, a `topic_flag` column is added to `coding_sheet.csv`:
* `likely_on_topic`: Records containing core protest markers (e.g. `jantar mantar`, `20 july`, `neet`, `lathicharge`, `लाठीचार्ज`, `संसद मार्च`, `student`, `छात्र`, `police`, `पुलिस`, `crowd`, `stone`, `पथराव`, `protest`, `प्रदर्शन`) and lacking explicit geographic or temporal exclusions.
* `needs_check`: Records containing explicit off-topic markers (e.g. `10 october`, `shivaji park`, `mumbai`, `jaipur`, `kolkata`, `jharkhand`, `bihar`, `lakhimpur`, `nana patekar`) or lacking protest action keywords.

> **Crucial Rule:** The pipeline does **NOT** auto-drop `needs_check` rows. Human researchers make the final decision during qualitative coding.

---

## 4. Item-by-Item Review of Off-Topic and Borderline Items (N = 13)

| Sample ID | Publisher | On-Topic | Failure Type | Specific Reason |
| --- | --- | --- | --- | --- |
| `REL_01` | AajTak | `no` | `unrelated_crime_case` | Concerns Lakhimpur Kheri witness murder claim; mentions CJP protest only as background timestamp. |
| `REL_06` | The Quint | `no` | `autumn_october_demonstration` | Asserts an October 10 CJP demonstration, outside the 20 July study window. |
| `REL_07` | FACTLY | `no` | `founder_personal_controversy` | Personal video controversy attacking founder's private past rather than the protest demonstration. |
| `REL_08` | AajTak | `no` | `celebrity_endorsement_unrelated` | Misattributed video message from Nana Patekar to a film producer, unrelated to protest. |
| `REL_09` | FACTLY | `no` | `different_city_date_protest` | Concerns October 2 rally at Shivaji Park in Mumbai, not the Delhi July demonstration. |
| `REL_12` | Dismislab | `no` | `autumn_october_demonstration` | Refers to October 10 protest logistical rumors in Haryana/Delhi. |
| `REL_19` | NewsMobile | `no` | `autumn_october_demonstration` | Video of metro disruption claimed during the October 10 protest. |
| `REL_25` | FACTLY | `unclear` | `generic_political_harassment` | Domestic violence clip shared with anti-government hashtags; unclear connection to Jantar Mantar. |
| `REL_28` | FACTLY | `no` | `different_city_date_protest` | Incident occurred in Jaipur, Rajasthan, not Delhi Jantar Mantar. |
| `REL_32` | FACTLY | `no` | `political_party_meeting` | Political party meeting in Jharkhand, not the student demonstration. |
| `REL_33` | FACTLY | `no` | `different_city_date_protest` | Concerns a Jharkhand student agitation, distinct from the Delhi protest. |
| `REL_34` | NewsMobile | `no` | `founder_personal_controversy` | Satirical photo meme regarding founder meeting PM Modi. |
| `REL_35` | Alt News | `no` | `different_city_date_protest` | Stone-pelting claim regarding a protest in Kolkata, not Delhi. |

---

## 5. What This Sample Can and Cannot Tell Us

1. **What It Tells Us:**
   * Broad API keyword searches over-retrieve by ~30% because the movement organized multiple regional agitations across different months (July vs October, Delhi vs Mumbai/Jaipur/Kolkata).
   * Date filtering alone (June 6 to July 25, 2026) removes many October claims, but claims lacking a specific `claim_date` require the `topic_flag` heuristic to alert human coders.
2. **What It Cannot Tell Us:**
   * It cannot replace human judgment on whether peripheral claims (e.g. counter-protests or nationwide solidarity marches) belong in the study scope.
   * Results apply strictly to the 40 sampled items ($N=40$) and should not be extrapolated as a universal precision score across other fact-check topics.
