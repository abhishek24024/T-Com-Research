# Pilot Study Changelog & Codebook v1.3 Rationale (Internal)

> [!NOTE]
> This document is strictly for internal research team governance and audit documentation.
> It cites records from `data/processed/pilot_sample.csv` to explain the empirical rationale for each codebook amendment.
> **This document must NEVER be shared with coders during ongoing labelling rounds.**

---

## 1. Summary of Pilot Diagnostics ($n=16$)

An inter-coder reliability pilot was conducted on 16 sampled records between Coder A and Coder B under `CODEBOOK.md` v1.2:
- `relevance`: 100.0% agreement (Kappa 1.000 / single-class degenerate marginals).
- `origin`: 93.8% agreement (Kappa 0.765).
- `direction`: 87.5% agreement (Kappa 0.748).
- `content_form`: 75.0% agreement (Kappa 0.543).
- `narrative`: 50.0% agreement (Kappa 0.360) — primary area of divergence.

Census of Disagreements: 15 disagreeing cells across 12 distinct records.

---

## 2. Detailed Cause Analysis & Record Citations

### A. VIP & Politician Visits to Jantar Mantar
- **Pilot Records Involved**: `R0001` (TN CM Vijay visit), `R0070` (Maneka Gandhi visit), `R0076` (CM Vijay visit).
- **Causes**: `codebook_missing_rule` (R0001), `codebook_vague` (R0070, R0076).
- **Divergence**: Coder A repeatedly classified claims asserting that a named politician/VIP visited Jantar Mantar as `individual_targeting` simply because a specific public figure was named. Coder B classified them as `crowd_legitimacy` or `other`.
- **Resolution in v1.3**:
  - Clarified in Rule T3.1 that claims asserting external political/celebrity attendance, endorsement, or solidarity belong to `crowd_legitimacy` (which already listed *'celebrity/VIP participation, or endorsements supporting the protest'*).
  - Coder-facing examples in v1.3 use verified non-pilot records: `R0003` (Sunita Williams) and `R0040` (Maneka Gandhi).
  - `individual_targeting` is strictly reserved for attacks on named leaders' personal conduct, private morality, or finances.

### B. Anonymous Protesters' Conduct & Gaffes
- **Pilot Records Involved**: `R0016`, `R0074` (schoolgirl gaffe regarding Israel-America war).
- **Cause**: `codebook_vague`.
- **Divergence**: Coder A coded `individual_targeting` because the video focused on a single person. Coder B coded `crowd_legitimacy` because the gaffe was used to challenge the crowd's seriousness.
- **Resolution in v1.3 (Rule T3.2)**:
  - Explicitly marked as **`[TEAM DECISION NEEDED]`** with two formal options: Option 1 (`crowd_legitimacy`) vs Option 2 (`other`).
  - Coders are instructed not to code these as `individual_targeting` (reserved for named organizers).

### C. Photo Manipulation vs Generative AI & Hedging Rules
- **Pilot Record Involved**: `R0042` (warped photo of Abhijeet Dipke midsection).
- **Cause**: `coder_misread_report`.
- **Divergence**: Coder B coded `ai_altered` and `documented_ai`. The fact-check report explicitly proved digital image warping/stretching of a real photo, with zero evidence of AI generation.
- **Resolution in v1.3 (Rule 6.1)**:
  - If a report hedges ("appears", "likely") or cites only automated detector scores: `content_form = not_established`, `origin = unknown`, note `hedged`.
  - If a report says only "edited/doctored" without tools: `origin = unknown`.
  - `origin = documented_non_ai` requires non-generative methods (e.g. liquefy, warping, splicing) or genuine old footage.

### D. Multi-Clip Compilations
- **Pilot Record Involved**: `R0009` (compilation bundling police action, burning car, and barricade breach).
- **Cause**: `codebook_missing_rule`.
- **Divergence**: Coder A retreated to `narrative = other` and `direction = mixed`. Coder B selected `narrative = protester_violence` and `direction = supports_police_government`.
- **Resolution in v1.3 (Rule T5)**:
  - Narrative: Apply Rule T1 (overt protester violence takes priority over police action unless police action dominates); do not retreat to `other`.
  - Direction: If clips depict opposing sides, classify direction as `mixed`.

### E. AI Voice Cloning on Real Video
- **Pilot Record Involved**: `R0018` (deepfake voice cloning of BJP MP speech).
- **Cause**: `codebook_vague`.
- **Divergence**: Coder B selected `ai_generated`.
- **Resolution in v1.3 (Rule T6)**:
  - Cloned AI audio overlaid onto real, pre-existing footage is `ai_altered`. `ai_generated` requires full synthesis from scratch.

### F. Manufactured Text Rumors vs Not Established
- **Pilot Record Involved**: `R0051` (unsubstantiated rumor claiming Dipke facing US deportation).
- **Cause**: `codebook_vague`.
- **Divergence**: Coder A selected `not_established`.
- **Resolution in v1.3 (Rule T7)**:
  - Unsubstantiated text claims with zero evidence or media are `fabricated_text`. `not_established` is reserved for inconclusive forensic analysis of physical media.

### G. Ambiguous Political Imagery Direction
- **Pilot Record Involved**: `R0054` (AI image of Modi shaking hands with Dipke).
- **Cause**: `genuinely_ambiguous_claim`.
- **Divergence**: Coder A coded `supports_protesters`; Coder B coded `supports_police_government`.
- **Resolution in v1.3 (Rule T8)**:
  - Imagery with dual partisan valence is `unclear` (or `mixed`) unless accompanying text establishes a one-sided framing.

### H. Off-Topic and Unsure Blank-Cell Rule
- **Pilot Finding**: In pilot coding, coders entered values across all fields even when relevance might be questionable.
- **Resolution in v1.3 (Rule 2.1)**:
  - When `relevance` is `off_topic` or `unsure`, the other four fields MUST be left blank.
