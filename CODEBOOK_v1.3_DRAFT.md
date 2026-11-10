# CODEBOOK: Claim-Narrative Triage Pipeline
**STATUS: v1.3 approved by team**  
**Version:** 1.3 (Audited Real Records, Clarified Hedging & Standardized Adjudication Rules)
**Date:** November 2026  
**Context:** Fact-checked claims concerning the June–July 2026 Jantar Mantar student protests (Cockroach Janta Party / CJP-led NEET examination agitation).

---

## 1. Core Coding Principles & Decision Rules

1. **Unit of Analysis:**  
   Each row in `coding_sheet.csv` represents a single fact-checked claim record (`record_id`). Coders evaluate the claim based on the documentary evidence reported in the corresponding fact-check article (`review_url`).

2. **Relevance Gate (Exclusion, Not "other"):**  
   Coders first determine whether the record is `on_topic`, `off_topic`, or `unsure`.  
   > [!IMPORTANT]  
   > If a record is judged `off_topic`, it is **completely excluded** from `dataset.csv` during `finalize` and written to `outputs/excluded_off_topic.csv`. Off-topic claims must **NEVER** be coded under the narrative category `other`.

   > [Rule 2.1 - Off-Topic and Unsure Blank-Cell Rule]:  
   > When a record is coded as `off_topic` or `unsure`, coders MUST leave `narrative`, `content_form`, `direction`, and `origin` strictly BLANK (entering notes only in `coder_notes`). This prevents forcing protest-specific categories onto non-protest claims and aligns with automated exclusion in `finalize`.

3. **One Primary Narrative per Record:**  
   Every on-topic record must be assigned exactly **ONE primary narrative** code. The primary narrative reflects **what the claim asserts happened** (the core assertion of fact or event), NOT whether the claim is true or false, and NOT who debunked it.

4. **Exclusivity of "other":**  
   Assign `other` **only** if the claim is on-topic but does not fit into any of the five defined substantive narrative categories. It must not be used as a convenient escape for ambiguous or complex claims.

5. **Tie-Break Hierarchy:**  
   When a claim embodies multiple narrative elements (e.g., an allegation combining communal slurs and physical violence, or high-profile visitor presence combined with crowd estimates), apply the following hierarchical tie-break rules:
   - **Rule T1 (Physical Violence over Ideological Framing):** If a claim asserts an overt act of physical confrontation, bodily injury, homicide, or weapon deployment, classify as `protester_violence` (if attributed to protesters) or `police_force` (if attributed to police), even if communal or religious identities are mentioned (e.g., `R0025`).
   - **Rule T2 (Specific State Brutality over Crowd Presence):** If a visual depicts police lathi-charge or brutality against individuals at a rally, classify as `police_force`, not `crowd_legitimacy`.
   - **Rule T3 (Named Organizer Conduct vs Collective Crowd):** If a claim specifically targets the personal conduct, private morality, financial status, or personal background of a named individual protest organizer or public official (e.g., Abhijeet Dipke), classify as `individual_targeting`, even if the event occurred at the protest site. If the claim concerns anonymous protesters exhibiting collective behavior (e.g., dancing, kissing, crowd density), classify as `crowd_legitimacy` (e.g., `R0041`).
   - **Rule T4 (Verbal Slogans & Foreign Backing):** Allegations of anti-national chants, religious slogans, or foreign extremist endorsements without direct physical assaults classify as `slogans_communal_loyalty`.
   - **Rule T3.1 (VIP & Politician Visits - Reminder of Existing Crowd Legitimacy Inclusion):** As defined in Section 3.4 (`crowd_legitimacy`: *'celebrity/VIP participation, or endorsements supporting the protest'*), claims asserting that an external politician, public figure, minister, or celebrity visited Jantar Mantar to endorse, attend, or show solidarity with the protest belong strictly to `crowd_legitimacy`. Coders must NOT classify these as `individual_targeting` (which is reserved for personal character smears) and must NOT classify them as `other`. *(Real Non-Pilot Verified Examples: `R0003` - Alt News report on claim that astronaut Sunita Williams visited Jantar Mantar to support CJP; `R0040` - Factly report on claim that BJP leader Maneka Gandhi visited Jantar Mantar in support of the protest)*.
   - **Rule T3.2 (Unnamed Protest Participants' Gaffes & Demeanor):** When a viral claim depicts an anonymous, unnamed protest participant making an embarrassing factual gaffe on camera about what the protest is about, acting bizarrely, or partying/dancing during a demonstration, classify as `crowd_legitimacy` (discrediting the collective competence, authenticity, seriousness, or demeanor of the protest crowd). Coders must NOT classify these as `individual_targeting` (which strictly requires named leaders/organizers like Abhijeet Dipke) and must NOT classify them as `other`. *(Real Non-Pilot Verified Example: `R0094` - Alt News report debunking viral videos of youths dancing to 'Character Dheela Hai' claimed to be CJP protesters treating solemn student protests as a party celebration; classified as `crowd_legitimacy`).*
   - **Rule T5 (Multi-Clip Compilation Debunks):** When a fact-check article debunks a compilation bundling multiple distinct video clips depicting different events:  
     a) **Narrative**: If the compilation depicts both police brutality and protester physical violence, apply Rule T1 (protester violence takes precedence if overt arson/attacks are shown). Coders should not retreat to `other` simply because multiple clips are present.  
     b) **Direction**: If the bundled clips depict conflicting political valences (e.g., one clip helps protesters by showing police brutality, while another hurts protesters by showing arson), coders must classify direction as `mixed`, rather than picking a single one-sided direction.
   - **Rule T6 (Deepfake Voice Cloning vs Full AI Synthesis):** When authentic, pre-existing video footage of a real person is modified using AI voice cloning, deepfake audio, or synthetic lip-sync, classify as `ai_altered`, NOT `ai_generated`. `ai_generated` is strictly reserved for media entirely synthesized from scratch (e.g., text-to-image or text-to-video generation).
   - **Rule T7 (Fabricated Text Rumors vs Not Established):** Purely manufactured text rumors, viral social media claims, or fake claims with zero evidence or genuine media must be classified as `fabricated_text`. `not_established` is strictly reserved for cases where physical media (image/audio/video) exists but forensic tools failed to reach a definitive conclusion.
   - **Rule T8 (Direction for Ambiguous Political Imagery):** When an image carries irreducibly dual or ambiguous political meanings depending on the viewer's partisan lens (e.g., an image of a government leader posing with a protest organizer without explicit praise or condemnation), coders must classify direction as `unclear` (or `mixed`) unless the accompanying text caption explicitly establishes a one-sided framing.

