#!/usr/bin/env python3
"""Build golden KuzuDB + ChromaDB directly from synthetic document ground truth.
No extraction quality issues — architecture comparison only."""
import json, os, re, shutil
import kuzu, chromadb
from sentence_transformers import SentenceTransformer

KUZU_DIR = "/home/joedpogi/.hermes/baseline/kuzudb_ablation_db"
CHROMA_DIR = "/home/joedpogi/.hermes/baseline/chromadb_ablation_db"
SYNTHETIC_DIR = "/home/joedpogi/.hermes/baseline/synthetic"

# Clean slate
import os as _os
for d in [KUZU_DIR, CHROMA_DIR]:
    if _os.path.exists(d):
        if _os.path.isdir(d):
            shutil.rmtree(d)
        else:
            _os.remove(d)
# Also clean old single-file DB
old_kuzu = "/home/joedpogi/.hermes/baseline/kuzudb_ablation"
if _os.path.exists(old_kuzu):
    _os.remove(old_kuzu)
old_chroma = "/home/joedpogi/.hermes/baseline/chromadb_ablation"
if _os.path.exists(old_chroma):
    if _os.path.isdir(old_chroma):
        shutil.rmtree(old_chroma)
    else:
        _os.remove(old_chroma)

db = kuzu.Database(KUZU_DIR)
conn = kuzu.Connection(db)

def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"')[:300] + '"'

# ── Schema ──
SCHEMA = [
    "CREATE NODE TABLE Service(name STRING, processing_time STRING, description STRING, effective_date STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE Requirement(name STRING, description STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE Fee(name STRING, amount DOUBLE, currency STRING, category STRING, effective_date STRING, repeal_date STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE Office(name STRING, department STRING, address STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE Legislation(name STRING, ordinance_number STRING, enacted_date STRING, effective_date STRING, description STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE Penalty(name STRING, amount DOUBLE, offense_level STRING, description STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE ZoningClassification(name STRING, zone_code STRING, description STRING, PRIMARY KEY(name))",
    "CREATE NODE TABLE Zettel(name STRING, zettel_type STRING, content STRING, PRIMARY KEY(name))",
    "CREATE REL TABLE REQUIRES(FROM Service TO Requirement)",
    "CREATE REL TABLE SETS_FEE(FROM Service TO Fee)",
    "CREATE REL TABLE HAS_ZETTEL(FROM Service TO Zettel)",
    "CREATE REL TABLE ISSUES(FROM Office TO Service)",
    "CREATE REL TABLE SUPERSEDES(FROM Legislation TO Legislation, effective_date STRING)",
    "CREATE REL TABLE CLASSIFIED_AS(FROM ZoningClassification TO Zettel)",
    "CREATE REL TABLE IMPOSES(FROM Legislation TO Penalty)",
]
for s in SCHEMA:
    try:
        conn.execute(s)
    except Exception as e:
        print(f"Schema: {e}")

# ── Golden Data ──
# Services
services = [
    ("Building Permit Application", "Varies by complexity", "Building permit for construction", "2024-07-01"),
    ("Barangay Clearance", "1 working day", "Clearance from barangay for various purposes", "2015-07-01"),
    ("Sanitary Permit", "2 working days", "Health and sanitation permit for establishments", "2015-07-01"),
    ("Tricycle Franchise (MTOP)", "5 working days", "Motorized Tricycle Operator's Permit", "2019-12-01"),
    ("Zoning Clearance", "3 working days", "Zoning/Locational Clearance for building permit", "2016-10-15"),
    ("Business Permit Application", "Varies", "Mayor's Permit / Business Permit", "2015-07-01"),
]
for s in services:
    conn.execute(f"CREATE (s:Service {{name: {q(s[0])}, processing_time: {q(s[1])}, description: {q(s[2])}, effective_date: {q(s[3])}}})")

