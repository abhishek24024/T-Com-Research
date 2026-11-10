# Pilot Coding Debrief & Rule Guidance for Coders

**To:** Coder A and Coder B  
**From:** Research Team  
**Subject:** Pilot Inter-Coder Reliability Debrief & Clarified Coding Guidelines  
**Status:** Mandatory Reference for Full Coding Sheet Labelling

---

Thank you for completing the pilot coding sheet. Your independent coding surfaced key areas where our codebook rules were ambiguous or frequently misapplied. 

Please review the following clarified decision rules before beginning the full coding sheet. **These rules take precedence.**

---

### 1. VIP & Politician Visits Belong to `crowd_legitimacy`
- **Rule**: Claims asserting that an external politician, public figure, minister, or celebrity visited Jantar Mantar to endorse, attend, or show solidarity with the protest belong strictly to **`crowd_legitimacy`** (under the existing rule: *celebrity/VIP participation or endorsements*).
- **Do NOT code as `individual_targeting`**: `individual_targeting` is reserved strictly for claims alleging personal misconduct, financial corruption, hypocrisy, or private immorality against named protest leaders (e.g., Abhijeet Dipke) or public officials. Simply naming a visiting leader does not make it individual targeting.
- **Do NOT code as `other`**.

### 2. Physical Violence Takes Priority (Rule T1)
- If a claim asserts an overt act of physical confrontation, bodily injury, weapon deployment, or direct physical assault (e.g., hitting a police officer, stone pelting, or setting vehicles on fire), classify as **`protester_violence`** (or **`police_force`** if by police).
- Do not dilute physical violence claims into `crowd_legitimacy` or `other`.

### 3. "Edited" Does NOT Mean "AI" (Media Provenance & Hedging)
- **Do NOT guess AI origin from visual appearance**:
  - Digital image warping, photo stretching (e.g., liquefying an authentic photo to make someone look overweight), manual photo manipulation, or video splicing must be coded as **`content_form = cropped_or_edited`** and **`origin = documented_non_ai`**.
  - Only code `ai_altered` or `ai_generated` when the fact-check report **explicitly states documentary or forensic evidence of generative AI models**.
- **Hedging in Reports**: If a fact-checker hedges (*"appears to be"*, *"likely"*, *"suspected"*) or relies solely on an automated detector score without forensic confirmation:
  - Code **`content_form = not_established`**
  - Code **`origin = unknown`**
  - Add the note `hedged` in `coder_notes`.
- **Generic 'Edited' Claims**: If a report states only that media is "edited" or "doctored" with no method named, code **`origin = unknown`**.

### 4. Deepfake Voice Cloning vs Full AI Synthesis
- Cloned AI audio or synthetic lip-sync overlaid onto authentic, pre-existing video of a real person is **`ai_altered`**.
- **`ai_generated`** is strictly reserved for media synthesized entirely from scratch (text-to-image or text-to-video).

### 5. Fabricated Text Rumors
- Viral social media text claims or rumors fabricated without any genuine media attachment are **`fabricated_text`**.
- Do not code manufactured text rumors as `not_established` (which is reserved for inconclusive forensic tests on physical media).

### 6. Multi-Clip Compilation Debunks
- When a viral post bundles multiple old video clips:
  - **Narrative**: Apply Rule T1 (overt protester violence takes precedence if depicted; do not retreat to `other`).
  - **Direction**: If the compilation depicts contradictory actions (e.g., one clip shows police brutality while another shows protester arson), classify direction as **`mixed`**.

### 7. Field Completion Rule for Blanks
- If you code **`relevance = off_topic`**, leave `narrative`, `content_form`, `direction`, and `origin` **completely BLANK**.
- If you code **`relevance = unsure`**, you **MUST fill all four fields** (`narrative`, `content_form`, `direction`, and `origin`) as if the claim were on-topic. Enter any reasoning or notes in `coder_notes`.

### 8. Anonymous Protesters' Gaffes & Demeanor (`crowd_legitimacy`)
- Viral claims depicting unnamed, anonymous protest participants making embarrassing factual gaffes on camera, acting bizarrely, or partying/dancing during demonstrations belong strictly to **`crowd_legitimacy`** (discrediting the competence, seriousness, or demeanor of the protest crowd).
- Do NOT code as `individual_targeting` (strictly reserved for named organizers/leaders) and do NOT code as `other`.
