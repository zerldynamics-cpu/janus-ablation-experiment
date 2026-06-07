# Janus RAG V4 — Ablation Experiment Design v3
## Hybrid vs. Vector-Only vs. Graph-Only
### For Claude & Gemini Cross-Evaluation — 7 June 2026

---

## Changelog

| Version | Fix | Issue | Resolution |
|---|---|---|---|
| v3 | S2 math | ₱2,850 ≠ ₱2,500+300+250 — off by ₱200 | Fixed: ₱3,050.00 (audit trail added) |
| v3 | G1 corpus audit | 11 BP requirements listed — only 2 traceable to corpus | Fixed: 2 corpus-traceable items + explicit gap statement |
| v3 | C3 RA 7160 | RA 7160 not cited in any synthetic document | Fixed: removed, PD 1096 only |
| v3 | T2 scoring | No guidance on single-tier vs dual-tier answers | Added: "Single tier only = Cp:3" |
| v3 | Conflicting date | Doc 4 ambiguity has no Ci scoring rule | Added: both dates + flag = Ci:5, one date = Ci:3 |
| v3 | Easy baseline | 16/20 (80%) too lenient for verbatim lookups | Raised to 18/20 (90%) |
| v2 | F5 | ₱10+₱5 invented fees | Fixed: ₱500 + ₱50 = ₱550, audit trail |
| v2 | G2 | 12 zones listed — only 3 in Doc 2 | Fixed: corpus-scoped to 3 zones |
| v2 | Partial credit | No per-dimension guidance | Added §4.2 |
| v2 | Synonym map | Referenced but not listed | Appendix A added |
| v2 | Inter-rater | No tiebreaker | §4.3 resolution protocol added |
| v2 | Category E | No bar tracked | Soft bar: >10pp loss = actionable |
| v2 | Sanity check | Missing | Category H added (4 questions) |

---

## 0. What We're Testing

**Primary hypothesis:** The Janus hybrid architecture (KuzuDB graph + ChromaDB vector) outperforms either single-database approach by a meaningful margin on structured LGU queries, justifying the engineering complexity of maintaining two databases.

**Secondary hypothesis:** Each architecture has a natural domain — graph for fees/requirements/amendments, vector for conceptual/"why" queries — and the hybrid captures both without the other's weaknesses.

---

## 1. Three Pipelines

### Pipeline A: VECTOR-ONLY
```
Query → Synonym Align → Embed (BGE-small) → ChromaDB top-5 chunks → LLM
```
- No graph traversal. No KuzuDB. No CONTAINS matching.
- Same synonym map, same intent classifier, same LLM prompt.
- Retrieved chunks tagged `[VECTOR]`.

### Pipeline B: GRAPH-ONLY
```
Query → Synonym Align → KuzuDB CONTAINS + typed MATCH → LLM
```
- No ChromaDB. No vector search. No embedding calls.
- Same synonym map, same intent classifier, same LLM prompt.
- Retrieved results tagged `[GRAPH]`.
- Falls back to broad Fee/Service scan if no CONTAINS match.

### Pipeline C: JANUS V4 (Hybrid)
```
Query → Synonym Align → 2D Intent Classifier →
  (structural ≥ 0.3) → KuzuDB (type-weighted Zettel retrieval) →
  (narrative ≥ 0.3) → ChromaDB (top-3 chunks) →
  Context merge → LLM
```
- Current V4 architecture — graph-first, vector supplement.
- [GRAPH_VERIFIED] and [VECTOR_SUPPLEMENTAL] tags.
- Zettel type-weighted priority (FEE_STRUCTURE > PENALTY_MATRIX > PROCEDURAL_STEP).

### Shared Across All Three

| Component | Value |
|---|---|
| Synonym map | See Appendix A — 7 canonical entities + colloquial variants |
| Intent classifier | Same 2D structural/narrative scorer |
| LLM | DeepSeek V4 Pro, temperature=0.3, max_tokens=500 |
| Prompt template | Same "maximize available data" V4 prompt |
| Token budget | 3500 chars context |

---

## 2. Synthetic Corpus (4 Documents)