# Requirements
reqs = [
    # Building Permit
    ("Zoning Clearance Requirement", "Zoning Clearance from CPDO required before Building Permit per Ordinance 2016-031"),
    ("Barangay Clearance - Building Permit", "Barangay Clearance for Building Permit purpose"),
    # Tricycle Franchise
    ("MTOP Application Form", "Duly accomplished MTOP application form from CTTMO"),
    ("TODA Membership Certificate", "Certificate from accredited Tricycle Operators and Drivers Association"),
    ("LTO Certificate of Registration", "LTO Official Receipt and Certificate of Registration of tricycle unit"),
    ("LTO Driver's License", "Valid Professional Driver's License with tricycle restriction"),
    ("Barangay Clearance - Tricycle", "Barangay Clearance from Punong Barangay where applicant resides"),
    ("NBI Clearance", "Valid NBI Clearance issued within last 6 months"),
    ("Police Clearance", "Police Clearance from Naga City Police Office"),
    ("Drug Test Result", "Drug test from DOH-accredited center, valid for 1 year"),
    ("Medical Certificate", "Medical certificate from City Health Office"),
    ("2x2 ID Photos", "Two recent 2x2 ID photos with white background"),
    ("Franchise Fee Payment Proof", "Proof of payment of PHP 500.00 franchise fee"),
]
for r in reqs:
    conn.execute(f"CREATE (r:Requirement {{name: {q(r[0])}, description: {q(r[1])}}})")

# Connect Building Permit ← Requirements
conn.execute(f"MATCH (s:Service), (r:Requirement) WHERE s.name = 'Building Permit Application' AND r.name = 'Zoning Clearance Requirement' CREATE (s)-[:REQUIRES]->(r)")
conn.execute(f"MATCH (s:Service), (r:Requirement) WHERE s.name = 'Building Permit Application' AND r.name = 'Barangay Clearance - Building Permit' CREATE (s)-[:REQUIRES]->(r)")

# Connect Tricycle ← Requirements
for rname in ["MTOP Application Form","TODA Membership Certificate","LTO Certificate of Registration","LTO Driver's License","Barangay Clearance - Tricycle","NBI Clearance","Police Clearance","Drug Test Result","Medical Certificate","2x2 ID Photos","Franchise Fee Payment Proof"]:
    conn.execute(f"MATCH (s:Service), (r:Requirement) WHERE s.name = 'Tricycle Franchise (MTOP)' AND r.name = {q(rname)} CREATE (s)-[:REQUIRES]->(r)")

# Fees
fees = [
    # Building Permit fees (current — Ord 2024-112)
    ("BP Residential ≤100sqm Base", 2500.00, "Building Permit", "2024-07-01", None),
    ("BP Residential 101-200sqm Base", 4000.00, "Building Permit", "2024-07-01", None),
    ("BP Residential >200sqm Base", 6000.00, "Building Permit", "2024-07-01", None),
    ("BP Fire Code Fee ≤200sqm", 300.00, "Fire Code", "2018-03-01", None),
    ("BP Fire Code Fee >200sqm", 500.00, "Fire Code", "2018-03-01", None),
    ("BP Electrical Fee ≤200sqm", 250.00, "Electrical", "2024-07-01", None),
    ("BP Electrical Fee >200sqm", 400.00, "Electrical", "2024-07-01", None),
    # Building Permit fees (historical)
    ("BP Flat Rate 2015", 1800.00, "Building Permit", "2015-07-01", "2018-03-01"),
    ("BP ≤100sqm Base 2018", 2000.00, "Building Permit", "2018-03-01", "2024-07-01"),
    ("BP 101-200sqm Base 2018", 3500.00, "Building Permit", "2018-03-01", "2024-07-01"),
    # Barangay Clearance fees
    ("Barangay Clearance - Business Permit (New)", 150.00, "Barangay Clearance", "2015-07-01", None),
    ("Barangay Clearance - Business Permit (Renewal)", 100.00, "Barangay Clearance", "2015-07-01", None),
    ("Barangay Clearance - Building Permit", 50.00, "Barangay Clearance", "2015-07-01", None),
    ("Barangay Clearance - Tricycle Franchise", 50.00, "Barangay Clearance", "2015-07-01", None),
    ("Barangay Clearance - General Purpose", 75.00, "Barangay Clearance", "2015-07-01", None),
    # Sanitary Permit fees
    ("Sanitary Permit - Food Service (Current)", 300.00, "Sanitary Permit", "2022-06-01", None),
    ("Sanitary Permit - Food Service (Pre-2022)", 200.00, "Sanitary Permit", "2015-07-01", "2022-06-01"),
    ("Sanitary Permit - Food Manufacturing", 500.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - Wet Market Stall", 150.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - Dry Market Stall", 100.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - Barbershop/Salon/Spa", 250.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - Hospital/Clinic", 1000.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - School", 500.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - Hotel/Inn", 800.00, "Sanitary Permit", "2015-07-01", None),
    ("Sanitary Permit - Other", 300.00, "Sanitary Permit", "2015-07-01", None),
    # Tricycle fees
    ("Tricycle Franchise Fee", 500.00, "Tricycle Franchise", "2019-12-01", None),
    # Zoning
    ("Zoning Clearance Fee", 200.00, "Zoning Clearance", "2016-10-15", None),
    # Mayor's Permit penalty
    ("Mayor's Permit Non-Posting Fine", 500.00, "Penalty", "2015-07-01", None),
]
for f in fees:
    repeal = "NULL" if f[4] is None else q(f[4])
    conn.execute(f"CREATE (f:Fee {{name: {q(f[0])}, amount: {f[1]}, currency: 'PHP', category: {q(f[2])}, effective_date: {q(f[3])}, repeal_date: {repeal}}})")

