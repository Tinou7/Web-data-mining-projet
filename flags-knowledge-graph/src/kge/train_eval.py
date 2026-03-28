import os
import torch
import numpy as np
import matplotlib.pyplot as plt
from pykeen.pipeline import pipeline
from pykeen.triples import TriplesFactory

# ----------------------------
# Paths
# ----------------------------
DATA_DIR   = "data/kge"
OUTPUT_DIR = "data/kge/results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ----------------------------
# Subset size for size-sensitivity analysis (Lab 3 section 5.2)
# Change to 50_000 or None (full) to run other sizes
# Full dataset crashed on laptop — documented in report
# ----------------------------
SUBSET_SIZE = 20_000

# ----------------------------
# Load triples
# ----------------------------
print("1. Chargement des splits...")

# Load full train to get entity/relation mappings
tf_full = TriplesFactory.from_path(f"{DATA_DIR}/train.txt")
tf_valid = TriplesFactory.from_path(
    f"{DATA_DIR}/valid.txt",
    entity_to_id=tf_full.entity_to_id,
    relation_to_id=tf_full.relation_to_id,
)
tf_test = TriplesFactory.from_path(
    f"{DATA_DIR}/test.txt",
    entity_to_id=tf_full.entity_to_id,
    relation_to_id=tf_full.relation_to_id,
)

if SUBSET_SIZE and tf_full.num_triples > SUBSET_SIZE:
    idx = torch.randperm(tf_full.num_triples)[:SUBSET_SIZE]
    subset_mapped = tf_full.mapped_triples[idx]
    tf_train = TriplesFactory(
        mapped_triples=subset_mapped,
        entity_to_id=tf_full.entity_to_id,
        relation_to_id=tf_full.relation_to_id,
    )
    print(f"   Sous-ensemble {SUBSET_SIZE} triplets (analyse taille)")
else:
    tf_train = tf_full

print(f"   Train: {tf_train.num_triples} | Valid: {tf_valid.num_triples} | Test: {tf_test.num_triples}")
print(f"   Entités: {tf_train.num_entities} | Relations: {tf_train.num_relations}")

# ----------------------------
# Training config
# ----------------------------
EMBEDDING_DIM = 50
NUM_EPOCHS    = 30
BATCH_SIZE    = 256
LR            = 0.01

print(f"\nConfig: dim={EMBEDDING_DIM}, epochs={NUM_EPOCHS}, batch={BATCH_SIZE}, lr={LR}")

# ----------------------------
# Train TransE
# ----------------------------
print("\n2. Entraînement TransE...")
result_transe = pipeline(
    training=tf_train,
    validation=tf_valid,
    testing=tf_test,
    model="TransE",
    model_kwargs={"embedding_dim": EMBEDDING_DIM},
    optimizer="Adam",
    optimizer_kwargs={"lr": LR},
    training_kwargs={"num_epochs": NUM_EPOCHS, "batch_size": BATCH_SIZE},
    evaluation_kwargs={"batch_size": BATCH_SIZE},
    random_seed=42,
    device="cpu",
)
result_transe.save_to_directory(f"{OUTPUT_DIR}/transe")

# ----------------------------
# Train DistMult
# ----------------------------
print("\n3. Entraînement DistMult...")
result_distmult = pipeline(
    training=tf_train,
    validation=tf_valid,
    testing=tf_test,
    model="DistMult",
    model_kwargs={"embedding_dim": EMBEDDING_DIM},
    optimizer="Adam",
    optimizer_kwargs={"lr": LR},
    training_kwargs={"num_epochs": NUM_EPOCHS, "batch_size": BATCH_SIZE},
    evaluation_kwargs={"batch_size": BATCH_SIZE},
    random_seed=42,
    device="cpu",
)
result_distmult.save_to_directory(f"{OUTPUT_DIR}/distmult")

# ----------------------------
# Print metrics
# ----------------------------
def print_metrics(name, result):
    m = result.metric_results.to_flat_dict()
    print(f"\n  [{name}]")
    for key in ["hits_at_1", "hits_at_3", "hits_at_10", "mean_reciprocal_rank"]:
        for k, v in m.items():
            if key in k.lower() and "both" in k.lower():
                print(f"    {k}: {v:.4f}")

print("\n=== Résultats Link Prediction ===")
print_metrics("TransE",   result_transe)
print_metrics("DistMult", result_distmult)

# ----------------------------
# t-SNE visualization
# ----------------------------
print("\n4. Visualisation t-SNE...")
try:
    from sklearn.manifold import TSNE

    # Get entity embeddings from best model
    model = result_transe.model
    embeddings = model.entity_representations[0](
        indices=None
    ).detach().cpu().numpy()

    # Sample 500 entities max for speed
    n_sample = min(500, len(embeddings))
    idx = np.random.choice(len(embeddings), n_sample, replace=False)
    sample_emb = embeddings[idx]

    tsne = TSNE(n_components=2, random_state=42, perplexity=30)
    coords = tsne.fit_transform(sample_emb)

    plt.figure(figsize=(10, 8))
    plt.scatter(coords[:, 0], coords[:, 1], alpha=0.5, s=10)
    plt.title("t-SNE des embeddings d'entités (TransE)")
    plt.xlabel("Dim 1")
    plt.ylabel("Dim 2")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/tsne_transe.png", dpi=150)
    plt.close()
    print(f"   t-SNE sauvegardé : {OUTPUT_DIR}/tsne_transe.png")

except Exception as e:
    print(f"   t-SNE échoué : {e}")

# ----------------------------
# Nearest neighbors
# ----------------------------
print("\n5. Voisins les plus proches (TransE)...")
try:
    from sklearn.metrics.pairwise import cosine_similarity

    entity_to_id = tf_train.entity_to_id
    id_to_entity = {v: k for k, v in entity_to_id.items()}

    # Pick a few interesting entities (countries)
    sample_names = ["http://www.wikidata.org/entity/Q142",   # France
                    "http://www.wikidata.org/entity/Q408",   # Australia
                    "http://www.wikidata.org/entity/Q17"]    # Japan

    for ent_uri in sample_names:
        if ent_uri not in entity_to_id:
            continue
        eid = entity_to_id[ent_uri]
        emb = embeddings[eid].reshape(1, -1)
        sims = cosine_similarity(emb, embeddings)[0]
        top5 = np.argsort(sims)[::-1][1:6]
        label = ent_uri.split("/")[-1]
        print(f"\n  Voisins de {label}:")
        for nid in top5:
            print(f"    {id_to_entity[nid].split('/')[-1]} (sim={sims[nid]:.3f})")

except Exception as e:
    print(f"   Nearest neighbors échoué : {e}")

print("\nTerminé. Résultats dans", OUTPUT_DIR)
