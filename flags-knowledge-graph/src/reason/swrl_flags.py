from owlready2 import get_ontology, Imp, get_namespace
from rdflib import Graph, Namespace, URIRef, RDF, RDFS, OWL
import os

# ----------------------------
# Paths
# ----------------------------
INPUT_GRAPH  = "kg_artifacts/initial_graph.ttl"
OUTPUT_GRAPH = "kg_artifacts/swrl_inferred.ttl"

FLAGS  = Namespace("http://flags-kg.org/ontology#")
FLAGS_R = Namespace("http://flags-kg.org/resource/")

# ----------------------------
# SWRL Rule (documented):
# Country(?c) ^ hasFlag(?c, ?f) ^ locatedIn(?c, ?continent) -> FlaggedCountry(?c)
#
# Simpler horn rule with 2 conditions (as required by lab):
# Country(?c) ^ hasFlag(?c, ?f) -> FlaggedCountry(?c)
# ----------------------------
SWRL_RULE = "Country(?c), hasFlag(?c, ?f) -> FlaggedCountry(?c)"

print("=== Règle SWRL sur le KB des drapeaux ===")
print(f"  Règle : {SWRL_RULE}")
print(f"  Signification : Tout pays qui possède un drapeau est classifié comme FlaggedCountry")

# ----------------------------
# Apply rule with rdflib (manual SWRL application)
# ----------------------------
print("\n=== Chargement du graphe ===")
g = Graph()
g.parse(INPUT_GRAPH, format="turtle")
print(f"  {len(g)} triplets chargés")

# Count before
countries = list(g.subjects(RDF.type, FLAGS.Country))
print(f"  Pays (Country) : {len(countries)}")

# Apply rule: Country(?c) ^ hasFlag(?c, ?f) -> FlaggedCountry(?c)
print("\n=== Application de la règle ===")
flagged = []
for country in countries:
    flags = list(g.objects(country, FLAGS.hasFlag))
    if flags:
        g.add((country, RDF.type, FLAGS.FlaggedCountry))
        name = str(country).split("/")[-1].replace("_", " ")
        flagged.append((name, len(flags)))

# Sort and display
flagged.sort(key=lambda x: x[0])
print(f"  FlaggedCountry inférés : {len(flagged)}")
print("\n  Exemples (premiers 10) :")
for name, n_flags in flagged[:10]:
    print(f"    {name} ({n_flags} drapeau(x))")

# Countries WITHOUT flag
unflagged = [c for c in countries if (c, RDF.type, FLAGS.FlaggedCountry) not in g]
print(f"\n  Pays SANS drapeau (non inférés) : {len(unflagged)}")

# ----------------------------
# Save inferred graph
# ----------------------------
os.makedirs("kg_artifacts", exist_ok=True)
g.serialize(destination=OUTPUT_GRAPH, format="turtle")

print(f"\n=== Résumé ===")
print(f"  Règle SWRL    : {SWRL_RULE}")
print(f"  Pays total    : {len(countries)}")
print(f"  FlaggedCountry: {len(flagged)}")
print(f"  Graphe sauvé  : {OUTPUT_GRAPH}")

# ----------------------------
# Comparison with embedding (Section 8 of Lab 3)
# ----------------------------
print(f"""
=== Comparaison rule-based vs embedding (Lab 3 Section 8) ===
Règle SWRL : Country(?c) ^ hasFlag(?c, ?f) -> FlaggedCountry(?c)
  → Inférence exacte, déterministe, 100% précision sur les données connues

Embedding équivalent (TransE) :
  → vector(hasFlag) peut être utilisé pour prédire des liens manquants
  → Moins précis mais généralise à des entités non vues
  → MRR obtenu : 0.0080 (Hits@10 : 0.0394) sur 20k triplets
  → Faible performance due à la taille réduite du sous-ensemble (20k/122k)
""")
