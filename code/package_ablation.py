#!/usr/bin/env python3
"""Package ablation results for blind Claude + Gemini scoring."""
import json, os

OUT_DIR = "/home/joedpogi/.hermes/baseline/answers/ablation"
PIPELINES = ["vector_only", "graph_only", "janus_v4"]

# ── Ground Truth Answers (from experiment design v3) ──
GROUND_TRUTH = {
    "F1": "PHP 4,550.00 (Base PHP 4,000.00 + Fire Code Fee PHP 300.00 + Electrical Fee PHP 250.00) — Ordinance No. 2024-112. Para sa residential 101-200 sq.m.",
    "F2": "PHP 150.00 — Barangay Clearance para sa bagong Business Permit (Revenue Code, Section 42).",
    "F3": "PHP 300.00 — Sanitary Permit fee para sa food service establishments (restaurant, carinderia) sa ilalim ng Ordinance No. 2022-089, effective June 1, 2022.",
    "F4": "PHP 500.00 per year — Tricycle Franchise (MTOP) fee.",
    "F5": "PHP 550.00 total: PHP 500.00 (Franchise Fee) + PHP 50.00 (Barangay Clearance para sa Tricycle Franchise). Iba pang potential fees (Mayor's Permit, atbp.) ay hindi nakasaad sa available documents.",
    "F6": "PHP 200.00 — Zoning/Locational Clearance fee. Processing time: 3 working days. Issuing office: CPDO.",
    "M1": "Zoning Clearance (PHP 200.00, CPDO) + Barangay Clearance (PHP 50.00, Barangay Hall — Building Permit purpose). Total: PHP 250.00.",
    "M2": "11 requirements: (1) Accomplished MTOP Application Form, (2) Certificate of TODA Membership, (3) LTO Certificate of Registration, (4) LTO Driver's License, (5) Barangay Clearance (PHP 50.00), (6) NBI Clearance, (7) Police Clearance, (8) Drug Test Result, (9) Medical Certificate, (10) Two 2x2 ID photos, (11) Proof of Franchise Fee Payment (PHP 500.00). Apply sa CTTMO, in coordination with NCCDO.",
    "M3": "Yes. Barangay Clearance ay kailangan para sa Building Permit. Fee: PHP 50.00 (Building Permit purpose, Revenue Code Section 42).",
    "M4": "Ordinance No. 2024-112 ang kasalukuyang nagtatakda ng Building Permit fees. Pinalitan nito ang Ordinance No. 2018-045. Na pumalit naman sa Ordinance No. 2015-023.",
    "C1": "Para masigurado na ang proposed structure ay sumusunod sa land use designation, permitted sa zone, at consistent sa CLUP. Required under PD 1096 at Ordinance No. 2016-031.",
    "C2": "Mula flat rate (PHP 1,800.00, 2015) → tiered pricing by area (2018, PHP 2,000.00-3,500.00) → current rates na may hiwalay na Fire at Electrical fees (2024, PHP 2,500.00-4,000.00 + PHP 300.00 + PHP 250.00). Layunin: mas patas na singil batay sa laki ng istraktura at kasama ang safety fees.",
    "C3": "Para maayos ang urban planning — hiwalay ang residential, commercial, industrial zones para maiwasan ang conflict sa land use, noise, traffic, at environmental impact. Required by law (PD 1096, National Building Code).",
    "C4": "Para ma-enforce ang transparency — makikita ng publiko na legitimate ang negosyo. Fine: PHP 500.00 (Revenue Code).",
    "T1": "PHP 1,800.00 — flat rate sa ilalim ng Ordinance No. 2015-023, effective July 1, 2015.",
    "T2": "Dalawang tier (under Ordinance No. 2018-045, effective March 1, 2018): Up to 100 sq.m. = PHP 2,300.00 (Base PHP 2,000.00 + Fire PHP 300.00). 101-200 sq.m. = PHP 3,800.00 (Base PHP 3,500.00 + Fire PHP 300.00).",
    "T3": "March 1, 2018 — effectivity date ng Ordinance No. 2018-045 na nag-introduce ng tiered pricing.",
    "T4": "2021: PHP 200.00 (pre-Ordinance No. 2022-089). Ngayon: PHP 300.00 (post-Ordinance No. 2022-089, effective June 1, 2022).",
    "S1": "PHP 150.00 — Barangay Clearance para sa bagong Business Permit.",
    "S2": "PHP 3,050.00 (Base PHP 2,500.00 + Fire Code Fee PHP 300.00 + Electrical Fee PHP 250.00) — Building Permit para sa residential ≤100 sq.m. sa ilalim ng Ordinance No. 2024-112.",
    "S3": "Process: accomplished form → pay assessed fees → claim permit. Ang detailed step-by-step process ay hindi nakasaad sa available documents.",
    "S4": "Yes. Ang karinderya ay food service establishment at kailangan ng Sanitary Permit. Fee: PHP 300.00 (Ordinance No. 2022-089, food service category).",
    "S5": "CTTMO (City Transportation and Traffic Management Office), City Hall Complex, Naga City. In coordination with NCCDO.",
    "S6": "Conditional use — ang sari-sari store na ≤15 sqm ay pinapayagan sa R-1 Residential Zone bilang conditional use. Kailangan ng Locational Clearance.",
    "A1": "NOT IN CORPUS — Wala pong nakasaad sa available documents tungkol sa tax break para sa senior citizen business owners sa Naga City.",
    "A2": "NOT IN CORPUS — Wala pong nakasaad sa available documents tungkol sa requirements para sa Barangay Tanod appointment.",
    "A3": "NOT IN CORPUS — Wala pong nakasaad sa available documents tungkol sa permit para sa motorized boat sa Naga River.",
    "A4": "NOT IN CORPUS — Wala pong nakasaad sa available documents tungkol sa pagbabayad ng amilyar (real property tax) sa Naga City.",
    "G1": "2 requirements explicitly stated in corpus: (1) Zoning Clearance (PHP 200.00, CPDO, Ordinance No. 2016-031), (2) Barangay Clearance (PHP 50.00, Barangay Hall — Building Permit purpose). Additional requirements (building plans, structural analysis, fire safety clearance, electrical plan, sanitary/plumbing plan, lot plan/TCT, bill of materials) ay required under the National Building Code (PD 1096) pero HINDI nakasaad sa available corpus documents.",
    "G2": "3 zones defined in corpus: R-1 (Residential Zone), C-2 (Commercial Zone), I-1 (Industrial Zone). Iba pang zone classifications ng Naga City ay hindi covered ng available documents.",
    "G3": "1st offense: PHP 1,000.00 fine + 3 days impoundment. 2nd offense: PHP 2,500.00 fine + 7 days impoundment. 3rd offense: PHP 5,000.00 fine + franchise revocation for 1 year.",
    "G4": "Tatlong ordinansa: Ordinance No. 2015-023, Ordinance No. 2018-045, Ordinance No. 2024-112.",
    "H1": "5 working days — processing time ng Tricycle Franchise (MTOP).",
    "H2": "CTTMO (City Transportation and Traffic Management Office), in coordination with NCCDO, City Hall Complex, Naga City.",
    "H3": "≤15 sqm — maximum floor area para sa sari-sari store bilang conditional use sa R-1 Residential Zone.",
    "H4": "PHP 300.00 — Fire Code Fee sa Building Permit (current, Ordinance No. 2024-112).",
}