# Connect Services → Fees
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Building Permit Application' AND f.name = 'BP Residential ≤100sqm Base' CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Building Permit Application' AND f.name = 'BP Residential 101-200sqm Base' CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Building Permit Application' AND f.name = 'BP Fire Code Fee ≤200sqm' CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Building Permit Application' AND f.name = 'BP Electrical Fee ≤200sqm' CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Building Permit Application' AND f.name = 'BP Fire Code Fee >200sqm' CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Building Permit Application' AND f.name = 'BP Electrical Fee >200sqm' CREATE (s)-[:SETS_FEE]->(f)")
for bc_fee in ["Barangay Clearance - Business Permit (New)","Barangay Clearance - Business Permit (Renewal)","Barangay Clearance - Building Permit","Barangay Clearance - Tricycle Franchise","Barangay Clearance - General Purpose"]:
    conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Barangay Clearance' AND f.name = {q(bc_fee)} CREATE (s)-[:SETS_FEE]->(f)")
for sp_fee in ["Sanitary Permit - Food Service (Current)","Sanitary Permit - Food Manufacturing","Sanitary Permit - Wet Market Stall","Sanitary Permit - Dry Market Stall","Sanitary Permit - Barbershop/Salon/Spa","Sanitary Permit - Hospital/Clinic","Sanitary Permit - School","Sanitary Permit - Hotel/Inn","Sanitary Permit - Other"]:
    conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Sanitary Permit' AND f.name = {q(sp_fee)} CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Tricycle Franchise (MTOP)' AND f.name = 'Tricycle Franchise Fee' CREATE (s)-[:SETS_FEE]->(f)")
conn.execute(f"MATCH (s:Service), (f:Fee) WHERE s.name = 'Zoning Clearance' AND f.name = 'Zoning Clearance Fee' CREATE (s)-[:SETS_FEE]->(f)")

# Offices
offices = [
    ("CTMO / Office of the Building Official", "Building Official", "City Hall Complex, Naga City"),
    ("CPDO (City Planning and Development Office)", "CPDO", "Rm. 208, City Hall Complex, Naga City"),
    ("Barangay Hall", "Barangay", "Respective Barangay Hall"),
    ("City Health Office (CHO)", "CHO", "J. Miranda Avenue, Concepcion Pequeña, Naga City"),
    ("CTTMO (City Transportation and Traffic Management Office)", "CTTMO", "City Hall Complex, Naga City"),
    ("NCCDO (Naga City Cooperatives Development Office)", "NCCDO", "City Hall Complex, Naga City"),
    ("City Treasurer's Office", "Treasury", "City Hall Complex, Naga City"),
]
for o in offices:
    conn.execute(f"CREATE (o:Office {{name: {q(o[0])}, department: {q(o[1])}, address: {q(o[2])}}})")

# ISSUES edges
conn.execute(f"MATCH (o:Office), (s:Service) WHERE o.name = 'CTMO / Office of the Building Official' AND s.name = 'Building Permit Application' CREATE (o)-[:ISSUES]->(s)")
conn.execute(f"MATCH (o:Office), (s:Service) WHERE o.name = 'Barangay Hall' AND s.name = 'Barangay Clearance' CREATE (o)-[:ISSUES]->(s)")
conn.execute(f"MATCH (o:Office), (s:Service) WHERE o.name = 'City Health Office (CHO)' AND s.name = 'Sanitary Permit' CREATE (o)-[:ISSUES]->(s)")
conn.execute(f"MATCH (o:Office), (s:Service) WHERE o.name = 'CTTMO (City Transportation and Traffic Management Office)' AND s.name = 'Tricycle Franchise (MTOP)' CREATE (o)-[:ISSUES]->(s)")
conn.execute(f"MATCH (o:Office), (s:Service) WHERE o.name = 'CPDO (City Planning and Development Office)' AND s.name = 'Zoning Clearance' CREATE (o)-[:ISSUES]->(s)")

