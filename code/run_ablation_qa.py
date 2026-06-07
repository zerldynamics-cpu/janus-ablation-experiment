#!/usr/bin/env python3
"""Ablation Experiment — Run all 3 pipelines (Vector-Only, Graph-Only, Janus V4) on 36 questions."""
import json, os, time, sys, re

# ── Paths ──
KUZU_DIR = "/home/joedpogi/.hermes/baseline/kuzudb_ablation_db"
CHROMA_DIR = "/home/joedpogi/.hermes/baseline/chromadb_ablation_db"
OUT_DIR = "/home/joedpogi/.hermes/baseline/answers/ablation"
os.makedirs(OUT_DIR, exist_ok=True)

# ── API Setup ──
key = None
with open(os.path.expanduser("~/.hermes/.env")) as f:
    for line in f:
        if "DEEP" in line and "SEEK" in line and "API" in line and "KEY" in line and not line.strip().startswith("#"):
            parts = line.strip().split("=", 1)
            if len(parts) == 2:
                key = parts[1].strip().strip('"').strip("'")
                break
from openai import OpenAI
llm = OpenAI(api_key=key, base_url="https://api.deepseek.com/v1")

# ── DB Setup ──
import kuzu, chromadb
from sentence_transformers import SentenceTransformer

db = kuzu.Database(KUZU_DIR)
conn = kuzu.Connection(db)
embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
chroma = chromadb.PersistentClient(path=CHROMA_DIR)
collection = chroma.get_collection("naga_ablation")

def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"')[:300] + '"'

# ── Synonym Map (from experiment design Appendix A) ──
SYN = {
    "Building Permit": ["building permit","bp","bldg permit","permit to construct","building permit application","konstruksyon permit","gawa bahay permit","permiso magpatayo"],
    "Barangay Clearance": ["barangay clearance","brgy clearance","bgy clearance","brgy cert","barangay business clearance","clearance sa barangay","certification"],
    "Business Permit": ["business permit","mayors permit","mayor's permit","bpl","business registration","business permit application","mayor's clearance","permit sa negosyo","business license","annual permit"],
    "Sanitary Permit": ["sanitary permit","health permit","sanitary clearance","health clearance","karinderya permit","food permit"],
    "Tricycle Franchise": ["tricycle franchise","MTOP","prangkisa ng trike","trike franchise","franchise","tricycle permit","operator's permit"],
    "Zoning Clearance": ["zoning clearance","locational clearance","zoning cert","land use clearance","zone clearance"],
    "Building Permit fee": ["bp fee","magkano bp","building fee","construction fee","bayad sa building"],
    # Colloquial zoning references
    "R-1 Residential Zone": ["r-1","residential zone","tindahan sa bahay","tindahan sa tabi ng bahay","sari-sari store","home occupation","bahay lang"],
}

def synonym_align(query):
    ql = query.lower()
    matched = []
    for canonical, variants in SYN.items():
        for v in variants:
            if v in ql:
                matched.append(canonical)
                break
    ts = {"hm":"how much","bgy":"barangay","brgy":"barangay","reqs":"requirements","po":None,"d2":"dito","n":"ng","s":"sa","pls":"please","magkano":"magkano","pano":"paano","saan":"saan","kelangan":"kailangan","lahat":"lahat"}
    words = [ts.get(w,w) for w in ql.split() if ts.get(w,w) is not None]
    return {"aligned":" ".join(words), "matched":list(set(matched))}

def classify(q):
    ql = q.lower()
    skw = {"magkano":0.3,"fee":0.3,"cost":0.25,"bayad":0.25,"requirements":0.3,"reqs":0.3,"kailangan":0.3,"paano":0.3,"steps":0.3,"hakbang":0.3,"sino":0.2,"saan":0.15,"ilan":0.15,"lahat":0.2,"dokumento":0.25,"penalty":0.3,"multa":0.3,"fine":0.3,"ordinansa":0.2}
    nkw = {"bakit":0.3,"why":0.3,"history":0.2,"kasaysayan":0.2,"explain":0.25,"ipaliwanag":0.25,"context":0.15,"layunin":0.3,"purpose":0.3}
    s = sum(w for kw,w in skw.items() if kw in ql)
    n = sum(w for kw,w in nkw.items() if kw in ql)
    s,n = min(s,1.0), min(n,1.0)
    if s==0 and n==0: s,n=0.5,0.5
    if s>=0.3 and n==0: s=max(s,0.7)
    is_fee_query = any(kw in ql for kw in ["magkano","fee","cost","bayad","halaga","presyo"])
    is_req_query = any(kw in ql for kw in ["requirements","reqs","kailangan","dokumento","ano","lahat"])
    return {"structural":s,"narrative":n,"is_fee":is_fee_query,"is_req":is_req_query}

