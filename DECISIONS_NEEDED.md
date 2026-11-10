# Decisions on Native Label to Proposal Code Mapping

**Status:** LOCKED / APPROVED BY TEAM (with specific items noted for human confirmation)  
**Context:** The final human-labelled dataset (`data/raw/C_final.xlsx`) utilizes 13 team-native narrative labels rather than the proposal's 6 controlled narrative codes. The mapping from the 13 native categories to Scheme P (proposal-aligned) has been locked according to team decisions.

---

### Summary of Team Mapping Decisions

| # | Native Label | Scheme P Code | Level | Affected Records | Team Decision Status | Notes & Human Follow-up |
|---|:---|:---|:---:|:---:|:---:|:---|
| **1** | `Delegitimizing / mockery` | `crowd_legitimacy` | Row-level | `R0016`, `R0074`, `R0080`, `R0086` (4 rows) | **APPROVED by team** | `R0016` & `R0074` depict student gaffes (Rule T3.2); `R0080` challenges authentic crowd size; `R0086` challenges crowd voluntariness. |
| **2** | `Fabricated document / statement` | `other` | Row-level | `R0027`, `R0059` (2 rows) | **APPROVED by team** (`R0027` approved; `R0059` provisional) | `R0027` is fake resignation letter (Section 3.6). `R0059` (AFP fact-check on minister/police video statement) is blocked by Akamai anti-bot protection; keep `other` unless a human reviews in browser and says otherwise. |
| **3** | `Moral / cultural smear` | `crowd_legitimacy` | Category | 8 rows | **APPROVED by team** | Anonymous protester conduct smears challenging collective demeanor (Rule T3.2). |
| **4** | `Fabricated casualties` | `police_force` | Category | 5 rows | **APPROVED by team** | Claims of manufactured student deaths/ICU injuries directly allege lethal state force (Section 3.1). |
| **5** | `Foreign / conspiracy link` | `slogans_communal_loyalty` | Category | 5 rows | **APPROVED by team** (with check) | `R0030` and `R0060` involve Jamaat-e-Islami support. Rows `R0046`, `R0051`, and `R0054` are mainly about named individuals (PM Modi, Abhijeet Dipke) and are flagged under "human to confirm". |
| **6** | `Pro-police counter-narrative` | `other` | Category | 4 rows | **APPROVED by team** | Civilian demonstrations and youth rallies supporting Delhi Police classify as `other` (Section 3.6). |
| **7** | `Political attack on govt/BJP` | `other` | Category | 4 rows | **APPROVED by team** | Political attacks/satire against ministers without alleging police brutality classify as `other`. |
| **8** | Rare-Class Merge Threshold | `other` / `other_merged` | Policy | Threshold = 8 claims | **APPROVED by team** | Kept as is. Scheme P's `other` (24 rows, 21 claims) is a mixed residual folding `protester_violence` (5 claims) and `individual_targeting` (6 claims) into it. |

---

### Remaining Items for Human Confirmation:
1. **`R0059` Browser Review:** Open the AFP Fact Check report (`https://factcheckhindi.afp.com/doc.afp.com.C3WW7ZQ`) in a standard browser to confirm whether `other` accurately reflects the claim.
2. **`Foreign / conspiracy link` Individual Smears:** Review rows `R0046` (PM Modi handshake), `R0051` (Dipke US deportation), and `R0054` (duplicate Modi-Dipke image) to decide if these 3 records should remain in `slogans_communal_loyalty` or move to `individual_targeting` (which folds into `other`).
3. **Coder Sheet Metadata:** Confirm unit of 20 conflicts (rows vs cells), fields involved, coder identities, and whether Coders A and B worked independently.
