# QA Report: Provenance & Codebook Example Audit (`CODEBOOK.md`)

**Audit Date:** 2026-11-08  
**Auditor:** Quality Assurance Reviewer  
**Population & Scope:** All 29 records cited as real examples or tricky counter-examples in `CODEBOOK.md` (100% census audit; no sampling).  
**Evaluation Protocol:** Each fact-check report at `review_url` was fetched over HTTP and read **prior to** comparing against the claim, `content_form`, `origin`, and `narrative` classifications in `CODEBOOK.md`.

---

## 1. Executive Summary & Audit Metrics

A complete census audit was executed on all 29 records referenced in `CODEBOOK.md` to ensure that every illustrative example directly reflects the documentary evidence established by the fact-checking organizations.

### Key Audit Metrics
* **Total Cited Records Audited:** 29 records (100% census)
* **Score 2 (All Correct):** 20 records (69.0%)
* **Score 1 (Minor Drift / Mislabeled Counter-Example):** 5 records (17.2%)
* **Score 0 (Substantively Wrong / Inverted / Provenance Overlooked):** 4 records (13.8%)

### Key Audit Findings & Resolutions:
1. **`R0080` (Genuine Media Inverted as AI):** Prior draft cited `R0080` as an example of AI generation. Reading The Quint's report revealed that the viral post falsely claimed a genuine photograph taken by *The Hindu* was AI-generated. The report conclusively proved the photo was real. Corrected to `genuine_wrongly_called_fake` (`documented_non_ai`).
2. **`R0096` (Provenance Conclusively Established):** Prior draft cited `R0096` under `not_established`/`unknown`. Reading Lighthouse Journalism's report revealed the fact-checker successfully tracked the video to a February 2026 night clash at Maurice Nagar police station involving AISA students protesting Delhi University elections. Provenance was established, not unknown.
3. **`R0089` (AI Forensic Evidence Overlooked):** Prior draft cited `R0089` under `unknown`. Reading BOOM's report revealed conclusive forensic evidence that the circulating memorial graphic was an AI-generated synthetic visual. Corrected to `documented_ai`.
4. **`R0045` (Voice Deepfake Misclassified as Shallow Crop):** Prior draft cited `R0045` under `cropped_or_edited`. Reading Alt News's report revealed the video was an AI voice clone deepfake superimposing audio onto genuine footage of Piyush Goyal. Corrected to `ai_altered` / `documented_ai`.
5. **`R0039` (Shallow Morphing vs Generative AI):** Prior draft cited `R0039` under `ai_altered`. Reading Telugu Post's report revealed the image was a digital warp/morph (traditional shallowfake editing) rather than generative AI. Relabeled as a tricky counter-example resolving to `cropped_or_edited` / `documented_non_ai`.

---

## 2. Failure Taxonomy (Population N = 29)

| Failure Type | Count | Description |
|:---|:---:|:---|
| `none` (Score 2) | 20 | All fields (claim, content_form, origin, narrative, direction) match source report findings. |
| `genuine_inverted_as_ai` (Score 0) | 1 | Genuine photograph falsely viral as AI was inverted in codebook as synthetic (`R0080`). |
| `provenance_established` (Score 0) | 1 | Video provenance was conclusively traced by outlet to an old protest, but cited under `unknown` (`R0096`). |
| `ai_evidence_overlooked` (Score 0) | 1 | Forensic AI determination by fact-checker was overlooked, coded as `unknown` (`R0089`). |
| `deepfake_labeled_crop` (Score 0) | 1 | AI voice clone deepfake was misclassified as a simple manual video crop (`R0045`). |
| `non_ai_morphed_as_ai` (Score 1) | 1 | Digital photo warp/morph without generative AI was placed under `ai_altered` (`R0039`). |
| `counter_example_mislabeled` (Score 1) | 1 | Record fits primary category but was labeled as a counter-example (`R0010`). |
| `inconsistent_direction` (Score 1) | 1 | Sister records with identical factual scenarios assigned diverging direction codes (`R0085` vs `R0012`). |
| `sub_claim_drift` (Score 1) | 1 | Row captures specific secondary rumor within a larger debunking piece (`R0091`). |
| `domain_timeout` (Score 1) | 1 | NewsMobile domain experienced HTTP connection timeout during live fetch; verified via sister reports (`R0020`). |
| **Total Below Score 2** | **9** | **4 scored 0, 5 scored 1** |

---

## 3. Detailed Audit Table (Starting with Priority Records)

