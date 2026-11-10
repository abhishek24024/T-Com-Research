# Pilot Coding Reliability & Disagreement Analysis

## 1. Executive Summary & Codebook Version Context

- **Pilot Sample Size**: $n = 16$ records sampled from `data/processed/pilot_sample.csv`.
- **Coders**: Two independent coders completed `data/processed/pilot_A.xlsx` and `pilot_B.xlsx`.
- **Conversion to CSV**: Converted using `xlsx_to_csv.py` with zero conversion errors across both workbooks (16 rows validated per coder).
- **Active Codebook Version**: The pilot was executed under **`CODEBOOK.md` Version 1.2 (STATUS: DRAFT v1.2: pending team approval)**.
  - **Content Form Hedging Rule**: **NOT PRESENT** in v1.2.
  - **Off-Topic / Unsure Blank-Cell Rule**: **NOT PRESENT** in v1.2.
- **Overall Reliability**:
  - `relevance`: 100.0% agreement (Kappa: 1.000 / degenerate due to single-class marginals).
  - `origin`: 93.8% agreement (Kappa: 0.765).
  - `direction`: 87.5% agreement (Kappa: 0.748).
  - `content_form`: 75.0% agreement (Kappa: 0.543).
  - `narrative`: 50.0% agreement (Kappa: 0.360) — primary area of inter-coder divergence.
- **Census of Disagreements**: Exactly 15 disagreeing cells across 12 distinct records.

---

## 2. Field-by-Field Inter-Coder Reliability Metrics

| Field | $n$ Rows | Percent Agreement | Cohen's Kappa | Reliability Assessment & Marginal Nuances |
|---|---|---|---|---|
| **`relevance`** | 16 | **100.0%** | **1.000** | **Mathematically degenerate**: Both coders coded 100% of rows as `on_topic` ($16/16$). With zero marginal variance, kappa is uninformative. |
| **`narrative`** | 16 | **50.0%** | **0.360** | **Low agreement**: Driven by systemic confusion between `individual_targeting` vs `crowd_legitimacy` (4 cases), and missing rules on multi-clip compilations. |
| **`content_form`** | 16 | **75.0%** | **0.543** | **Moderate agreement**: 10 agreed cases of `old_or_out_of_context`. Divergences stemmed from AI voice-cloning vs full generation and text rumors vs `not_established`. |
| **`direction`** | 16 | **87.5%** | **0.748** | **Substantial agreement**: 14 of 16 rows agreed. Disagreements occurred on multi-clip compilations and ambiguous AI images. |
| **`origin`** | 16 | **93.8%** | **0.765** | **Substantial agreement**: Heavily skewed toward `documented_non_ai` ($13/16$). 1 disagreement where Coder B assumed AI without report documentation. |

### Confusion Pairs per Field (Coder A vs Coder B)

#### `relevance`
- `on_topic` vs `on_topic`: 16 pairs (100.0% agreement)

#### `narrative` (8 disagreements / 50.0% agreement)
- `individual_targeting` vs `individual_targeting`: 4 pairs (AGREE)
- `individual_targeting` vs `crowd_legitimacy`: 4 pairs (**DISAGREE**: Coder A coded individual targeting for VIP visitors / student gaffes; Coder B coded crowd legitimacy)
- `slogans_communal_loyalty` vs `slogans_communal_loyalty`: 2 pairs (AGREE)
- `individual_targeting` vs `other`: 1 pair (**DISAGREE**: CM Vijay visit in R0001)
- `protester_violence` vs `protester_violence`: 1 pair (AGREE)
- `protester_violence` vs `crowd_legitimacy`: 1 pair (**DISAGREE**: Shoe hurled at policeman in R0067)
- `other` vs `individual_targeting`: 1 pair (**DISAGREE**: BJP politician deepfake threats in R0018)
- `police_force` vs `police_force`: 1 pair (AGREE)
- `other` vs `protester_violence`: 1 pair (**DISAGREE**: Multi-clip compilation in R0009)