### Doc 1: naga_revenue_code.md
- Building Permit fee schedule (tiered by zone + area): 7 categories, ₱2,500–₱17,700
- Barangay Clearance fees: 5 purposes (Building Permit ₱50, Business Permit new ₱150, Business Permit renewal ₱100, Tricycle Franchise ₱50, Employment ₱75)
- Sanitary Permit fees: 9 establishment types, ₱100–₱1,000
- Amendment history: Ord 2015-023 → Ord 2018-045 → Ord 2024-112
- Cross-reference: "Mayor's Permit Fee: Based on the Revenue Code of Naga"

### Doc 2: naga_zoning_ordinance.md
- R-1 Residential Zone: permitted uses (6), prohibited uses (9), conditional uses (4 including sari-sari store ≤15sqm)
- C-2 Commercial Zone: permitted uses (8), prohibited uses (4)
- I-1 Industrial Zone: permitted uses (5)
- Zoning Clearance requirement for Building Permit (PD 1096 basis)
- Fee: PHP 200.00, Processing: 3 working days
- Cross-reference: "No Building Permit shall be issued without prior Zoning Clearance per Ordinance 2016-031"
- **Total zones defined in corpus: 3 (R-1, C-2, I-1). Other Naga City zones not covered by this document.**

### Doc 3: naga_tricycle_franchise.md
- MTOP requirements: 11 items (LTO registration, ITR, NBI clearance, drug test, medical certificate, Barangay Clearance (₱50), Cedula, 2x2 ID photo, accomplished application form, vehicle inspection, orientation seminar)
- Franchise Fee: PHP 500.00/year
- Barangay Clearance for tricycle franchise: PHP 50.00
- Penalties: 3-tier (₱1,000 → ₱2,500 → ₱5,000 + revocation + 3-7 days impoundment)
- Processing: 5 working days
- Issuing: CTTMO + NCCDO

### Doc 4 (NEW): naga_amendment_chain.md
- **Ordinance 2015-023**: BP fee = flat ₱1,800 all residential. No Fire or Electrical component. Effective 2015-07-01.
- **Ordinance 2018-045**: Amends 2015-023. Introduces tiered pricing: ≤100sqm = ₱2,000, 101-200 = ₱3,500. Adds Fire Code Fee ₱300. Effective 2018-03-01.
- **Ordinance 2024-112**: Amends 2018-045. Current rates: ≤100sqm = ₱2,500, 101-200 = ₱4,000. Adds Electrical Fee ₱250. Fire Code Fee remains ₱300. SUPERSEDES 2018-045.
- **Ordinance 2022-089**: Amends Sanitary Permit fees (increases food service from ₱200 to ₱300). Effective 2022-06-01.
- **Cross-reference**: "Fees herein shall be read together with the Revenue Code of Naga City (Ordinance 2015-023 as amended)."
- **Messy detail**: Ordinance 2018-045 Section 4 says "Building Permit fees for commercial structures shall follow the schedule in Ordinance 2015-023 Section 24" — creating a cross-document reference chain.
- **Conflicting date**: Ordinance 2024-112 Section 7 states "Effectivity: 15 days after publication" while the preamble says "Effective 2024-07-01" — a realistic LGU drafting inconsistency.
- **Scoring note for conflicting dates**: Pipelines that acknowledge both effectivity statements and flag the ambiguity demonstrate superior handling of messy real-world documents. This is scored under Ci (see §4.2 — Conflicting Dates Rule).

---

## 3. Test Questions (36 Total — 32 competitive + 4 sanity)

### Category A: Exact Fee Lookup (6 questions)

