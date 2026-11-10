# QA Report: Coding Sheet & Claim Grouping

- **Population size:** 158 distinct claims (159 rows)
- **Sample size:** 20 distinct claims (random_state=42)
- **Score distribution:** 2 (Clean): 20, 1 (Borderline): 0, 0 (Wrongly Grouped): 0
- **Mean score:** 2.00 / 2.00

## Failure Taxonomy

No grouping failures detected in sample (all proposed claim_ids scored 2/2).

## Item-by-Item Review

| ID | Claim ID | Records | Score | Reason | Primary Text |
| --- | --- | --- | --- | --- | --- |
| CS_01 | C0029 | 1 | 2 | Clean grouping; near-duplicates connected | Senior BJP leader Maneka Gandhi visited Jantar Man... |
| CS_02 | C0007 | 1 | 2 | Clean grouping; near-duplicates connected | CJP protesters raised Islamic slogans at Jantar Ma... |
| CS_03 | C0071 | 1 | 2 | Clean grouping; near-duplicates connected | Farmers heading to join the Cockroach Janta Party'... |
| CS_04 | C0063 | 1 | 2 | Clean grouping; near-duplicates connected | CJP के 'संसद मार्च' के दौरान पुलिस का आंसू गैस का ... |
| CS_05 | C0058 | 1 | 2 | Clean grouping; near-duplicates connected | CJP को लेकर दिल्ली पुलिस और केंद्रीय मंत्री के बया... |
| CS_06 | C0036 | 1 | 2 | Clean grouping; near-duplicates connected | A video shows former NASA astronaut Sunita William... |
| CS_07 | C0027 | 1 | 2 | Clean grouping; near-duplicates connected | Purported resignation letter of Dharmendra Pradhan... |
| CS_08 | C0140 | 1 | 2 | Clean grouping; near-duplicates connected | जंतर मंतर पर छात्रों की भारी भीड़ दिखाने वाली एआई ... |
| CS_09 | C0023 | 1 | 2 | Clean grouping; near-duplicates connected | Visuals of police officers assaulting female prote... |
| CS_10 | C0152 | 1 | 2 | Clean grouping; near-duplicates connected | Drone footage showing endless crowd at Jantar Mant... |
| CS_11 | C0109 | 1 | 2 | Clean grouping; near-duplicates connected | Old video of stone pelting on train in Murshidabad... |
| CS_12 | C0009 | 1 | 2 | Clean grouping; near-duplicates connected | Videos show recent CJP protests |
| CS_13 | C0008 | 1 | 2 | Clean grouping; near-duplicates connected | Video shows Delhi Police vandalsing vehicles durin... |
| CS_14 | C0024 | 1 | 2 | Clean grouping; near-duplicates connected | A video shows a convoy of soldiers travelling to D... |
| CS_15 | C0056 | 1 | 2 | Clean grouping; near-duplicates connected | The video shows the Cockroach Janata Party’s prote... |
| CS_16 | C0060 | 1 | 2 | Clean grouping; near-duplicates connected | 20 जुलाई को CJP के 'संसद मार्च' के दौरान प्रदर्शनक... |
| CS_17 | C0130 | 1 | 2 | Clean grouping; near-duplicates connected | AI-generated video shows Delhi Police commissioner... |
| CS_18 | C0155 | 1 | 2 | Clean grouping; near-duplicates connected | AI images showing student leaders severely injured... |
| CS_19 | C0144 | 1 | 2 | Clean grouping; near-duplicates connected | All Delhi University professors went on indefinite... |
| CS_20 | C0051 | 1 | 2 | Clean grouping; near-duplicates connected | The video shows CJP founder Abhijeet Dipke's old R... |

## What This Sample Cannot Tell Us

1. This sample cannot guarantee that subtle semantic paraphrases in disparate languages were successfully linked by char-n-gram TF-IDF.
2. Coders must still manually confirm proposed claim_ids in the coding sheet.
3. Results apply strictly to the sampled claims and should not be extrapolated to uninspected rows.
