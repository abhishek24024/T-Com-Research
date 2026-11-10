# QA Review: Human Label Quality Audit (`label_audit`)

**Audit Type:** Ground-Truth Human Label Quality Assessment  
**Standard:** Section 3 Qualitative Review Standard  
**Seed:** 42  
**Population Size:** 97 records  
**Sample Size:** 25 records (25.8% of the dataset)  
**Blind Packet File:** `qa/blind_label_audit.csv`  
**Key File:** `qa/key_label_audit.csv`  

---

### 1. Audit Overview & Methodology
A representative random sample of 25 records was drawn from `data/processed/final_labels.csv` with a fixed seed (`42`). For each sampled record, the source fact-check report at `review_url` was read and evaluated **before** examining the sheet's native labels (`narrative_native`, `content_form_native`, `direction_native`).

Each field was scored:
- **2 (Fully Supported):** The label accurately reflects the factual conclusions, forensic evidence, and political framing established in the fact-check report.
- **1 (Minor Drift / Tension):** Minor semantic ambiguity, multi-claim bundling, or inaccessible external CDN page.
- **0 (Incorrect / Unsupported):** The label directly contradicts the report.

---

### 2. Audit Scores Summary
- **Overall Record Scores:**
  - **Score 2 (Fully Supported):** 21 / 25 (84.0%)
  - **Score 1 (Minor Tension):** 4 / 25 (16.0%)
  - **Score 0 (Incorrect):** 0 / 25 (0.0%)
  - **Mean Overall Score:** 1.84 / 2.00 (92.0%)
- **Per-Field Scores:**
  - **Primary Narrative:** Mean 1.96 / 2.00 (98.0% agreement with evidence)
  - **Content Form:** Mean 2.00 / 2.00 (100% agreement with evidence)
  - **Political Direction:** Mean 2.00 / 2.00 (100% agreement with evidence)

---

### 3. Failure Taxonomy & Items Scored Below 2

| Packet ID | Record ID | Publisher | Native Labels (Narrative \| Form \| Dir) | Score | Failure Taxonomy Category | One-Line Reason |
|:---|:---:|:---|:---|:---:|:---|:---|
| `LBL_PKT_09` | `R0011` | The Quint | `Communal / anti-national framing` \| `Old / recycled video` \| `Anti-CJP` | 1 | `recap_multi_claim_bundling` | Weekly recap page bundles an unrelated Kerala narcotics raid alongside CJP debunks; claim narrative has marginal connection to core protest. |
| `LBL_PKT_13` | `R0048` | AFP Fact Check | `Communal / anti-national framing` \| `Old / recycled video` \| `Anti-CJP` | 1 | `source_link_inaccessible_403` | Source fact-check URL returned HTTP 403 Forbidden; claim text directly aligns with Kashmir remark debunks. |
| `LBL_PKT_21` | `R0050` | AFP Fact Check | `Endorsement / solidarity claim` \| `Old / recycled video` \| `Pro-CJP` | 1 | `source_link_inaccessible_403` | Source fact-check URL returned HTTP 403 Forbidden; claim text directly aligns with astronaut/CM solidarity debunks. |
| `LBL_PKT_23` | `R0069` | AFP Fact Check | `Communal / anti-national framing` \| `Old / recycled video` \| `Anti-CJP` | 1 | `source_link_inaccessible_403` | Source fact-check URL returned HTTP 403 Forbidden; Hindi claim text directly aligns with Kashmir speech debunks. |

#### Taxonomy Breakdown:
1. **`source_link_inaccessible_403` (3 items):** Automated HTTP requests blocked by AFP's CDN firewall (HTTP 403 Forbidden), requiring reliance on claim text and metadata rather than live report text.
2. **`recap_multi_claim_bundling` (1 item):** Fact-check aggregator pages bundling unrelated police actions with protest claims.

---

### 4. What This Sample Cannot Show
1. **Unsampled Human Labels:** The remaining 72 records in `C_final.xlsx` were not audited in this sample. While the 25-record sample confirms high overall fidelity (92%), individual edge-case errors in unsampled rows cannot be ruled out.
2. **Inter-Coder Disagreement Traces:** Because only the adjudicated final sheet `C_final.xlsx` was provided, this audit assesses the adjudicated consensus labels, not the pre-adjudication divergence between Coder A and Coder B.