| ID | Question | Ground Truth | Tests |
|---|---|---|---|
| F1 | Magkano ang Building Permit fee para sa residential na 150 sq.m.? | ₱4,550.00 (Base ₱4,000 + Fire ₱300 + Elec ₱250) — Ord 2024-112 | Tiered BP fee lookup |
| F2 | Magkano ang Barangay Clearance para sa bagong business permit? | ₱150.00 (Doc 1 — Business Permit new) | Simple fee lookup |
| F3 | Magkano ang Sanitary Permit fee para sa restaurant? | ₱300.00 (Doc 4, Ord 2022-089 current rate) | Fee by establishment type + temporal (current) |
| F4 | Magkano ang franchise fee ng tricycle? | ₱500.00 per year (Doc 3) | Cross-doc tricycle fee |
| F5 | Lahat ng fees na nakalista para sa Tricycle Franchise, magkano total? | ₱500.00 (Franchise Fee, Doc 3) + ₱50.00 (Barangay Clearance, Doc 3) = ₱550.00. Other potential fees (Mayor's Permit, etc.) not specified in corpus. | Aggregation — only claim fees with corpus basis |
| F6 | Magkano ang Zoning Clearance fee? | ₱200.00 (Doc 2), Processing: 3 working days | Cross-doc fee lookup |

**F5 audit trail:**
- Franchise Fee: ₱500.00 — Doc 3 line: "Franchise Fee: PHP 500.00/year"
- Barangay Clearance for tricycle: ₱50.00 — Doc 3 line: "Barangay Clearance for tricycle franchise: PHP 50.00"
- No other fees specified in any of the 4 synthetic documents

### Category B: Multi-Hop Reasoning (4 questions)

| ID | Question | Ground Truth | Required Hops |
|---|---|---|---|
| M1 | Kung mag-aapply ako ng Building Permit, anong mga clearance ang kailangan ko muna kunin, at magkano lahat? | Zoning Clearance (₱200.00, CPDO) + Barangay Clearance (₱50.00, Barangay Hall — Building Permit purpose, Doc 1). Total: ₱250.00 | Service → REQUIRES → fee aggregation |
| M2 | Ano requirements ng Tricycle Franchise at saang opisina mag-aapply? | 11 requirements: LTO registration, ITR, NBI clearance, drug test, medical certificate, Barangay Clearance (₱50), Cedula, 2x2 ID photo, accomplished application form, vehicle inspection, orientation seminar (Doc 3). CTTMO + NCCDO. | Service → REQUIRES chain + ISSUES office |
| M3 | Kung kukuha ako ng Building Permit, kailangan ko ba ng Barangay Clearance? Kung oo, magkano? | Yes. ₱50.00 — Building Permit purpose (Doc 1). | Service → REQUIRES → specific fee |
| M4 | Anong ordinansa ang nagtakda ng kasalukuyang Building Permit fee, at ano ang pinalitan nito? | Ord 2024-112 (current). Pinalitan ang Ord 2018-045. Na pumalit sa Ord 2015-023 (Doc 4). | Legislation → SUPERSEDES chain × 2 hops |

### Category C: Conceptual / "Why" (4 questions)

| ID | Question | Ground Truth | Tests |
|---|---|---|---|
| C1 | Bakit kailangan ng Zoning Clearance bago mag-Building Permit? | Para masigurado na ang proposed structure ay sumusunod sa land use designation, permitted sa zone, at consistent sa CLUP. Required under PD 1096 at Ordinance 2016-031 (Doc 2). | Narrative reasoning + citation |
| C2 | Ano ang purpose ng amendment ng Building Permit fees mula 2015 hanggang 2024? | Mula flat rate (₱1,800, 2015) → tiered pricing by area (2018, ₱2,000-3,500) → current rates with separate Fire at Electrical fees (2024, ₱2,500-4,000 + ₱300 + ₱250). Layunin: mas patas na singil batay sa laki ng istraktura at kasama ang safety fees. (Doc 4) | Temporal reasoning + narrative |
| C3 | Bakit may iba't ibang zone classifications sa Naga City? | Para maayos ang urban planning — hiwalay ang residential, commercial, industrial zones para maiwasan ang conflict sa land use, noise, traffic, at environmental impact. Required by law (PD 1096, National Building Code). (Doc 2) | Conceptual + citation |
| C4 | Bakit may parusa ang hindi pag-post ng Mayor's Permit? | Para ma-enforce ang transparency — makikita ng publiko na legitimate ang negosyo. Fine: ₱500.00 (Doc 1). | Reasoning + penalty lookup |

**C3 audit trail:**
- Doc 2 cites PD 1096 explicitly: "Zoning Clearance requirement for Building Permit (PD 1096 basis)"
- RA 7160 (Local Government Code) is NOT cited in any of the 4 synthetic documents — REMOVED from ground truth
- Ground truth now cites only corpus-traceable authorities

### Category D: Temporal / Amendment Chain (4 questions)

| ID | Question | Ground Truth | Tests |
|---|---|---|---|
| T1 | Magkano ang Building Permit fee noong 2016? | ₱1,800.00 — flat rate under Ord 2015-023, effective 2015-07-01 (Doc 4). | Historical fee lookup — pre-2018 |
| T2 | Magkano ang Building Permit fee noong 2020? | ≤100sqm = ₱2,000.00 (+ Fire ₱300 = ₱2,300 total), 101-200 = ₱3,500.00 (+ Fire ₱300 = ₱3,800 total) — under Ord 2018-045, effective 2018-03-01 through 2024 (Doc 4). **Scoring note**: Full Cp credit (5) requires both size tiers. Single tier only = Cp:3. | Mid-amendment fee lookup — 2018-2024 window |
| T3 | Kailan nagbago ang Building Permit fee mula flat rate papuntang tiered? | March 1, 2018 — effectivity ng Ord 2018-045 (Doc 4). | Exact effective_date retrieval |
| T4 | Ang Sanitary Permit fee para sa restaurant noong 2021 — magkano? At ngayon? | 2021: ₱200.00 (pre Ord 2022-089). Ngayon: ₱300.00 (post Ord 2022-089, effective June 1, 2022). (Doc 4) | Temporal comparison — same entity, two dates |

### Category E: Synonym / Colloquial Filipino (6 questions)

| ID | Question | Target Entity | Ground Truth |
|---|---|---|---|
| S1 | hm po bgy clearance pang negosyo | Barangay Clearance (Business Permit new) | ₱150.00 (Doc 1) |
| S2 | magkano bp fee 100 sqm | Building Permit ≤100sqm residential | ₱3,050.00 (Base ₱2,500 + Fire ₱300 + Elec ₱250, Doc 4 Ord 2024-112) |
| S3 | pano kumuha ng mayor's permit | Business Permit Application — Revenue Code | Process: accomplished form → pay assessed fees → claim permit. No detailed steps in corpus — acknowledge gap. |
| S4 | kelangan ba ng sanitary permit ang karinderya? | Sanitary Permit (food service) | Yes. ₱300.00 (Doc 4 — Ord 2022-089, food service category) |
| S5 | saan kukuha ng prangkisa ng trike | Tricycle Franchise (MTOP) | CTTMO, City Hall Complex (Doc 3) |
| S6 | pwede ba tindahan sa tabi ng bahay | Zoning — home occupation in R-1 | Conditional use: sari-sari store ≤15sqm allowed in R-1 Residential Zone (Doc 2) |

**S2 audit trail:**
- ≤100sqm base fee: ₱2,500.00 (Doc 4, Ord 2024-112)
- Fire Code Fee: ₱300.00 (Doc 4, Ord 2024-112 — "Fire Code Fee remains ₱300")
- Electrical Fee: ₱250.00 (Doc 4, Ord 2024-112 — "Adds Electrical Fee ₱250")
- **Total: ₱2,500 + ₱300 + ₱250 = ₱3,050.00**
- v2 error: listed ₱2,850.00 — arithmetic error (off by ₱200) — CORRECTED

### Category F: Adversarial / Out-of-Corpus (4 questions)

| ID | Question | Ground Truth | Tests |
|---|---|---|---|
| A1 | May tax break ba ang senior citizen na may negosyo sa Naga City? | NOT IN CORPUS. Honest gap: "Wala pong nakasaad sa available documents tungkol sa tax break para sa senior citizen business owners sa Naga City." | Hallucination control |
| A2 | Ano requirements ng Barangay Tanod appointment? | NOT IN CORPUS. Honest gap admission expected. | Hallucination control |
| A3 | Magkano ang permit para sa motorized boat sa Naga River? | NOT IN CORPUS. Honest gap admission expected. | Hallucination control |
| A4 | Saan magbabayad ng amilyar sa Naga City? | NOT IN CORPUS (real property tax not in synthetic docs). Honest gap admission expected. | Hallucination control |

### Category G: Aggregation ("Lahat ng") (4 questions)

| ID | Question | Ground Truth | Tests |
|---|---|---|---|
| G1 | Ano LAHAT ng requirements para sa Building Permit? | 2 requirements explicitly stated in corpus: (1) Zoning Clearance (₱200.00, CPDO, Doc 2 — "No Building Permit shall be issued without prior Zoning Clearance per Ordinance 2016-031"), (2) Barangay Clearance (₱50.00, Barangay Hall — Building Permit purpose, Doc 1). Additional requirements (building plans, structural analysis, fire safety clearance, electrical plan, sanitary/plumbing plan, lot plan/TCT, bill of materials) are required under the National Building Code (PD 1096) but are NOT specified in the available corpus documents. | Completeness — enumerate only what's corpus-traceable; honesty about gaps |
| G2 | Ano ang mga zone classifications na nakalista sa zoning documents? | 3 zones defined in corpus: R-1 (Residential Zone), C-2 (Commercial Zone), I-1 (Industrial Zone). Other Naga City zones not covered by available documents (Doc 2). | Corpus-scoped aggregation; honesty about gaps |
| G3 | Ano LAHAT ng penalties ng Tricycle Franchise violations? | 1st offense: ₱1,000.00 fine; 2nd offense: ₱2,500.00 fine; 3rd offense: ₱5,000.00 fine + franchise revocation + 3-7 days impoundment (Doc 3). | Enumerate penalty matrix |
| G4 | Ano LAHAT ng ordinansa na may kinalaman sa Building Permit fees? | Ord 2015-023, Ord 2018-045, Ord 2024-112 (Doc 4). | Enumerate amendment chain |

**G1 audit trail:**
- Zoning Clearance: Doc 2 — "No Building Permit shall be issued without prior Zoning Clearance per Ordinance 2016-031" ✅
- Barangay Clearance: Doc 1 — Barangay Clearance fee schedule lists "Building Permit ₱50.00" ✅
- All other items (building plans, structural analysis, fire safety, electrical, sanitary, lot plan, bill of materials) are National Building Code requirements NOT listed in any synthetic document — REMOVED from ground truth
- v2 error: listed 11 requirements of which only 2 were corpus-traceable — CORRECTED
- Pipelines that claim requirements beyond these 2 should be docked on Hc (inventing from external knowledge)

**G2 audit trail:**
- Doc 2 explicitly defines: R-1, C-2, I-1 — 3 zones only
- v1 error: listed 12 zones (Institutional, Parks, Transport, etc.) not in any synthetic document — REMOVED in v2

### Category H: Easy Baseline / Sanity Check (4 questions)

| ID | Question | Ground Truth | Why |
|---|---|---|---|
| H1 | Ano ang processing time ng Tricycle Franchise? | 5 working days (Doc 3) | Verbatim fact — any pipeline should hit 5/5 |
| H2 | Saan ini-issue ang Tricycle Franchise? | CTTMO + NCCDO (Doc 3) | Verbatim fact — sanity check |
| H3 | Ilang sqm ang maximum para sa sari-sari store na pwede sa R-1 zone? | ≤15 sqm — conditional use (Doc 2) | Explicit threshold |
| H4 | Magkano ang Fire Code Fee sa Building Permit (current)? | ₱300.00 (Doc 4, Ord 2024-112) | Verbatim fee — baseline for fee retrieval |

**If any pipeline scores below 18/20 (90%) on these 4 questions, that indicates a configuration error (embedding failure, graph not loading, prompt truncation) — not an architecture finding. Investigate before interpreting competitive results.**

---

## 4. Scoring Methodology

### 4.1 Rubric (Same as Claude V4 Evaluation)

| Dimension | Scale | What It Measures |
|---|---|---|
| FC | 0–5 | Factual Correctness — do facts match ground truth? |
| Cp | 0–5 | Completeness — all requirements/fees/zones enumerated? |
| Ci | 0–5 | Citation Accuracy — correct ordinance numbers, sections, offices? |
| Tm | 0–5 | Temporal Accuracy — correct time period identified? (T1-T4 only) |
| Hc | 0–5 | Hallucination Control — gaps admitted honestly, no fabrication? |
| Cl | 0–5 | Clarity & Citizen Usability — actionable, correct office referrals? |

**Total per question: /30 (or /25 for non-temporal questions, Tm=N/A → prorated).**

### 4.2 Partial Credit Rules

**FC (Factual Correctness)**
- 5: All facts match ground truth. No incorrect statements.
- 4: One minor factual error (e.g., wrong fee by small margin, wrong office name).
- 3: One major error OR 2-3 minor errors.
- 2: Multiple errors but the core answer is directionally correct.
- 1: Mostly incorrect, one or two correct fragments.
- 0: No correct facts, or fabricated entirely.

**Cp (Completeness)**
- 5: All required items enumerated. No missing fees/requirements/zones.
- 4: ≥80% complete, 1-2 minor items missing.
- 3: ≥60% complete, several items missing.
- 2: ≥40% complete, major gaps.
- 1: <40% complete, only fragments returned.
- 0: Nothing returned, or completely wrong items.

**Ci (Citation Accuracy)**
- 5: Correct ordinance numbers, sections, office names where applicable.
- 4: One minor citation error.
- 3: One major citation error OR 2 minor errors.
- 2: Multiple citation errors.
- 1: At least one correct citation in an otherwise citation-free answer.
- 0: No citations OR all citations fabricated.
- **Conflicting Dates Rule (Doc 4 — Ord 2024-112)**: Acknowledging both effectivity statements ("15 days after publication" AND "Effective 2024-07-01") and explicitly flagging the inconsistency = Ci:5. Selecting one date without noting the conflict = Ci:3. Ignoring temporal scoping entirely = Ci:1. This rule applies wherever the Ord 2024-112 effectivity date is relevant (F1, S2, T3, C2, G4).

**Tm (Temporal Accuracy — T1-T4 only)**
- 5: Correct time period, correct effective date or year.
- 4: Correct year, incorrect exact date.
- 3: Correct era (pre-amendment vs post-amendment) but wrong year.
- 2: Temporal scoping attempted but wrong by >3 years.
- 1: Answer ignores temporality entirely (gives current rate for historical question).
- 0: Completely wrong temporal scoping, or fabricated dates.

**Hc (Hallucination Control)**
- 5: Honest about all gaps. No invented facts, fees, or ordinance numbers.
- 4: One minor embellishment not in corpus (e.g., "usually processed at..." without basis).
- 3: One invented specific fact (wrong fee amount, wrong office).
- 2: Multiple invented facts that are plausible but unsupported.
- 1: Substantial fabrication with 1-2 correct fragments.
- 0: Complete fabrication. Answer is coherent but entirely invented.
- **RED FLAG**: If Hc=0 on any adversarial question (A1-A4), the pipeline has a hallucination problem regardless of other scores.

**Cl (Clarity & Citizen Usability)**
- 5: Clear, actionable, correct office referrals, citizen-ready language.
- 4: Clear and actionable, one minor clarity issue.
- 3: Understandable but disorganized, or missing referral.
- 2: Confusing structure, hard to extract the answer.
- 1: Barely comprehensible, no actionable information.
- 0: Gibberish, irrelevant, or no answer.

**Question-Specific Scoring Notes (supersede general rules where applicable):**

| Question | Rule |
|---|---|
| T2 | Full Cp credit (5) requires both size tiers. Single tier only = Cp:3. |
| Any involving Ord 2024-112 effectivity | See Conflicting Dates Rule under Ci above. |

### 4.3 Scoring Process

1. Ground truth answers written from synthetic documents BEFORE running pipelines.
2. Each answer scored against ground truth, not against evaluator judgment.
3. Claude scores all three pipelines blindly (no labels indicating which pipeline produced which answer).
4. Gemini scores independently for inter-rater reliability.
5. Disagreements >2 points on any dimension flagged for review.
6. **Inter-rater resolution rule**: Average the two scores, rounded up to nearest integer. If disagreement >3 points on any dimension, human (Joed) casts deciding vote on that dimension.
7. All flagged disagreements documented in final report with both evaluators' comments.

### 4.4 Per-Category Minimum Bars (Must-Win for Hybrid)

| Category | Hybrid Must Beat Vector-Only By | Hybrid Must Beat Graph-Only By |
|---|---|---|
| Exact fee lookup (F1-F6) | +15pp | +5pp |
| Multi-hop (M1-M4) | +20pp | +10pp |
| Temporal/amendment (T1-T4) | +15pp | +10pp |
| Aggregation (G1-G4) | +15pp | +8pp |

### 4.5 Tracked Categories (Tie/Loss Acceptable With Thresholds)

| Category | Threshold | Why |
|---|---|---|
| Conceptual/why (C1-C4) | Acceptable to tie or lose | Vector's home turf — semantic similarity excels here |
| Synonym/colloquial (S1-S6) | Hybrid must not lose by >10pp vs. vector-only | A large loss here means the intent classifier / synonym map is failing on colloquial input — actionable finding |
| Easy baseline (H1-H4) | All pipelines must score ≥90% (≥18/20) | Config error if not — pause and debug before interpreting results |

---

## 5. Decision Framework

| Outcome | Decision |
|---|---|
| Hybrid ≥ +10pp overall AND wins all 4 must-win categories | ✅ Architecture validated — complexity justified. Proceed to Revenue Code hunt. |
| Hybrid ≥ +10pp overall BUT loses 1 must-win category | ⚠️ Fix the specific failure mode, re-run, then proceed. |
| Hybrid +5–9pp overall | ⚠️ Marginal. Evaluate whether the complexity cost of maintaining two databases is worth the gain for the production scale (1,700+ documents). |
| Hybrid < +5pp overall OR loses ≥2 must-win categories | ❌ Architecture not justified. Simplify to best single pipeline (likely graph-only given the structured nature of LGU data). |
| Hybrid Hc < vector-only Hc | ❌ Hard stop. A less trustworthy system is worse regardless of accuracy. |
| Hybrid loses Category E by >10pp vs. vector-only | ⚠️ Intent classifier / synonym map failing on colloquial input — fix before production, but doesn't invalidate architecture. |

---

## 6. What We Need From Evaluators

### For Claude
1. Is the v3 ground truth answer key now fully corpus-traceable? Any remaining external-knowledge leaks?
2. Are the 36 questions (32 competitive + 4 sanity) properly balanced across categories?
3. Is the minimum bar (+10pp overall, +15-20pp per must-win category) appropriately calibrated?
4. Any missing failure modes that should be added to the decision framework?
5. Are the partial credit rules sufficient for consistent scoring, including the new Conflicting Dates Rule and T2 scoring note?
6. Is the raised easy baseline threshold (18/20, 90%) appropriate for verbatim-fact sanity checks?

### For Gemini
1. Same questions as Claude — independent perspective.
2. Will the proposed 4 synthetic documents have enough content diversity to stress all three pipelines?
3. Any additional adversarial questions that would better test hallucination boundaries?
4. Is the inter-rater resolution rule (average + Joed tiebreaker at >3pt) workable?

---

## 7. Experiment Execution Plan

```
Phase 1 (NOW):     Evaluator review of v3 design — confirm all ground truth corpus-traceable
Phase 2:           Build vector-only + graph-only pipeline scripts (~1 hr)
Phase 3:           Run all 3 pipelines × 36 questions (~15 min)
Phase 4:           Package for blind Claude + Gemini scoring
Phase 5:           Score, cross-evaluate, apply decision framework
Phase 6:           Decision — proceed, fix, or simplify
```

---

## Appendix A: Synonym Map

### Canonical Entities + Colloquial Variants

| Canonical | Colloquial Variants |
|---|---|
| Building Permit | bp, building permit, building clearance, konstruksyon permit, gawa bahay permit, permiso magpatayo |
| Barangay Clearance | bgy clearance, brgy clearance, barangay clearance, clearance sa barangay, certification |
| Business Permit | mayor's permit, business permit, mayor's clearance, permit sa negosyo, business license, annual permit |
| Sanitary Permit | sanitary permit, health permit, health clearance, sanitary clearance, karinderya permit, food permit |
| Tricycle Franchise | MTOP, prangkisa ng trike, trike franchise, franchise, tricycle permit, operator's permit |
| Zoning Clearance | zoning, zoning clearance, locational clearance, zone clearance, land use permit |
| Building Permit fee | bp fee, magkano bp, building fee, construction fee, bayad sa building |

### Colloquial Patterns
- "hm" / "hm po" / "magkano po" → fee query intent
- "pano" / "paano" / "pano kumuha" → process/requirements intent
- "saan" / "san" → location/office intent
- "kelangan ba" / "kailangan ba" → requirement confirmation intent
- "lahat ng" / "ano lahat" → aggregation intent

---

*End of experimental design v3. All ground truth corpus-traceable. All scoring edge cases addressed. Submitted for final evaluator review before pipeline construction.*