# Legislation
legislation = [
    ("Ordinance No. 2015-023", "2015-023", "2015-06-15", "2015-07-01", "Revenue Code of Naga City"),
    ("Ordinance No. 2018-045", "2018-045", "2018-02-10", "2018-03-01", "Amended Section 24 — tiered BP fees"),
    ("Ordinance No. 2022-089", "2022-089", "2022-05-05", "2022-06-01", "Increased Sanitary Permit food service fee from PHP 200 to PHP 300"),
    ("Ordinance No. 2024-112", "2024-112", "2024-06-10", "2024-07-01", "Current BP fee schedule with Fire and Electrical fees"),
    ("Ordinance No. 2016-031", "2016-031", "2016-09-20", "2016-10-15", "Comprehensive Zoning Ordinance of Naga City"),
    ("Ordinance No. 2019-072", "2019-072", "2019-11-12", "2019-12-01", "Tricycle Franchise Regulatory Framework"),
]
for l in legislation:
    conn.execute(f"CREATE (l:Legislation {{name: {q(l[0])}, ordinance_number: {q(l[1])}, enacted_date: {q(l[2])}, effective_date: {q(l[3])}, description: {q(l[4])}}})")

# SUPERSEDES edges
conn.execute(f"MATCH (a:Legislation), (b:Legislation) WHERE a.name = 'Ordinance No. 2018-045' AND b.name = 'Ordinance No. 2015-023' CREATE (a)-[:SUPERSEDES]->(b)")
conn.execute(f"MATCH (a:Legislation), (b:Legislation) WHERE a.name = 'Ordinance No. 2024-112' AND b.name = 'Ordinance No. 2018-045' CREATE (a)-[:SUPERSEDES]->(b)")

# Zoning Classifications
zones = [
    ("R-1 Residential Zone", "R-1", "Residential — single-detached dwellings, duplex, home occupation, parks"),
    ("C-2 Commercial Zone", "C-2", "Commercial — retail, restaurants, banks, offices, hotels"),
    ("I-1 Industrial Zone", "I-1", "Industrial — light manufacturing, warehousing, food processing"),
]
for z in zones:
    conn.execute(f"CREATE (z:ZoningClassification {{name: {q(z[0])}, zone_code: {q(z[1])}, description: {q(z[2])}}})")

# Penalties
penalties = [
    ("Tricycle 1st Offense", 1000.00, "1st", "Fine of PHP 1,000.00 and 3 days impoundment"),
    ("Tricycle 2nd Offense", 2500.00, "2nd", "Fine of PHP 2,500.00 and 7 days impoundment"),
    ("Tricycle 3rd Offense", 5000.00, "3rd", "Fine of PHP 5,000.00 and franchise revocation for 1 year"),
]
for p in penalties:
    conn.execute(f"CREATE (p:Penalty {{name: {q(p[0])}, amount: {p[1]}, offense_level: {q(p[2])}, description: {q(p[3])}}})")

# Zettels
zettels = [
    ("Zettel-BP-Tiers", "FEE_STRUCTURE", "Building Permit residential tiers (Ord 2024-112): ≤100sqm = PHP 2,500 base + PHP 300 fire + PHP 250 electrical = PHP 3,050 total; 101-200sqm = PHP 4,000 + PHP 300 + PHP 250 = PHP 4,550; >200sqm = PHP 6,000 + PHP 500 + PHP 400 = PHP 6,900"),
    ("Zettel-BP-History", "FEE_STRUCTURE", "BP fee history: 2015 flat PHP 1,800 → 2018 tiered PHP 2,000-3,500 + PHP 300 fire → 2024 current PHP 2,500-6,000 + fire + electrical"),
    ("Zettel-BC-Fees", "FEE_STRUCTURE", "Barangay Clearance fees: Business Permit new PHP 150, renewal PHP 100, Building Permit PHP 50, Tricycle PHP 50, General PHP 75"),
    ("Zettel-SP-Fees", "FEE_STRUCTURE", "Sanitary Permit fees: Food service PHP 300, Manufacturing PHP 500, Wet market PHP 150, Dry market PHP 100, Salon PHP 250, Hospital PHP 1,000, School PHP 500, Hotel PHP 800"),
    ("Zettel-Trike-Reqs", "PROCEDURAL_REQUIREMENT", "Tricycle Franchise requirements: 11 items — MTOP form, TODA cert, LTO reg, LTO license, Bgy Clearance (PHP 50), NBI, Police, Drug test, Medical, 2x2 photos, Fee payment (PHP 500)"),
    ("Zettel-Zoning-Conds", "REGULATION_CLAUSE", "R-1 conditional uses: sari-sari store ≤15sqm, schools (elementary), clinics (max 4 rooms), bakeries (≤30sqm). All require Locational Clearance."),
]
for z in zettels:
    conn.execute(f"CREATE (z:Zettel {{name: {q(z[0])}, zettel_type: {q(z[1])}, content: {q(z[2])}}})")