| Packet ID | Record ID | Outlet | Score | Failure Type | Audit Reason & Source Fact-Check Finding |
|:---|:---|:---|:---:|:---|:---|
| `PKT_CB_01` | `R0096` | Lighthouse Journalism | 0 | `provenance_established` | Report conclusively traced video to February Maurice Nagar AISA protest, not untraceable/unknown. |
| `PKT_CB_02` | `R0089` | BOOM | 0 | `ai_evidence_overlooked` | Report investigated visual and proved it was an AI-generated memorial visual, not unknown origin. |
| `PKT_CB_03` | `R0039` | Telugu Post | 1 | `non_ai_morphed_as_ai` | Report states image was digitally morphed/warped (shallowfake), not generative AI. |
| `PKT_CB_04` | `R0014` | BOOM Fact Check | 2 | `none` | All correct: report explicitly documents generative AI crowd magnification and aerial doctoring. |
| `PKT_CB_05` | `R0019` | India Today | 2 | `none` | All correct: report explicitly documents synthetic text-to-image AI generation. |
| `PKT_CB_06` | `R0080` | The Quint | 0 | `genuine_inverted_as_ai` | Report proved photo was genuine by The Hindu photographer; claim falsely alleged it was AI. |
| `PKT_CB_07` | `R0045` | Alt News | 0 | `deepfake_labeled_crop` | Report explicitly identified video as an AI voice deepfake, not simple manual video cropping. |
| `PKT_CB_08` | `R0030` | Lighthouse Journalism | 2 | `none` | All correct: report proved viral Jamaat letter was fabricated on forged letterhead. |
| `PKT_CB_09` | `R0087` | BOOM | 2 | `none` | All correct: report confirmed memorial visual of casualty was AI-generated. |
| `PKT_CB_10` | `R0001` | BOOM Fact Check | 2 | `none` | All correct: report traced archival clip of CM Vijay to May 2026 pre-dating protest. |
| `PKT_CB_11` | `R0002` | BOOM Fact Check | 2 | `none` | All correct: report traced clip of Sunita Williams to January 2026 Kerala Literature Festival. |
| `PKT_CB_12` | `R0007` | The Quint | 2 | `none` | All correct: report proved video was selectively clipped to omit patriotic slogans. |
| `PKT_CB_13` | `R0010` | The Quint | 1 | `counter_example_mislabeled` | Correctly identified as archival Kashmir speech, but mislabeled as counter-example rather than primary example. |
| `PKT_CB_14` | `R0012` | The Quint | 2 | `none` | All correct: report documents archival clip of pro-police civilian gathering outside Kartavya Path. |
| `PKT_CB_15` | `R0020` | NewsMobile | 1 | `domain_timeout` | Live Factly/PTI sister reports confirm Ambika Shukla identity; NewsMobile domain experienced timeout. |
| `PKT_CB_16` | `R0023` | FACTLY | 2 | `none` | All correct: report proved footage was old 2025 clash from Dehradun, Uttarakhand. |
| `PKT_CB_17` | `R0025` | FACTLY | 2 | `none` | All correct: report proved road rage incident occurred in Gaya, Bihar; correctly illustrates Rule T1. |
| `PKT_CB_18` | `R0027` | PTI | 2 | `none` | All correct: report confirmed resignation letter of Dharmendra Pradhan was fabricated on blank template. |
| `PKT_CB_19` | `R0031` | PTI | 2 | `none` | All correct: report traced stone pelting video to old Patna railway station violence. |
| `PKT_CB_20` | `R0036` | FACTLY | 2 | `none` | All correct: report proved video was of an unrelated couple from Bangladesh. |
| `PKT_CB_21` | `R0038` | Telugu Post | 2 | `none` | All correct: report proved video showed CM Vijay at unrelated public rally in Tamil Nadu. |
| `PKT_CB_22` | `R0041` | DigitEye India | 2 | `none` | All correct: report proved kissing clip was from 2014 JNU Kiss of Love campaign. |
| `PKT_CB_23` | `R0047` | NewsMobile | 2 | `none` | All correct: report proved Roadies audition clip did not show founder Abhijeet Dipke. |
| `PKT_CB_24` | `R0053` | विश्वास न्यूज | 2 | `none` | All correct: report proved Anna Hazare press conference image was AI-generated. |
| `PKT_CB_25` | `R0055` | PTI | 2 | `none` | All correct: report verified image of Yogi Adityanath was AI-generated satirical visual. |
| `PKT_CB_26` | `R0061` | AajTak | 2 | `none` | All correct: report proved Head Constable Amit died of health complications, not protester attack. |
| `PKT_CB_27` | `R0085` | FACTLY | 1 | `inconsistent_direction` | Report verified old India Gate clip; correctly coded as other but had inconsistent direction coding. |
| `PKT_CB_28` | `R0086` | India Today | 2 | `none` | All correct: report proved Lallantop interview occurred in February during campus clashes. |
| `PKT_CB_29` | `R0091` | BOOM | 1 | `sub_claim_drift` | Report debunks protest death rumors; row captures specific rumor of news blackout within the piece. |

---

## 4. Verification Files for Human Double-Checking
* **Blind Audit File:** `qa/blind_codebook_examples.csv` — Contains `packet_id`, `review_url`, and empty columns (`content_form`, `origin`) for blind coding by a human auditor (rows randomly shuffled with seed 42).
* **Key File:** `qa/key_codebook_examples.csv` — Contains the unblinded mapping linking `packet_id` to `record_id`, `publisher`, `review_url`, `claim_in_csv`, `audit_score`, `failure_type`, and `audit_reason`.
