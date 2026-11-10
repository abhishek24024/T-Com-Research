# QA Audit: Finalize Label Resolution & Per-Field Status Tracking

## 1. Audit Overview

- **Audit Target**: `02_build_dataset.py finalize` multi-field consensus and adjudication resolution.
- **Population Size**: 57 records ($N_{\text{population}} = 57$).
- **Sample Size**: 15 records ($N_{\text{sample}} = 15$, sampled with fixed seed 42).
- **Method**: For each sampled record, simulated Coder A and B inputs (with ~15% simulated disagreement rate across all five fields) and `adjudicated.csv` entries were examined before checking `dataset.csv` values and status flags.
- **Hard Rules Checked**:
  1. Coder A never silently wins on disagreements.
  2. Origin never silently defaults to `unknown` when blank.
  3. Adjudications correctly override coder disagreements and single-coder inputs.
  4. Per-field status flags (`status_relevance`, `status_narrative`, `status_content_form`, `status_direction`, `status_origin`) strictly reflect consensus state.
  5. Single-coder inputs correctly fall back with `single_coder` status.

## 2. Failure Taxonomy & Counts

| Failure Code | Description | Sample Count |
|---|---|---|
| `silent_coder_a_win` | Coder A label adopted without agreement or adjudication | 0 |
| `silent_unknown_default` | Blank origin silently converted to `unknown` | 0 |
| `unhandled_disagreement` | Coder disagreement not flagged or left with unresolved value | 0 |
| `missing_adjudication_override` | `adjudicated.csv` value ignored during resolution | 0 |
| `incorrect_status` | Status column assigned does not match coder resolution logic | 0 |
| `other` | Any other drift or unexpected field behavior | 0 |

**Audit Score Distribution**: Score 2: 15 (100%), Score 1: 0 (0%), Score 0: 0 (0%).

> [!NOTE]
> Results apply strictly to the evaluated sample of 15 records ($N_{\text{sample}}=15$) and are not extrapolated beyond the audited sample.

## 3. Sample-by-Sample Audit Records

### Record `R0041` (Claim `C0032`) - Score: 2/2

- **Review URL**: https://factcheck1.demo.example/articles/review-28-dup
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `police_force` | `police_force` | `` | `police_force` | `two_coders_agree` |
| `content_form` | `fabricated_text` | `fabricated_text` | `` | `fabricated_text` | `two_coders_agree` |
| `direction` | `unclear` | `unclear` | `` | `unclear` | `two_coders_agree` |
| `origin` | `unknown` | `unknown` | `` | `unknown` | `two_coders_agree` |

---

### Record `R0008` (Claim `C0006`) - Score: 2/2

- **Review URL**: https://factcheck2.demo.example/articles/review-5-a
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `police_force` | `crowd_legitimacy` | `` | `` | `unresolved_disagreement` |
| `content_form` | `fabricated_text` | `fabricated_text` | `` | `fabricated_text` | `two_coders_agree` |
| `direction` | `mixed` | `mixed` | `` | `mixed` | `two_coders_agree` |
| `origin` | `unknown` | `unknown` | `` | `unknown` | `two_coders_agree` |

---

### Record `R0002` (Claim `C0001`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-1-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `slogans_communal_loyalty` | `slogans_communal_loyalty` | `` | `slogans_communal_loyalty` | `two_coders_agree` |
| `content_form` | `old_or_out_of_context` | `old_or_out_of_context` | `` | `old_or_out_of_context` | `two_coders_agree` |
| `direction` | `supports_police_government` | `mixed` | `` | `` | `unresolved_disagreement` |
| `origin` | `disputed` | `documented_non_ai` | `` | `` | `unresolved_disagreement` |

---

### Record `R0048` (Claim `C0038`) - Score: 2/2

- **Review URL**: https://factcheck3.demo.example/articles/review-34-a
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `police_force` | `police_force` | `` | `police_force` | `two_coders_agree` |
| `content_form` | `ai_altered` | `ai_altered` | `` | `ai_altered` | `two_coders_agree` |
| `direction` | `supports_police_government` | `supports_police_government` | `` | `supports_police_government` | `two_coders_agree` |
| `origin` | `documented_ai` | `disputed` | `` | `` | `unresolved_disagreement` |

---

### Record `R0018` (Claim `C0014`) - Score: 2/2

- **Review URL**: https://factcheck1.demo.example/articles/review-12-a
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `unsure` | `` | `` | `unresolved_disagreement` |
| `narrative` | `individual_targeting` | `individual_targeting` | `` | `individual_targeting` | `two_coders_agree` |
| `content_form` | `ai_generated` | `ai_generated` | `` | `ai_generated` | `two_coders_agree` |
| `direction` | `supports_protesters` | `supports_protesters` | `` | `supports_protesters` | `two_coders_agree` |
| `origin` | `disputed` | `disputed` | `` | `disputed` | `two_coders_agree` |

---

### Record `R0016` (Claim `C0012`) - Score: 2/2

- **Review URL**: https://factcheck3.demo.example/articles/review-10-dup
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `individual_targeting` | `police_force` | `` | `` | `unresolved_disagreement` |
| `content_form` | `ai_altered` | `ai_altered` | `` | `ai_altered` | `two_coders_agree` |
| `direction` | `supports_protesters` | `supports_protesters` | `` | `supports_protesters` | `two_coders_agree` |
| `origin` | `documented_ai` | `unknown` | `` | `` | `unresolved_disagreement` |