6. **Documentary Evidence Only (No AI Speculation):**  
   Origin labels (`origin`) are recorded **only if the fact-check report explicitly provides documentary or forensic evidence**. Coders must never guess that text or media is AI-generated based on its appearance, smoothness, tone, or automated detector scores.

   > [Rule 6.1 - Media Provenance & Hedging Rules]:  
   > 1. **Hedging & Detector Scores**: If a fact-check report hedges ("appears to be", "likely", "possible") or relies solely on an automated detector score without conclusive forensic proof, coders must classify `content_form = not_established`, `origin = unknown`, and add the note `hedged` in `coder_notes`.
   > 2. **Generic 'Edited/Doctored' Language**: If a report states only that an image or video is "edited", "manipulated", or "doctored" without specifying the software, method, or tools, classify `origin = unknown` (do not speculate that it is AI or non-AI).
   > 3. **Documented Non-AI Criteria**: `origin = documented_non_ai` is assigned ONLY when the report explicitly states a non-generative digital method (e.g., Photoshop liquefy, manual warping, image splicing, cropping) or confirms genuine footage from an older or different event.

---

## 2. Topic Relevance Codes (`relevance`)

Coders first assess whether the claim specifically pertains to the 2026 Jantar Mantar NEET protests.

### 2.1 `on_topic`
- **Definition:** The claim directly concerns the June–July 2026 Jantar Mantar student agitation led by the Cockroach Janta Party (CJP) over the NEET examination, including actions of student protesters, Delhi Police, organizers, political visitors to Jantar Mantar, or immediate policy fallout.
- **Real Example 1:** `R0008` — "Video shows Delhi Police vandalsing vehicles during CJP protest"
- **Real Example 2:** `R0087` — "AI-generated image showing deceased student after police lathicharge at Jantar Mantar"

