import random
import os
from rdflib import Graph, URIRef

# ----------------------------
# Paths
# ----------------------------
INPUT_NT   = "kg_artifacts/expanded.nt"
OUTPUT_DIR = "data/kge"

random.seed(42)

# ----------------------------
# Load graph
# ----------------------------
print("1. Chargement du graphe expansé...")
g = Graph()
g.parse(INPUT_NT, format="nt")
print(f"   {len(g)} triplets chargés")

# ----------------------------
# Clean triples
# ----------------------------
print("\n2. Nettoyage des triplets...")

def is_valid_triple(s, p, o):
    # Keep only URI-URI-URI triples (no literals for KGE)
    if not isinstance(s, URIRef) or not isinstance(p, URIRef) or not isinstance(o, URIRef):
        return False
    # Remove triples with blank nodes or invalid URIs
    for term in [str(s), str(p), str(o)]:
        if not term.startswith("http"):
            return False
        if " " in term:
            return False
    return True

triples = []
seen = set()
for s, p, o in g:
    if not is_valid_triple(s, p, o):
        continue
    triple = (str(s), str(p), str(o))
    if triple not in seen:
        seen.add(triple)
        triples.append(triple)

print(f"   {len(triples)} triplets valides après nettoyage")

# ----------------------------
# Check entity/relation counts
# ----------------------------
entities  = set(t[0] for t in triples) | set(t[2] for t in triples)
relations = set(t[1] for t in triples)
print(f"   Entités   : {len(entities)}")
print(f"   Relations : {len(relations)}")

# ----------------------------
# Ensure no entity appears only in valid/test
# ----------------------------
print("\n3. Création des splits (80/10/10)...")
random.shuffle(triples)

# Collect entities that appear in train
n = len(triples)
n_train = int(n * 0.8)
n_valid = int(n * 0.1)

train = triples[:n_train]
valid = triples[n_train:n_train + n_valid]
test  = triples[n_train + n_valid:]

# Ensure all valid/test entities appear in train
train_entities = set(t[0] for t in train) | set(t[2] for t in train)

safe_valid, overflow = [], []
for t in valid:
    if t[0] in train_entities and t[2] in train_entities:
        safe_valid.append(t)
    else:
        overflow.append(t)

safe_test = []
for t in test:
    if t[0] in train_entities and t[2] in train_entities:
        safe_test.append(t)
    else:
        overflow.append(t)

# Add overflow back to train
train += overflow

print(f"   Train : {len(train)} triplets")
print(f"   Valid : {len(safe_valid)} triplets")
print(f"   Test  : {len(safe_test)} triplets")

# ----------------------------
# Save
# ----------------------------
os.makedirs(OUTPUT_DIR, exist_ok=True)

def save_split(triples, path):
    with open(path, "w", encoding="utf-8") as f:
        for s, p, o in triples:
            f.write(f"{s}\t{p}\t{o}\n")

save_split(train,      f"{OUTPUT_DIR}/train.txt")
save_split(safe_valid, f"{OUTPUT_DIR}/valid.txt")
save_split(safe_test,  f"{OUTPUT_DIR}/test.txt")

print(f"\n   Fichiers sauvegardés dans {OUTPUT_DIR}/")
print("   train.txt, valid.txt, test.txt")