# HAS_ZETTEL edges
conn.execute(f"MATCH (s:Service), (z:Zettel) WHERE s.name = 'Building Permit Application' AND z.name = 'Zettel-BP-Tiers' CREATE (s)-[:HAS_ZETTEL]->(z)")
conn.execute(f"MATCH (s:Service), (z:Zettel) WHERE s.name = 'Building Permit Application' AND z.name = 'Zettel-BP-History' CREATE (s)-[:HAS_ZETTEL]->(z)")
conn.execute(f"MATCH (s:Service), (z:Zettel) WHERE s.name = 'Barangay Clearance' AND z.name = 'Zettel-BC-Fees' CREATE (s)-[:HAS_ZETTEL]->(z)")
conn.execute(f"MATCH (s:Service), (z:Zettel) WHERE s.name = 'Sanitary Permit' AND z.name = 'Zettel-SP-Fees' CREATE (s)-[:HAS_ZETTEL]->(z)")
conn.execute(f"MATCH (s:Service), (z:Zettel) WHERE s.name = 'Tricycle Franchise (MTOP)' AND z.name = 'Zettel-Trike-Reqs' CREATE (s)-[:HAS_ZETTEL]->(z)")

# Count
for t in ["Service","Requirement","Fee","Office","Legislation","Penalty","ZoningClassification","Zettel"]:
    r = conn.execute(f"MATCH (n:{t}) RETURN count(n) as c")
    if r.has_next():
        print(f"{t}: {r.get_next()[0]}")

print(f"\nGolden graph built: {KUZU_DIR}")

# ── ChromaDB Vector Index ──
print(f"\nBuilding ChromaDB vector index...")
embedder = SentenceTransformer("BAAI/bge-small-en-v1.5")
chroma = chromadb.PersistentClient(path=CHROMA_DIR)
try:
    chroma.delete_collection("naga_ablation")
except:
    pass
collection = chroma.create_collection("naga_ablation")

DOCS = {
    "naga_revenue_code": f"{SYNTHETIC_DIR}/naga_revenue_code.md",
    "naga_zoning_ordinance": f"{SYNTHETIC_DIR}/naga_zoning_ordinance.md",
    "naga_tricycle_franchise": f"{SYNTHETIC_DIR}/naga_tricycle_franchise.md",
    "naga_amendment_chain": f"{SYNTHETIC_DIR}/naga_amendment_chain.md",
}

chunk_id = 0
for name, path in DOCS.items():
    with open(path) as f:
        text = f.read()
    # Chunk by paragraphs
    paras = text.split("\n\n")
    current_chunk = ""
    for para in paras:
        if len(current_chunk) + len(para) > 800 and current_chunk:
            chunk_text = f"[{name}] {current_chunk.strip()}"
            emb = embedder.encode([chunk_text])[0].tolist()
            collection.add(documents=[chunk_text], embeddings=[emb], ids=[f"chunk_{chunk_id}"], metadatas=[{"source": name}])
            chunk_id += 1
            current_chunk = para
        else:
            current_chunk += "\n\n" + para if current_chunk else para
    if current_chunk.strip():
        chunk_text = f"[{name}] {current_chunk.strip()}"
        emb = embedder.encode([chunk_text])[0].tolist()
        collection.add(documents=[chunk_text], embeddings=[emb], ids=[f"chunk_{chunk_id}"], metadatas=[{"source": name}])
        chunk_id += 1

print(f"Vector DB: {chunk_id} chunks in 'naga_ablation'")
print("\n=== GOLDEN BUILD COMPLETE ===")