### 2.2 `off_topic`
- **Definition:** The claim is entirely unrelated to the 2026 Jantar Mantar NEET protests. This includes fact-checks matching search terms that concern separate protests in different cities/dates, unrelated personal controversies, or general political news.
- **Handling:** **Off-topic rows are completely EXCLUDED from the modeling dataset (`dataset.csv`) during `finalize` and archived in `outputs/excluded_off_topic.csv`. They are NOT labelled as the narrative class "other".**
- **Real Example 1:** `R0011` — "WebQoof Recap: Of Claims Surrounding PM Modi and CJP Protest" *(Multi-claim weekly recap article bundling an unrelated Kerala narcotics seizure with protest debunks; coders evaluating the narcotics sub-claim code it as `off_topic`).*
- **Real Example 2:** *no clear example among the audited codebook examples; coders may encounter this code in the other records.*

### 2.3 `unsure`
- **Definition:** Borderline cases where the report leaves the exact connection to the Jantar Mantar protest ambiguous, requiring third-coder adjudication.

---

### 2.4 Field Completion Rule for Blanks
- **`relevance = off_topic`**: Coders leave the other four fields (`narrative`, `content_form`, `direction`, `origin`) completely blank. Off-topic rows are excluded from the dataset during finalization.
- **`relevance = unsure`**: Coders MUST fill all four fields (`narrative`, `content_form`, `direction`, `origin`) as if the claim were on-topic. If adjudication subsequently confirms the claim is on-topic, the coder's substantive labels are preserved.

---

## 3. Narrative Codes (`narrative`)

### 3.1 `police_force`
- **Definition:** Claims asserting that police or state security forces engaged in excessive, unlawful, brutal, or lethal physical violence, unprovoked lathi-charge, tear gas deployment, property destruction, or abusive detention against student protesters.
- **Inclusions:** Police baton charges, student deaths/hospitalizations from police action, smashing vehicles, dragging female protesters, home arrests post-protest.
- **Exclusions:** Protests *against* police without alleging specific physical force; claims asserting that civilians assaulted police (see `protester_violence`); pro-police rallies (see `other`).
- **Real Example 1:** `R0087` — "AI-generated image showing deceased student after police lathicharge at Jantar Mantar"
- **Real Example 2:** `R0023` — "Visuals of police officers assaulting female protesters during the CJP protest at Jantar Mantar"
- **Tricky Counter-Example:** `R0012` — "This video shows people supporting the Delhi Police amid the CJP-led protests." *(Classified as `other`: depicts civilian counter-demonstrations supporting police; no assertion of police force or violence against protesters).*

### 3.2 `protester_violence`
- **Definition:** Claims asserting that student demonstrators or CJP cadres engaged in unlawful physical violence, riots, arson, assaulting police personnel, stone pelting, or damaging public infrastructure (e.g., trains, government vehicles).
- **Inclusions:** Physical assault on police officers (e.g., killing of Head Constable), stone pelting at railway trains, attempting to burn vehicles, wielding offensive weapons.
- **Exclusions:** Peaceful sit-ins, shouting provocative slogans (see `slogans_communal_loyalty`), non-violent civil disobedience, verbal confrontations with journalists.
- **Real Example 1:** `R0031` — "Video shows CJP protesters attacking India's first hydrogen-powered train in Delhi."
- **Real Example 2:** `R0061` — "20 जुलाई को CJP के 'संसद मार्च' के दौरान प्रदर्शनकारियों के हमले में दिल्ली पुलिस के हेड कांस्टेबल अमित की मौत हो गई." *(Claim that Delhi Police Head Constable Amit was killed in attack by CJP protesters).*
- **Tricky Counter-Example:** `R0007` — "CJP protesters raised Islamic slogans at Jantar Mantar." *(Classified as `slogans_communal_loyalty`: asserts religious/ideological chanting, not physical assault or destruction of property).*

### 3.3 `slogans_communal_loyalty`
- **Definition:** Claims asserting that the protest movement is motivated by, infiltrated by, or expressing solidarity with communal, anti-national, religious extremist, or hostile foreign groups (e.g., raising Islamic/pro-Pakistan slogans, waving foreign flags, backed by foreign Islamist parties).
- **Inclusions:** Allegations of chanting "Allahu Akbar" or pro-separatist slogans, alleged endorsements by Bangladesh Jamaat-e-Islami, claims of communal conspiracies behind NEET agitation.
- **Exclusions:** Secular political slogans against ministers; physical communal clashes involving arson or homicide (see Rule T1 -> `protester_violence`).
- **Real Example 1:** `R0007` — "CJP protesters raised Islamic slogans at Jantar Mantar."
- **Real Example 2:** `R0010` — "The video shows Arundhati Roy speaking about Kashmir at the CJP's protest." *(Archival Kashmir speech falsely shared as CJP protest speech; directly questions national loyalty).*
- **Real Example 3:** `R0030` — "Fact check: Bangladesh Jamaat-e-Islami has not backed CJP protest, viral letter is fake"
- **Tricky Counter-Example:** `R0025` — "The video shows a Muslim man attempting to set a car on fire during the CJP protest at Jantar Mantar, Delhi." *(Classified as `protester_violence`: although framed around religious identity, Rule T1 mandates that physical violence/arson resolves to `protester_violence`, not `slogans_communal_loyalty`).*