#### `content_form` (4 disagreements / 75.0% agreement)
- `old_or_out_of_context` vs `old_or_out_of_context`: 10 pairs (AGREE)
- `cropped_or_edited` vs `ai_altered`: 1 pair (**DISAGREE**: Liquify/warp image edit in R0042)
- `fabricated_text` vs `fabricated_text`: 1 pair (AGREE)
- `ai_generated` vs `ai_generated`: 1 pair (AGREE)
- `ai_altered` vs `ai_generated`: 1 pair (**DISAGREE**: Deepfake voice cloning over real speech in R0018)
- `old_or_out_of_context` vs `fabricated_text`: 1 pair (**DISAGREE**: 2007 Roadies clip in R0052)
- `not_established` vs `fabricated_text`: 1 pair (**DISAGREE**: Unverified deportation rumor in R0051)

#### `direction` (2 disagreements / 87.5% agreement)
- `supports_police_government` vs `supports_police_government`: 9 pairs (AGREE)
- `supports_protesters` vs `supports_protesters`: 5 pairs (AGREE)
- `supports_protesters` vs `supports_police_government`: 1 pair (**DISAGREE**: Modi-Dipke AI handshake in R0054)
- `mixed` vs `supports_police_government`: 1 pair (**DISAGREE**: Multi-clip compilation in R0009)

#### `origin` (1 disagreement / 93.8% agreement)
- `documented_non_ai` vs `documented_non_ai`: 13 pairs (AGREE)
- `documented_ai` vs `documented_ai`: 2 pairs (AGREE)
- `documented_non_ai` vs `documented_ai`: 1 pair (**DISAGREE**: Coder B guessed AI on warped photo in R0042)

---

## 3. Census of All 15 Disagreeing Cells

Every source report at `review_url` was fetched, opened, and read prior to scoring.

| Record ID | Field | Coder A Value (Score) | Coder B Value (Score) | Evaluator Gold | Disagreement Cause | One-Line Evaluation Rationale |
|---|---|---|---|---|---|---|
| **`R0042`** | `content_form` | `cropped_or_edited` (2) | `ai_altered` (0) | `cropped_or_edited` | `coder_misread_report` | Coder B scored 0: Report proves image is warped/stretched using photo editing; gives no evidence of generative AI modification. |
| **`R0042`** | `origin` | `documented_non_ai` (2) | `documented_ai` (0) | `documented_non_ai` | `coder_misread_report` | Coder B scored 0: Violated Principle 6 by guessing AI origin without documentary or forensic evidence in report. |
| **`R0001`** | `narrative` | `individual_targeting` (0) | `other` (1) | `crowd_legitimacy` | `codebook_missing_rule` | Coder A scored 0: Claim asserts high-profile political solidarity, not personal attacks; Coder B scored 1: Avoided individual_targeting but missed crowd_legitimacy due to missing VIP rule. |
| **`R0070`** | `narrative` | `individual_targeting` (0) | `crowd_legitimacy` (2) | `crowd_legitimacy` | `codebook_vague` | Coder A scored 0: Naming a prominent visitor does not constitute personal character targeting or smear. |
| **`R0076`** | `narrative` | `individual_targeting` (0) | `crowd_legitimacy` (2) | `crowd_legitimacy` | `codebook_vague` | Coder A scored 0: Claim asserts a political leader visit endorsing protest, not an attack on the leader's private conduct. |
| **`R0016`** | `narrative` | `individual_targeting` (1) | `crowd_legitimacy` (2) | `crowd_legitimacy` | `codebook_vague` | Coder A scored 1: Student is an unnamed participant used to disparage the broader crowd's competence; Rule T3 specifies named leaders for individual_targeting. |
| **`R0054`** | `direction` | `supports_protesters` (1) | `supports_police_government` (1) | `unclear` | `genuinely_ambiguous_claim` | Both coders scored 1: Direction of an AI image showing Modi with Dipke is legitimately ambiguous (can imply government endorsement or smear CJP as ruling-party plant); direction rule prescribes unclear/mixed. |
| **`R0067`** | `narrative` | `protester_violence` (2) | `crowd_legitimacy` (0) | `protester_violence` | `coder_misread_report` | Coder B scored 0: Physical assault on police officer with a shoe is overt violence, which Rule T1 strictly assigns to protester_violence over crowd_legitimacy. |
| **`R0018`** | `narrative` | `other` (2) | `individual_targeting` (1) | `other` | `codebook_vague` | Coder B scored 1: Individual_targeting applies to protest figures/organizers, whereas inflammatory speeches by external politicians belong in other. |
| **`R0018`** | `content_form` | `ai_altered` (2) | `ai_generated` (1) | `ai_altered` | `codebook_vague` | Coder B scored 1: Authentic video footage modified with cloned AI voice is ai_altered, not synthesized from scratch (ai_generated). |
| **`R0052`** | `content_form` | `old_or_out_of_context` (2) | `fabricated_text` (0) | `old_or_out_of_context` | `coder_misread_report` | Coder B scored 0: Claim is anchored by authentic 2007 MTV Roadies video footage, making it old_or_out_of_context, not fabricated_text. |
| **`R0009`** | `narrative` | `other` (1) | `protester_violence` (2) | `protester_violence` | `codebook_missing_rule` | Coder A scored 1: Retreated to other due to conflicting compilation clips; Rule T1 prioritizes protester violence depicted in two of the three clips. |
| **`R0009`** | `direction` | `mixed` (2) | `supports_police_government` (1) | `mixed` | `codebook_missing_rule` | Coder B scored 1: Overlooked that the compilation also contained police brutality footage which helps protesters; mixed is the accurate direction. |
| **`R0074`** | `narrative` | `individual_targeting` (1) | `crowd_legitimacy` (2) | `crowd_legitimacy` | `codebook_vague` | Coder A scored 1: Unnamed student gaffe used to disparage the broader protest crowd; Rule T3 specifies named leaders for individual_targeting. |
| **`R0051`** | `content_form` | `not_established` (0) | `fabricated_text` (2) | `fabricated_text` | `codebook_vague` | Coder A scored 0: Not_established is reserved for inconclusive forensic analysis of media; an unsubstantiated text rumor is fabricated_text. |

