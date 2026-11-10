# QA Review: Narrative Mapping Audit (Native Labels to Scheme P)

**Audit Type:** Native-to-Proposal Mapping Verification (`mapping_audit`)  
**Standard:** Section 3 Qualitative Review Standard  
**Seed:** 42  
**Population Size:** 97 records (91 category-level, 6 row-level)  
**Sample Size:** 21 records (6 row-level records [100% census] + 15 sampled category-level records)  
**Blind Packet File:** `qa/blind_mapping_audit.csv`  
**Key File:** `qa/key_mapping_audit.csv`  

---

### 1. Audit Overview & Methodology
For every audited record, the source fact-check report was read **before** evaluating the native label and proposed proposal code. Each record was scored:
- **2 (Fully Supported):** The mapped code directly and accurately reflects the claim and fact-check evidence per `CODEBOOK.md` v1.3.
- **1 (Minor Tension / Ambiguity):** The mapped code is justifiable under codebook guidelines but involves underlying source access barriers (e.g. HTTP 403 on syndicated AFP pages) or recap multi-claim bundling.
- **0 (Incorrect Mapping):** The mapped code contradicts the report or codebook rules.

---

### 2. Audit Scores Summary
- **Score 2 (Fully Supported):** 18 / 21 (85.7%)
- **Score 1 (Minor Tension):** 3 / 21 (14.3%)
- **Score 0 (Incorrect):** 0 / 21 (0.0%)
- **Mean Score:** 1.86 / 2.00 (92.9%)

---

### 3. Failure Taxonomy & Items Scored Below 2

| Packet ID | Record ID | Native Label | Proposed Code | Score | Failure Taxonomy Category | One-Line Reason |
|:---|:---:|:---|:---|:---:|:---|:---|
| `MAP_PKT_07` | `R0059` | `Fabricated document / statement` | `other` | 1 | `source_link_inaccessible_403` | Source fact-check URL returned HTTP 403 Forbidden; mapping to `other` is inferred from claim text asserting fabricated police/minister video statement per Section 3.6 administrative claim rule. |
| `MAP_PKT_11` | `R0058` | `Crowd size / legitimacy` | `crowd_legitimacy` | 1 | `source_link_inaccessible_403` | Source fact-check URL returned HTTP 403 Forbidden; mapping to `crowd_legitimacy` is inferred from claim metadata asserting protest turnout in June 2026. |
| `MAP_PKT_17` | `R0011` | `Communal / anti-national framing` | `slogans_communal_loyalty` | 1 | `recap_multi_claim_bundling` | Article is a weekly recap page bundling an unrelated Kerala narcotics raid alongside CJP debunks; claim has marginal thematic overlap with protest slogans. |

#### Taxonomy Breakdown:
1. **`source_link_inaccessible_403` (2 items):** Inaccessibility of AFP syndication URLs forces reliance on claim text and editorial metadata rather than complete forensic report text.
2. **`recap_multi_claim_bundling` (1 item):** Fact-checker recap articles that aggregate multiple distinct claims introduce ambiguity regarding which specific sub-claim was evaluated.

---

### 4. What This Sample Cannot Show
1. **Unsampled Category Rows:** While all 6 row-level overrides were audited (100% census), the 15 sampled category rows represent ~16.5% of the 91 category-level records. Rare edge cases in the remaining 76 rows may contain subtle multi-narrative cross-overs.
2. **Post-Merge Classification Behavior:** This audit evaluates the semantic mapping to the 6 proposal classes prior to the rare-class threshold merge (which merges classes with $< 8$ claims into `other`).