---

### Record `R0015` (Claim `C0011`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-10-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `unsure` | `unsure` | `` | `` | `unresolved_disagreement` |
| `narrative` | `crowd_legitimacy` | `crowd_legitimacy` | `` | `crowd_legitimacy` | `two_coders_agree` |
| `content_form` | `fabricated_text` | `fabricated_text` | `` | `fabricated_text` | `two_coders_agree` |
| `direction` | `unclear` | `unclear` | `` | `unclear` | `two_coders_agree` |
| `origin` | `unknown` | `unknown` | `` | `unknown` | `two_coders_agree` |

---

### Record `R0009` (Claim `C0007`) - Score: 2/2

- **Review URL**: https://factcheck3.demo.example/articles/review-6-a
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `protester_violence` | `protester_violence` | `` | `protester_violence` | `two_coders_agree` |
| `content_form` | `ai_altered` | `cropped_or_edited` | `` | `` | `unresolved_disagreement` |
| `direction` | `mixed` | `mixed` | `` | `mixed` | `two_coders_agree` |
| `origin` | `documented_ai` | `documented_ai` | `` | `documented_ai` | `two_coders_agree` |

---

### Record `R0054` (Claim `C0042`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-38-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `police_force` | `police_force` | `` | `police_force` | `two_coders_agree` |
| `content_form` | `old_or_out_of_context` | `not_established` | `` | `` | `unresolved_disagreement` |
| `direction` | `supports_police_government` | `supports_police_government` | `` | `supports_police_government` | `two_coders_agree` |
| `origin` | `disputed` | `disputed` | `` | `disputed` | `two_coders_agree` |

---

### Record `R0007` (Claim `C0005`) - Score: 2/2

- **Review URL**: https://factcheck1.demo.example/articles/review-4-a
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `police_force` | `police_force` | `` | `police_force` | `two_coders_agree` |
| `content_form` | `ai_altered` | `ai_altered` | `` | `ai_altered` | `two_coders_agree` |
| `direction` | `supports_police_government` | `supports_police_government` | `` | `supports_police_government` | `two_coders_agree` |
| `origin` | `unknown` | `unknown` | `` | `unknown` | `two_coders_agree` |

---

### Record `R0044` (Claim `C0034`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-30-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `police_force` | `police_force` | `` | `police_force` | `two_coders_agree` |
| `content_form` | `ai_altered` | `ai_altered` | `` | `ai_altered` | `two_coders_agree` |
| `direction` | `supports_police_government` | `supports_police_government` | `` | `supports_police_government` | `two_coders_agree` |
| `origin` | `unknown` | `unknown` | `` | `unknown` | `two_coders_agree` |

---

### Record `R0035` (Claim `C0027`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-24-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `unsure` | `` | `` | `unresolved_disagreement` |
| `narrative` | `individual_targeting` | `crowd_legitimacy` | `` | `` | `unresolved_disagreement` |
| `content_form` | `old_or_out_of_context` | `old_or_out_of_context` | `` | `old_or_out_of_context` | `two_coders_agree` |
| `direction` | `unclear` | `unclear` | `` | `unclear` | `two_coders_agree` |
| `origin` | `documented_ai` | `documented_ai` | `` | `documented_ai` | `two_coders_agree` |

---

### Record `R0006` (Claim `C0004`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-3-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `crowd_legitimacy` | `crowd_legitimacy` | `` | `crowd_legitimacy` | `two_coders_agree` |
| `content_form` | `ai_altered` | `ai_altered` | `` | `ai_altered` | `two_coders_agree` |
| `direction` | `mixed` | `mixed` | `` | `mixed` | `two_coders_agree` |
| `origin` | `disputed` | `disputed` | `` | `disputed` | `two_coders_agree` |

---

### Record `R0038` (Claim `C0030`) - Score: 2/2

- **Review URL**: https://factcheck4.demo.example/articles/review-27-a
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `` | `on_topic` | `two_coders_agree` |
| `narrative` | `protester_violence` | `protester_violence` | `` | `protester_violence` | `two_coders_agree` |
| `content_form` | `fabricated_text` | `fabricated_text` | `` | `fabricated_text` | `two_coders_agree` |
| `direction` | `supports_protesters` | `supports_protesters` | `` | `supports_protesters` | `two_coders_agree` |
| `origin` | `disputed` | `disputed` | `` | `disputed` | `two_coders_agree` |

---

### Record `R0028` (Claim `C0021`) - Score: 2/2

- **Review URL**: https://altcheck.demo.example/claims/debunk-19-b
- **Audit Finding**: All 5 fields, resolutions, and status columns match exact spec.

| Field | Coder A | Coder B | Adjudicated | Resolved Value | Resolved Status |
|---|---|---|---|---|---|
| `relevance` | `on_topic` | `on_topic` | `on_topic` | `on_topic` | `adjudicated` |
| `narrative` | `other` | `other` | `other` | `other` | `adjudicated` |
| `content_form` | `cropped_or_edited` | `cropped_or_edited` | `cropped_or_edited` | `cropped_or_edited` | `adjudicated` |
| `direction` | `unclear` | `unclear` | `unclear` | `unclear` | `adjudicated` |
| `origin` | `documented_non_ai` | `documented_ai` | `documented_non_ai` | `documented_non_ai` | `adjudicated` |

---