---

## 4. Disagreement Cause Taxonomy & Counts

| Cause Code | Description | Narrative | Content Form | Direction | Origin | Total Counts |
|---|---|---|---|---|---|---|
| `codebook_vague` | Existing codebook definition did not sufficiently distinguish boundary cases | 5 | 2 | 0 | 0 | **7** |
| `coder_misread_report` | Coder overlooked explicit documentary findings or applied forbidden inference | 1 | 2 | 0 | 1 | **4** |
| `codebook_missing_rule` | Codebook lacked an explicit rule for a recurring phenomenon (VIP visits, compilations) | 2 | 0 | 1 | 0 | **3** |
| `genuinely_ambiguous_claim` | Media payload has inherently dual or irreducibly ambiguous partisan valences | 0 | 0 | 1 | 0 | **1** |
| `link_dead_or_unreadable` | URL dead, blocked, or paywalled | 0 | 0 | 0 | 0 | **0** |
| `relevance_boundary` | Ambiguity regarding whether event pertained to Jantar Mantar NEET protests | 0 | 0 | 0 | 0 | **0** |
| `other` | Any other cause | 0 | 0 | 0 | 0 | **0** |
| **TOTAL** | | **8** | **4** | **2** | **1** | **15** |

---

## 5. Inconsistency & Link Provenance Findings

1. **Dead Links**: **0 dead links**. All 12 distinct review URLs returned HTTP 200 OK with full fact-check text.
2. **Cross-Field Logic Inconsistencies**: **0 inconsistencies**. Neither coder entered contradictory combinations (such as `ai_generated` paired with `documented_non_ai`, or `old_or_out_of_context` with `documented_ai`).
3. **Coder Notes**: Neither coder entered comments in the optional `coder_notes` column.

---

## 6. What a 16-Row Pilot Cannot Show

1. **Rare Class Performance & Zero-Variance Degradation**:
   - `relevance`: 100% of pilot rows were `on_topic` ($16/16$). The pilot provided zero observations of `off_topic` or `unsure` claims, leaving the practical usability of the Relevance Gate untested on human coders.
   - `content_form`: Zero observations of `genuine_wrongly_called_fake` or `disputed`.
   - `origin`: Zero observations of `disputed` or `unknown`.
2. **Statistical Margin of Error**: With $n=16$, Cohen's kappa 95% confidence intervals exceed $\pm 0.40$. The numbers must be interpreted as qualitative diagnostic signals rather than precise statistical estimates.
3. **Linguistic Diversity**: Only 2 of the 16 records were in Devanagari script (`R0070` and `R0067`), leaving Hindi-specific framing ambiguities largely unobserved.
