# Agent QA Report: Self-Check of Final Coding Sheet (`coding_sheet.csv`)

**Audit Date:** 2026-11-08  
**Auditor:** Antigravity Autonomous Research Agent  
**Sampling Configuration:** `random_state = 42`, $N_{\text{sample}} = 15$, $N_{\text{population}} = 97$

---

## 1. Executive Summary

A self-check qualitative audit was conducted on a random sample of 15 records from the final, post-quarantine `data/processed/coding_sheet.csv` ($N = 97$ records, 81 distinct claims).

For each sampled record, the fact-check report at `review_url` was fetched over HTTP and read **prior to** comparing against the recorded claim text, dates, and publisher.

### Key Audit Metrics
* **Total Population Size:** 97 records
* **Sample Size Audited:** 15 records (Fixed seed: 42)
* **Score Distribution:**
  * **Score 2 (All Correct):** 14 rows (93.3%)
  * **Score 1 (Minor Drift):** 1 row (6.7%)
  * **Score 0 (Wrong / Dead URL / Missing):** 0 rows (0.0%)
* **Zero Failure Rate (Score 0):** **0.0%** (0 / 15)

All 15 URLs resolved to live, authentic fact-checks with HTTP 200 from verified outlets (AajTak, Alt News, AFP, BOOM, DigitEye, Factly, India Today, Lighthouse Journalism, PTI, Telugu Post, Vishwas News, and The Quint).

---

## 2. Failure Taxonomy (Sample N = 15)

| Failure Type | Count | Description |
|:---|:---:|:---|
| `roundup_aggregation` | 1 | Weekly fact-check recap page containing multiple debunked stories; claim matches one of the bundled sub-items (`R0011`). |
| `dead_url` | 0 | No dead URLs or 404 errors observed in final sheet sample. |
| `claim_not_on_page` | 0 | All claims directly substantiated by page text. |
| `date_drift` | 0 | Claim and review dates align with published report metadata. |
| `wrong_publisher` | 0 | Publisher name matches host organization. |
| **Total Items Below Score 2** | **1** | |

---

## 3. Item-by-Item Review (Sample N = 15)

| Packet ID | Record ID | Publisher | Score | Failure Type | Reason |
|:---|:---|:---|:---:|:---|:---|
| `PKT_FINAL_01` | `R0063` | AajTak | 2 | `none` | All correct: verified live page debunks video of injured woman falsely linked to CJP protest. |
| `PKT_FINAL_02` | `R0041` | DigitEye India | 2 | `none` | All correct: verified live page debunks 2014 JNU kissing clip falsely linked to CJP Jantar Mantar protest. |
| `PKT_FINAL_03` | `R0094` | Alt News | 2 | `none` | All correct: verified live page debunks college cultural fest dance performance clip linked to CJP protest. |
| `PKT_FINAL_04` | `R0019` | India Today | 2 | `none` | All correct: verified live page proves image of woman protester in revealing clothing was AI-generated. |
| `PKT_FINAL_05` | `R0082` | The Quint | 2 | `none` | All correct: verified live page debunks Sunita Williams KLF video linked to CJP Jantar Mantar protest. |
| `PKT_FINAL_06` | `R0084` | Telugu Post | 2 | `none` | All correct: verified live page debunks Bihar BPSC lathicharge clip shared as Delhi Police lathicharge on CJP march. |
| `PKT_FINAL_07` | `R0065` | विश्वास न्यूज | 2 | `none` | All correct: verified live page debunks Canada gathering clip misrepresented as CJP protest in Delhi. |
| `PKT_FINAL_08` | `R0043` | FACTLY | 2 | `none` | All correct: verified live page debunks 2010 Arundhati Roy Kashmir speech falsely linked to 2026 CJP agitation. |
| `PKT_FINAL_09` | `R0011` | The Quint | 1 | `roundup_aggregation` | Article is a multi-story weekly recap ("WebQoof Recap: Of Claims Surrounding PM Modi and CJP Protest"); row captures one sub-story. |
| `PKT_FINAL_10` | `R0001` | BOOM Fact Check | 2 | `none` | All correct: verified live page debunks old video of CM Vijay visiting Jantar Mantar. |
| `PKT_FINAL_11` | `R0032` | Lighthouse Journalism | 2 | `none` | All correct: verified live page debunks archival clips of CM Vijay and Sunita Williams at CJP protest. |
| `PKT_FINAL_12` | `R0076` | FACTLY | 2 | `none` | All correct: verified live page debunks viral clips of Tamil Nadu CM Vijay at Jantar Mantar. |
| `PKT_FINAL_13` | `R0048` | AFP Fact Check | 2 | `none` | All correct: verified live page debunks decade-old remarks by Arundhati Roy linked to CJP protest. |
| `PKT_FINAL_14` | `R0027` | PTI | 2 | `none` | All correct: verified live page debunks fake resignation letter of Dharmendra Pradhan shared amid CJP protests. |
| `PKT_FINAL_15` | `R0045` | Alt News | 2 | `none` | All correct: verified live page debunks deepfake video of Piyush Goyal calling to hang cockroaches. |

---

## 4. What This Sample Can and Cannot Tell Us

1. **What It Can Tell Us:**
   * Post-quarantine curation of `coding_sheet.csv` achieved high fidelity (14/15 top score, 0 dead links).
   * Verified fact-checkers actively debunked rumors surrounding the CJP protest across Hindi and English outlets.
2. **What It Cannot Tell Us:**
   * It cannot tell us about the frequency of off-topic posts outside fact-check coverage.
   * It cannot assess public reach on social platforms, as fact-checker reports only sample viral items.
   * Extrapolations are strictly bounded to this sample ($n=15$) and population ($N=97$).