### 3.4 `crowd_legitimacy`
- **Definition:** Claims intended to amplify or delegitimize the scale, popular mandate, moral character, or composition of the protest crowd at large. Includes claims of massive turnouts, attendance by famous astronauts/politicians/celebrities, or conversely, allegations of public indecency, moral depravity, or paid attendance.
- **Inclusions:** Exaggerated drone crowd shots; visits/endorsements by national celebrities (Sunita Williams, CM Vijay); viral claims of public kissing, dancing, or partying at the solemn protest site.
- **Exclusions:** Targeted smears against a named leader's private personal life (see `individual_targeting`); specific acts of rioting/arson (see `protester_violence`).
- **Real Example 1:** `R0002` — "Video shows astronaut Sunita Williams joining the CJP Protest."
- **Real Example 2:** `R0014` — "Visuals show crowd at Cockroach Janta Party's protest at Jantar Mantar in Delhi"
- **Real Example 3:** `R0041` — "A video shows protesters kissing during a protest by the Cockroach Janta Party (CJP) at Delhi's Jantar Mantar."
- **Tricky Counter-Example:** `R0036` — "The video shows a four-year-old personal video of Abhijeet Dipke, the founder of the Cockroach Janata Party, kissing a young woman." *(Classified as `individual_targeting`: although alleging moral depravity/kissing, Rule T3 mandates that allegations targeting a named founder's private personal life resolve to `individual_targeting`, not `crowd_legitimacy`).*

### 3.5 `individual_targeting`
- **Definition:** Claims focusing directly on the personal integrity, private life, character, physical appearance, financial corruption, or past history of named individual leaders, organizers, or key political figures involved in the protest (most prominently CJP founder Abhijeet Dipke).
- **Inclusions:** Leaked private romantic videos of named organizers, mockery of weight gain/loss during hunger strikes, fake past audition clips (Roadies), allegations of personal criminal deportation.
- **Exclusions:** General criticism of student protesters as a collective group (see `crowd_legitimacy`); claims asserting violence by an unnamed group member.
- **Real Example 1:** `R0036` — "The video shows a four-year-old personal video of Abhijeet Dipke, the founder of the Cockroach Janata Party, kissing a young woman."
- **Real Example 2:** `R0039` — "The image shows Abhijeet Dipke gained 12 Kgs during the Cockroach Janata Party’s protest in Delhi."
- **Tricky Counter-Example:** `R0020` — "A viral video of BJP leader and former Union Minister Maneka Gandhi attended the ongoing CJP protest." *(Classified as `crowd_legitimacy`: claims political endorsement from a senior ruling-party leader to boost protest standing, rather than a personal character assassination).*

### 3.6 `other`
- **Definition:** Claims that are on-topic (related to the protest or its political fallout) but do not fall within the five core narrative categories.
- **Inclusions:** Administrative and policy rumors (e.g., fake resignation letters of ministers, rumors of internet/media blackouts, logistical announcements); pro-police civilian demonstrations or youth gatherings supporting law enforcement (`R0012`, `R0085`).
- **Exclusions:** Any off-topic claims (see Section 2.2); any claim meeting the definitions of sections 3.1–3.5 above.
- **Real Example 1:** `R0027` — "Purported resignation letter of Dharmendra Pradhan shared amid CJP protests."
- **Real Example 2:** `R0091` — "Post claiming central government imposed news blackout following student deaths"
- **Real Example 3:** `R0012` & `R0085` — "This video shows people supporting the Delhi Police amid the CJP-led protests." / "The video shows a group of youths gathering at India Gate in support of the Delhi Police against the CJP protests." *(Pro-police civilian counter-demonstrations).*
- **Tricky Counter-Example:** `R0086` — "In an interview with The Lallantop, JNU students alleged that professors were forcing them to participate." *(Classified as `crowd_legitimacy`: challenges the organic authenticity/voluntariness of student participation).*

---

## 4. Content Form Codes (`content_form`)

Coders record the primary media or textual manipulation format documented in the fact-check report.

### 4.1 `old_or_out_of_context`
- **Definition:** Genuine, unmanipulated archival photo or video footage from a completely different time, event, or geographic location falsely presented as recent footage of the 2026 CJP Jantar Mantar protest.
- **Real Example 1:** `R0002` — "Video shows astronaut Sunita Williams joining the CJP Protest." *(Old video from Kerala Literature Festival, January 2026).*
- **Real Example 2:** `R0041` — "A video shows protesters kissing during a protest by the Cockroach Janta Party (CJP) at Delhi's Jantar Mantar." *(Footage from the 2014 JNU Kiss of Love campaign).*
- **Tricky Counter-Example:** `R0007` — "CJP protesters raised Islamic slogans at Jantar Mantar." *(Cropped video from the actual CJP protest, not an old event; resolves to `cropped_or_edited`).*

### 4.2 `ai_generated`
- **Definition:** Completely synthetic visuals or audio produced from scratch using generative artificial intelligence tools (e.g., Midjourney, Stable Diffusion, Sora, voice cloning models).
- **Real Example 1:** `R0087` — "AI-generated image showing deceased student after police lathicharge at Jantar Mantar" *(Synthetic photo of injured student).*
- **Real Example 2:** `R0019` — "This image shows a woman in revealing clothing participating in the CJP protest at Jantar Mantar." *(Synthetic image produced to malign protesters).*
- **Tricky Counter-Example:** `R0039` — "The image shows Abhijeet Dipke gained 12 Kgs during the Cockroach Janata Party’s protest in Delhi." *(Looks like synthetic AI generation, but the report establishes it was a digitally warped/morphed real photograph without generative AI; resolves to `cropped_or_edited` and `documented_non_ai`).*

### 4.3 `ai_altered`
- **Definition:** Authentic imagery or audio that has been substantially modified, extended, or manipulated using generative AI tools (e.g., generative fill, crowd magnification, inpainting, AI voice replacement).
- **Real Example 1:** `R0014` — "Visuals show crowd at Cockroach Janta Party's protest at Jantar Mantar in Delhi" *(BOOM analysis confirmed aerial crowd density was synthetically magnified using generative AI tools).*
- **Real Example 2:** `R0045` — "Union Minister Piyush Goyal claimed that 2-3 cockroaches should be hanged to teach them a lesson" *(Alt News confirmed video used AI voice clone deepfake to alter genuine footage).*
- **Tricky Counter-Example:** `R0087` — "AI-generated image showing deceased student..." *(Classified as `ai_generated`: entirely synthetic visual generated from scratch, not a modified original photo).*

### 4.4 `cropped_or_edited`
- **Definition:** Traditional shallowfake editing without generative AI: selective temporal clipping of video, omission of crucial contextual speech, speed alterations, or manual photo warping/juxtaposition.
- **Real Example 1:** `R0007` — "CJP protesters raised Islamic slogans at Jantar Mantar." *(Clip truncated to omit patriotic slogans preceding and following).*
- **Real Example 2:** `R0039` — "The image shows Abhijeet Dipke gained 12 Kgs during the Cockroach Janata Party’s protest in Delhi." *(Digitally warped/morphed real photograph without generative AI).*
- **Tricky Counter-Example:** `R0036` — "The video shows a four-year-old personal video of Abhijeet Dipke..." *(Video is unedited, but falsely attributed to Dipke; resolves to `old_or_out_of_context`).*

### 4.5 `fabricated_text`
- **Definition:** Claims based on forged physical or digital documents, fake official letterheads, fabricated press releases, fake tweets/posts created with template generators, or fabricated text quotes.
- **Real Example 1:** `R0027` — "Purported resignation letter of Dharmendra Pradhan shared amid CJP protests." *(Forged letterhead).*
- **Real Example 2:** `R0030` — "Fact check: Bangladesh Jamaat-e-Islami has not backed CJP protest, viral letter is fake" *(Forged organizational endorsement).*
- **Tricky Counter-Example:** `R0002` — "Video shows astronaut Sunita Williams joining..." *(Although viral text caption is false, the core circulating medium is video; resolves to `old_or_out_of_context`).*

### 4.6 `genuine_wrongly_called_fake`
- **Definition:** Authentic media from the protest that was erroneously labeled fake, doctored, or denied by authorities or counter-partisans.
- **Real Example 1:** `R0080` — "This image, showing a large crowd at the CJP's protest in Delhi, is an AI-generated one." *(Fact-check by The Quint proved the viral photo was authentic, taken by The Hindu's photojournalist at Jantar Mantar, and was falsely accused of being AI; resolves to `genuine_wrongly_called_fake` and `documented_non_ai`).*
- **Real Example 2:** *no clear example among the audited codebook examples; coders may encounter this code in the other records.*

### 4.7 `disputed`
- **Definition:** Situations where fact-checking organizations or official inquiries present contradictory conclusions or where facts remain contested.
- **Data Availability Note:** *no clear example among the audited codebook examples; coders may encounter this code in the other records.*

### 4.8 `not_established`
- **Definition:** Media or claims where the fact-checker explicitly reports that the original source, date, or production method could not be conclusively verified due to low resolution or lack of metadata.
- **Data Availability Note:** *no clear example among the audited codebook examples; coders may encounter this code in the other records.*

---

## 5. Political Direction Codes (`direction`)

Coders record the net political effect of the claim's narrative assertion relative to the protest agitation.

> [!IMPORTANT]
> **Direction Decision Rule:** If a reader believed the claim, does it help or hurt the protest's standing? Help = `supports_protesters`; hurt = `supports_police_government`; both = `mixed`; neither or entertainment = `unclear`.

### 5.1 `supports_protesters`
- **Definition:** The claim advances the cause, moral authority, victimhood, or popular momentum of the student protesters; or portrays police/government actions as brutal, unjust, corrupt, or tyrannical.
- **Real Example 1:** `R0002` — "Video shows astronaut Sunita Williams joining the CJP Protest." *(Lends national/international celebrity prestige).*
- **Real Example 2:** `R0087` — "AI-generated image showing deceased student after police lathicharge at Jantar Mantar" *(Portrays protesters as victims of lethal police brutality).*
- **Tricky Counter-Example:** `R0061` — "20 जुलाई को CJP के 'संसद मार्च' के दौरान प्रदर्शनकारियों के हमले में दिल्ली पुलिस के हेड कांस्टेबल अमित की मौत हो गई." *(Classified as `supports_police_government`: paints protesters as violent murderers).*

### 5.2 `supports_police_government`
- **Definition:** The claim discredits, trivializes, or delegitimizes the protest (framing it as violent, anti-national, communal, or frivolous); or defends/justifies police actions and state authority.
- **Real Example 1:** `R0007` — "CJP protesters raised Islamic slogans at Jantar Mantar." *(Delegitimizes protest as communal/divisive).*
- **Real Example 2:** `R0031` — "Video shows CJP protesters attacking India's first hydrogen-powered train in Delhi." *(Portrays protesters as reckless saboteurs of public assets).*
- **Real Example 3:** `R0012` & `R0085` — "This video shows people supporting the Delhi Police amid the CJP-led protests." / "The video shows a group of youths gathering at India Gate in support of the Delhi Police against the CJP protests." *(Both depict civilian gatherings backing law enforcement).*
- **Tricky Counter-Example:** `R0027` — "Purported resignation letter of Dharmendra Pradhan shared amid CJP protests." *(Classified as `supports_protesters`: implies government capitulation and minister culpability).*

### 5.3 `mixed`
- **Definition:** The claim embodies countervailing political vectors where neither side clearly benefits, or portrays simultaneous mutual fault.
- **Real Example 1:** `R0055` — "An image was shared online claiming to show Uttar Pradesh Chief Minister Yogi Adityanath condemning both examination authorities and street agitators."
- **Tricky Counter-Example:** `R0012` / `R0085` — "This video shows people supporting the Delhi Police amid the CJP-led protests." *(Classified as `supports_police_government`: explicitly aligns with law enforcement).*

### 5.4 `unclear`
- **Definition:** Satirical, bizarre, or apolitical claims where a clear directional alignment toward the protest conflict cannot be established.
- **Real Example 1:** `R0047` — "CJP founder and president Abhijeet Dipke during an audition for Roadies" *(Viral entertainment trivia without obvious ideological alignment).*
- **Real Example 2:** `R0053` — "Anna Hazare attended the CJP press conference." *(Unverified political rumor without obvious ideological tilt).*
- **Tricky Counter-Example:** `R0039` — "The image shows Abhijeet Dipke gained 12 Kgs during the Cockroach Janata Party’s protest in Delhi." *(Classified as `supports_police_government`: mocks his hunger strike integrity).*

---

## 6. Media Production Origin Codes (`origin`)

Coders record media production origin **only if the fact-check report explicitly provides documentary or forensic evidence**. Never infer AI origin from appearance, tone, stylistic smoothness, or automated detector scores. If the report provides no documentary determination, record `unknown`.

### 6.1 `documented_ai`
- **Definition:** The fact-check report provides documentary evidence that the visual, audio, or video was produced de novo or altered using generative artificial intelligence tools (e.g., Midjourney, Stable Diffusion, DALL-E, Sora, voice cloning models), cited by forensic lab analysis, tool watermarks, or creator admission.
- **Inclusions:** Completely synthetic AI imagery of martyrs or protesters; AI generative fill/magnification of crowds; AI voice clone deepfakes.
- **Exclusions:** Traditional shallowfakes, manual photoshops, cropping, or spliced clips without generative AI.
- **Real Example 1:** `R0087` — "AI-generated image showing deceased student after police lathicharge at Jantar Mantar" *(BOOM cited digital forensic inconsistencies and AI generation artifacts).*
- **Real Example 2:** `R0019` — "This image shows a woman in revealing clothing participating in the CJP protest at Jantar Mantar." *(India Today reported conclusive evidence of text-to-image AI generation).*
- **Real Example 3:** `R0014` — "Visuals show crowd at Cockroach Janta Party's protest at Jantar Mantar in Delhi" *(BOOM confirmed crowd density was synthetically magnified using generative AI tools).*
- **Real Example 4:** `R0045` — "Union Minister Piyush Goyal claimed that 2-3 cockroaches should be hanged..." *(Alt News confirmed AI voice clone deepfake was superimposed on genuine footage).*
- **Tricky Counter-Example:** `R0039` — "The image shows Abhijeet Dipke gained 12 Kgs during the Cockroach Janata Party’s protest in Delhi." *(Report proved digital photo warping/morphing without generative AI; resolves to `documented_non_ai`).*

### 6.2 `documented_non_ai`
- **Definition:** The fact-check report documents that the circulating media originated from genuine camera recordings (e.g., old historical footage, news broadcasts, unrelated events) or traditional non-generative digital manipulation (manual photo cropping, speed alterations, digital warping, forged paper letterheads).
- **Inclusions:** Old authentic clips from 2014 JNU rallies, 2026 literary festivals, Bihar road accidents, digitally warped portraits, or forged resignation letters.
- **Exclusions:** Media created or enhanced with generative AI.
- **Real Example 1:** `R0002` — "Video shows astronaut Sunita Williams joining the CJP Protest." *(Traced to authentic video from Kerala Literature Festival, January 2026).*
- **Real Example 2:** `R0041` — "A video shows protesters kissing during a protest by the Cockroach Janta Party (CJP) at Delhi's Jantar Mantar." *(Traced to authentic 2014 JNU Kiss of Love footage).*
- **Real Example 3:** `R0080` — "This image, showing a large crowd at the CJP's protest in Delhi, is an AI-generated one." *(Traced to authentic photograph by The Hindu's photojournalist).*
- **Tricky Counter-Example:** `R0087` — "AI-generated image showing deceased student..." *(Synthetically generated by AI, not authentic footage; resolves to `documented_ai`).*

### 6.3 `disputed`
- **Definition:** Credible fact-checking organizations or forensic investigations present conflicting findings regarding whether generative AI or authentic footage was involved.
- **Inclusions:** Cases where one verification desk claims AI synthesis while another identifies authentic footage or manual CGI.
- **Data Availability Note:** *no clear example among the audited codebook examples; coders may encounter this code in the other records.*

### 6.4 `unknown`
- **Definition:** The fact-check report debunks the narrative assertion but provides no conclusive forensic evidence or documentary attribution regarding how the circulating media was produced; or the original source footage could not be traced.
- **Inclusions:** Grainy mobile clips, low-resolution screen captures, or textual rumors where provenance could not be verified.
- **Data Availability Note:** *no clear example among the audited codebook examples; coders may encounter this code in the other records.*

---

## 7. Qualitative Codebook Audit: Findings & Rule Refinements

A qualitative audit was conducted on all **28 real records** cited in `CODEBOOK.md`. Each underlying report was opened and read prior to coding.

| Record ID | Claim Summary | Source Fact-Check Finding | Assigned Narrative | Hard Boundary / Refinement Reason |
|:---|:---|:---|:---|:---|
| `R0038` | CM Vijay visiting CJP protest | Telugu Post: Archival clip from public meet | `crowd_legitimacy` | Political endorsement boosts movement mandate. |
| `R0002` | Sunita Williams joining protest | BOOM: Kerala Literature Festival clip | `crowd_legitimacy` | Celebrity endorsement reinforces crowd legitimacy. |
| `R0030` | Jamaat-e-Islami letter backing CJP | Lighthouse: Forged letterhead | `slogans_communal_loyalty` | Alleges Islamic extremist solidarity. |
| `R0039` | Abhijeet Dipke gained 12 kg | Telugu Post: Digitally warped photo | `individual_targeting` | Personal mockery of organizer's hunger strike (shallowfake, non-AI). |
| `R0025` | Muslim man burning car at protest | Factly: Bihar road rage incident | `protester_violence` | **Boundary Refinement:** While communal identity is highlighted, Rule T1 mandates classifying physical arson/violence under `protester_violence`. |
| `R0036` | Old video of Dipke kissing woman | Factly: Unrelated couple from Bangladesh | `individual_targeting` | Personal smear aimed at organizer's private life. |
| `R0014` | Visuals show massive CJP crowd | BOOM: Crowd magnified using AI | `crowd_legitimacy` | Claims massive turnout to inflate popular support (generative AI crowd magnification). |
| `R0087` | AI image of deceased student | BOOM: Synthetic image of victim | `police_force` | Alleges fatal police lathi-charge (fully synthetic AI visual). |
| `R0007` | Protesters chanting Islamic slogans | The Quint: Cropped video omitting slogans | `slogans_communal_loyalty` | Allegation of communal chanting without physical acts. |
| `R0019` | Woman in revealing clothing | India Today: AI-generated woman visual | `crowd_legitimacy` | **Boundary Refinement:** Unnamed visual depiction smears the moral character and decorum of the crowd at large; not `individual_targeting`. |
| `R0061` | Delhi Police constable Amit killed | Aaj Tak: Policeman died of illness | `protester_violence` | Alleges homicide of police officer by protesters. |
| `R0041` | Protesters kissing at Jantar Mantar | DigitEye: 2014 JNU Kiss of Love clip | `crowd_legitimacy` | **Boundary Refinement:** Targets crowd culture and decency rather than an individual leader. |
| `R0080` | Crowd photo is AI-generated | The Quint: Genuine photo by The Hindu | `crowd_legitimacy` | **Boundary Refinement:** Genuine photo falsely accused of being fake; assigned `genuine_wrongly_called_fake` and `documented_non_ai`. |
| `R0045` | Piyush Goyal hang cockroaches | Alt News: AI voice clone deepfake | `other` | **Boundary Refinement:** AI audio deepfake altering genuine speech; assigned `ai_altered` and `documented_ai`. |
| `R0012` | People supporting Delhi Police | The Quint: Archival pro-police gathering | `other` | **Boundary Refinement:** Civilian demonstration supporting law enforcement; assigned `other` and `supports_police_government`. |
| `R0085` | Youths supporting Delhi Police | Factly: Old India Gate youth gathering | `other` | **Boundary Refinement:** Consistent with `R0012`, assigned `other` and `supports_police_government`. |

### Rule Adjustments Resulting from Audit:
1. **Clarified Rule T1:** Claims combining communal identity and violent acts (e.g., `R0025`) are consistently coded as `protester_violence` because the asserted action is violent destruction of property.
2. **Clarified Leader vs. Anonymous Protester Distinction:** Smears involving anonymous actors (e.g., `R0019`, `R0041` kissing/clothing) code to `crowd_legitimacy` (characterizing the movement's crowd culture), whereas smears directed at named organizers (`R0036`, `R0039`) code to `individual_targeting`.
3. **Harmonized Direction for Pro-Police Rallies:** Civilian demonstrations expressing solidarity with Delhi Police (`R0012`, `R0085`) are consistently coded as `supports_police_government` under direction and `other` under narrative.
4. **Explicit Separation of Shallow Morphing vs AI:** Traditional photo warping/morphing (`R0039`) is coded as `cropped_or_edited` / `documented_non_ai`, reserving `ai_altered` for generative AI modifications (e.g., voice cloning in `R0045`, generative crowd magnification in `R0014`).