# ── Load Results ──
all_pipelines = {}
for pipeline in PIPELINES:
    path = os.path.join(OUT_DIR, f"{pipeline}_answers.json")
    if os.path.exists(path):
        with open(path) as f:
            all_pipelines[pipeline] = json.load(f)

# ── Package for Blind Scoring ──
# Assign random labels: P1, P2, P3 (shuffled)
import random
labels = ["Pipeline A", "Pipeline B", "Pipeline C"]
random.shuffle(labels)
label_map = dict(zip(PIPELINES, labels))
print("Pipeline Labeling (for evaluator reference after scoring):")
for pipe, label in label_map.items():
    print(f"  {pipe} → {label}")

# Build blind scoring file
scoring = {
    "experiment": "Janus V4 Ablation Experiment",
    "version": "v3",
    "date": "2026-06-07",
    "total_questions": len(QUESTIONS) if 'QUESTIONS' in dir() else 36,
    "pipeline_labels": f"Pipeline A, B, C are vector_only, graph_only, janus_v4 in random order",
    "label_mapping_for_verification": {v: k for k, v in label_map.items()},
    "ground_truth": GROUND_TRUTH,
    "pipelines": {},
}

for pipeline in PIPELINES:
    if pipeline in all_pipelines:
        label = label_map[pipeline]
        scoring["pipelines"][label] = []
        for r in all_pipelines[pipeline]:
            scoring["pipelines"][label].append({
                "id": r["id"],
                "question": r["question"],
                "answer": r["answer"],
            })

# Save scoring package
score_path = os.path.join(OUT_DIR, "ablation_blind_scoring.json")
with open(score_path, 'w') as f:
    json.dump(scoring, f, indent=2, ensure_ascii=False)

# Also save answer key separately
key_path = os.path.join(OUT_DIR, "ablation_ground_truth.json")
with open(key_path, 'w') as f:
    json.dump({"ground_truth": GROUND_TRUTH, "total_questions": len(GROUND_TRUTH)}, f, indent=2, ensure_ascii=False)

# Print summary stats
print(f"\n{'='*60}")
print("PACKAGING COMPLETE")
print(f"{'='*60}")
for pipeline in PIPELINES:
    if pipeline in all_pipelines:
        res = all_pipelines[pipeline]
        total_time = sum(r["time_sec"] for r in res)
        avg_graph = sum(r["graph_chunks"] for r in res) / len(res)
        avg_vector = sum(r["vector_chunks"] for r in res) / len(res)
        print(f"\n{pipeline} ({label_map[pipeline]}):")
        print(f"  Questions: {len(res)}")
        print(f"  Total time: {total_time:.1f}s")
        print(f"  Avg graph chunks: {avg_graph:.1f}")
        print(f"  Avg vector chunks: {avg_vector:.1f}")

print(f"\nBlind scoring file: {score_path}")
print(f"Ground truth file: {key_path}")

# Print all answers side-by-side for quick comparison
print(f"\n{'='*60}")
print("SIDE-BY-SIDE COMPARISON (first 150 chars per answer)")
print(f"{'='*60}")

for i, qid in enumerate(sorted(set(r["id"] for pipe in all_pipelines.values() for r in pipe))):
    print(f"\n--- {qid} ---")
    print(f"GT: {GROUND_TRUTH.get(qid, 'N/A')[:150]}")
    for pipeline in PIPELINES:
        if pipeline in all_pipelines:
            ans = next((r["answer"] for r in all_pipelines[pipeline] if r["id"] == qid), "N/A")
            print(f"[{pipeline[:6]}] {ans[:150]}")