# ── Retrieval Functions ──

def vector_retrieve(query, top_k=5):
    """ChromaDB semantic search only."""
    emb = embedder.encode([query])[0].tolist()
    results = collection.query(query_embeddings=[emb], n_results=top_k)
    chunks = []
    for doc in results.get("documents", [[]])[0]:
        chunks.append(f"[VECTOR] {doc}")
    return chunks

ZETTEL_TYPE_PRIORITY = {
    "FEE_STRUCTURE": 10,
    "PENALTY_MATRIX": 9,
    "PROCEDURAL_REQUIREMENT": 5,
    "PROCESSING_STEP": 4,
    "REGULATION_CLAUSE": 3,
    "PROCUREMENT_RESULT": 8,
}

def graph_retrieve(matched_entities, intent):
    """KuzuDB graph traversal only. CONTAINS + typed MATCH + Zettel filter."""
    results = []
    is_fee = intent.get("is_fee", False)
    
    for entity in matched_entities:
        eq = q(entity)
        
        # Service lookup
        try:
            r = conn.execute(f"MATCH (s:Service) WHERE s.name CONTAINS {eq} RETURN s.name, s.processing_time, s.description LIMIT 5")
            while r.has_next():
                row = r.get_next()
                results.append(("SERVICE", 10, f"SERVICE: {row[0]} | Processing: {row[1]} | {row[2]}"))
        except: pass
        
        # REQUIRES chain
        try:
            r = conn.execute(f"MATCH (s:Service)-[:REQUIRES]->(req) WHERE s.name CONTAINS {eq} RETURN s.name, req.name, labels(req) LIMIT 25")
            while r.has_next():
                row = r.get_next()
                results.append(("REQUIRES", 7, f"REQUIRES: {row[0]} -> [{row[2][0]}] {row[1]}"))
        except: pass
        
        # Fee lookup via SETS_FEE
        try:
            r = conn.execute(f"MATCH (s:Service)-[:SETS_FEE]->(f:Fee) WHERE s.name CONTAINS {eq} RETURN f.name, f.amount, f.category, f.effective_date LIMIT 20")
            while r.has_next():
                row = r.get_next()
                results.append(("FEE", 9 if is_fee else 5, f"FEE: {row[0]} — PHP {row[1]:,.2f} | Category: {row[2]} | Effective: {row[3]}"))
        except: pass
        
        # Zettels with type filter
        try:
            r = conn.execute(f"MATCH (s:Service)-[:HAS_ZETTEL]->(z:Zettel) WHERE s.name CONTAINS {eq} RETURN z.name, z.zettel_type, z.content LIMIT 20")
            while r.has_next():
                row = r.get_next()
                ztype = row[1] or "UNKNOWN"
                priority = ZETTEL_TYPE_PRIORITY.get(ztype, 1)
                # Boost fee/penalty zettels for fee queries, suppress procedural for fee queries
                if is_fee and ztype in ("FEE_STRUCTURE", "PENALTY_MATRIX"):
                    priority = 15
                elif is_fee and ztype == "PROCEDURAL_STEP":
                    priority = 2
                results.append(("ZETTEL", priority, f"ZETTEL [{ztype}]: {row[2]}"))
        except: pass
        
        # Legislation + SUPERSEDES chain
        try:
            r = conn.execute(f"MATCH (l:Legislation)-[:SUPERSEDES]->(prev:Legislation) WHERE l.name CONTAINS {eq} OR prev.name CONTAINS {eq} RETURN l.name, l.effective_date, prev.name, prev.effective_date LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(("SUPERSEDES", 8, f"SUPERSEDES: {row[0]} ({row[1]}) supersedes {row[2]} ({row[3]})"))
        except: pass
        
        # Zoning classifications
        try:
            r = conn.execute(f"MATCH (z:ZoningClassification) WHERE z.name CONTAINS {eq} OR z.zone_code CONTAINS {eq} RETURN z.name, z.zone_code, z.description LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(("ZONING", 6, f"ZONING: {row[0]} ({row[1]}) — {row[2]}"))
        except: pass
        
        # Penalties
        try:
            r = conn.execute(f"MATCH (p:Penalty) WHERE p.name CONTAINS {eq} RETURN p.name, p.amount, p.offense_level, p.description LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(("PENALTY", 7, f"PENALTY: {row[0]} — PHP {row[1]:,.2f} | {row[2]} | {row[3]}"))
        except: pass
        
        # Office lookup — ISSUES edge (FIX: was missing, caused H2/S5 failures)
        try:
            r = conn.execute(f"MATCH (o:Office)-[:ISSUES]->(s:Service) WHERE s.name CONTAINS {eq} OR o.name CONTAINS {eq} RETURN o.name, o.address, o.department, s.name LIMIT 10")
            while r.has_next():
                row = r.get_next()
                results.append(("OFFICE", 10, f"OFFICE: {row[0]} ({row[2]}) | Address: {row[1]} | Issues: {row[3]}"))
        except: pass
    
    # Sort by priority, deduplicate
    results.sort(key=lambda x: x[1], reverse=True)
    
    # FIX: Ensure ALL Fee and Penalty items appear before other content
    # Prevents fee nodes being dropped by context truncation (caused F5 failure)
    fee_items = [r for r in results if r[0] in ("FEE", "PENALTY")]
    other_items = [r for r in results if r[0] not in ("FEE", "PENALTY")]
    results = fee_items + other_items
    
    seen = set()
    unique = []
    for _, _, text in results:
        if text not in seen:
            seen.add(text)
            unique.append(text)
    
    return unique

# ── V4 Prompt ──
PROMPT_V4 = """Ikaw ay isang government assistant para sa Naga City. Sagutin ang tanong gamit LAMANG ang impormasyon mula sa ibinigay na context.

CONTEXT:
{context}

TANONG: {question}

MGA TAGUBILIN:
1. Kung may eksaktong impormasyon sa context — ibigay ito nang may kumpletong detalye, halaga, at citation.
2. Kung WALA sa context — sabihin nang tapat: "Wala pong nakasaad sa available documents tungkol dito." HUWAG manghula o mag-imbento.
3. Ang alam ko... Pero ang fee/specifics ay wala sa documents — gamitin itong pattern kapag partial lang ang info.
4. Kung ang tanong ay tungkol sa fees, ibigay ang eksaktong halaga mula sa context.
5. Gamitin ang Filipino o Taglish. Maging diretso at kapaki-pakinabang.

SAGOT:"""

# ── 36 Questions ──
QUESTIONS = [
    # Category A: Exact Fee Lookup (F1-F6)
    ("F1", "Magkano ang Building Permit fee para sa residential na 150 sq.m.?"),
    ("F2", "Magkano ang Barangay Clearance para sa bagong business permit?"),
    ("F3", "Magkano ang Sanitary Permit fee para sa restaurant?"),
    ("F4", "Magkano ang franchise fee ng tricycle?"),
    ("F5", "Lahat ng fees na nakalista para sa Tricycle Franchise, magkano total?"),
    ("F6", "Magkano ang Zoning Clearance fee?"),
    # Category B: Multi-Hop (M1-M4)
    ("M1", "Kung mag-aapply ako ng Building Permit, anong mga clearance ang kailangan ko muna kunin, at magkano lahat?"),
    ("M2", "Ano requirements ng Tricycle Franchise at saang opisina mag-aapply?"),
    ("M3", "Kung kukuha ako ng Building Permit, kailangan ko ba ng Barangay Clearance? Kung oo, magkano?"),
    ("M4", "Anong ordinansa ang nagtakda ng kasalukuyang Building Permit fee, at ano ang pinalitan nito?"),
    # Category C: Conceptual (C1-C4)
    ("C1", "Bakit kailangan ng Zoning Clearance bago mag-Building Permit?"),
    ("C2", "Ano ang purpose ng amendment ng Building Permit fees mula 2015 hanggang 2024?"),
    ("C3", "Bakit may iba't ibang zone classifications sa Naga City?"),
    ("C4", "Bakit may parusa ang hindi pag-post ng Mayor's Permit?"),
    # Category D: Temporal (T1-T4)
    ("T1", "Magkano ang Building Permit fee noong 2016?"),
    ("T2", "Magkano ang Building Permit fee noong 2020?"),
    ("T3", "Kailan nagbago ang Building Permit fee mula flat rate papuntang tiered?"),
    ("T4", "Ang Sanitary Permit fee para sa restaurant noong 2021 — magkano? At ngayon?"),
    # Category E: Synonym (S1-S6)
    ("S1", "hm po bgy clearance pang negosyo"),
    ("S2", "magkano bp fee 100 sqm"),
    ("S3", "pano kumuha ng mayor's permit"),
    ("S4", "kelangan ba ng sanitary permit ang karinderya?"),
    ("S5", "saan kukuha ng prangkisa ng trike"),
    ("S6", "pwede ba tindahan sa tabi ng bahay"),
    # Category F: Adversarial (A1-A4)
    ("A1", "May tax break ba ang senior citizen na may negosyo sa Naga City?"),
    ("A2", "Ano requirements ng Barangay Tanod appointment?"),
    ("A3", "Magkano ang permit para sa motorized boat sa Naga River?"),
    ("A4", "Saan magbabayad ng amilyar sa Naga City?"),
    # Category G: Aggregation (G1-G4)
    ("G1", "Ano LAHAT ng requirements para sa Building Permit?"),
    ("G2", "Ano ang mga zone classifications na nakalista sa zoning documents?"),
    ("G3", "Ano LAHAT ng penalties ng Tricycle Franchise violations?"),
    ("G4", "Ano LAHAT ng ordinansa na may kinalaman sa Building Permit fees?"),
    # Category H: Easy Baseline (H1-H4)
    ("H1", "Ano ang processing time ng Tricycle Franchise?"),
    ("H2", "Saan ini-issue ang Tricycle Franchise?"),
    ("H3", "Ilang sqm ang maximum para sa sari-sari store na pwede sa R-1 zone?"),
    ("H4", "Magkano ang Fire Code Fee sa Building Permit (current)?"),
]

# ── Run All 3 Pipelines ──
PIPELINES = ["vector_only", "graph_only", "janus_v4"]

for pipeline in PIPELINES:
    print(f"\n{'='*60}")
    print(f"PIPELINE: {pipeline}")
    print(f"{'='*60}")
    
    results = []
    
    for qid, question in QUESTIONS:
        t0 = time.time()
        al = synonym_align(question)
        it = classify(al["aligned"])
        
        ctx_parts = []
        g_count = 0
        v_count = 0
        
        if pipeline == "vector_only":
            # Vector only — ChromaDB top-5
            vres = vector_retrieve(al["aligned"], top_k=5)
            if vres:
                ctx_parts.append("[VECTOR_ONLY]\n" + "\n".join(vres))
                v_count = len(vres)
        
        elif pipeline == "graph_only":
            # Graph only — KuzuDB CONTAINS + typed MATCH
            gres = graph_retrieve(al["matched"], it)
            if gres:
                ctx_parts.append("[GRAPH_ONLY]\n" + "\n".join(gres[:15]))
                g_count = len(gres)
        
        elif pipeline == "janus_v4":
            # Janus V4 — graph-first, vector supplement
            if it["structural"] >= 0.3:
                gres = graph_retrieve(al["matched"], it)
                if gres:
                    ctx_parts.append("[GRAPH_VERIFIED]\n" + "\n".join(gres[:12]))
                    g_count = len(gres)
            if it["narrative"] >= 0.3 or it["structural"] <= 0.7:
                vres = vector_retrieve(al["aligned"], top_k=3)
                if vres:
                    ctx_parts.append("[VECTOR_SUPPLEMENTAL]\n" + "\n".join(vres))
                    v_count = len(vres)
        
        ctx = "\n".join(ctx_parts) if ctx_parts else "(No relevant information found in database)"
        
        prompt = PROMPT_V4.format(context=ctx[:3500], question=question)
        resp = llm.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
        )
        answer = resp.choices[0].message.content
        elapsed = time.time() - t0
        
        res = {
            "id": qid,
            "question": question,
            "answer": answer,
            "pipeline": pipeline,
            "intent": it,
            "graph_chunks": g_count,
            "vector_chunks": v_count,
            "time_sec": round(elapsed, 1),
        }
        results.append(res)
        print(f"  {qid}: S={it['structural']:.2f} N={it['narrative']:.2f} | G:{g_count} V:{v_count} | {elapsed:.1f}s")
        print(f"    {answer[:200]}")
    
    # Save
    out_path = os.path.join(OUT_DIR, f"{pipeline}_answers.json")
    with open(out_path, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Stats
    total_time = sum(r["time_sec"] for r in results)
    print(f"\n{pipeline} complete: {len(results)} questions, {total_time:.1f}s total")

print("\n=== ALL 3 PIPELINES COMPLETE ===")
print(f"Results in: {OUT_DIR}/")
