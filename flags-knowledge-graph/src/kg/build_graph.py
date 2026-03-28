import pandas as pd
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
from rdflib.namespace import SKOS
import re
import os

# ----------------------------
# Paths
# ----------------------------
INPUT_ENTITIES  = "data/extracted_knowledge.csv"
INPUT_RELATIONS = "data/extracted_relations.csv"
OUTPUT_ONTOLOGY = "kg_artifacts/ontology.ttl"
OUTPUT_GRAPH    = "kg_artifacts/initial_graph.ttl"

# ----------------------------
# Namespace
# ----------------------------
FLAGS = Namespace("http://flags-kg.org/ontology#")
FLAGS_R = Namespace("http://flags-kg.org/resource/")

# ----------------------------
# Helpers
# ----------------------------
def to_uri_slug(text: str) -> str:
    """Convert a string to a valid URI fragment."""
    slug = re.sub(r"[^\w]", "_", text.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug

def entity_uri(name: str) -> URIRef:
    return FLAGS_R[to_uri_slug(name)]

# ----------------------------
# Build Ontology
# ----------------------------
def build_ontology(g: Graph):
    """Define classes and properties for the flags domain."""
    # Classes
    for cls in ["Country", "Flag", "Continent", "Symbol", "Organization", "Date"]:
        g.add((FLAGS[cls], RDF.type, OWL.Class))
        g.add((FLAGS[cls], RDFS.label, Literal(cls, lang="en")))

    g.add((FLAGS["Country"],      RDFS.subClassOf, FLAGS["GeopoliticalEntity"]))
    g.add((FLAGS["GeopoliticalEntity"], RDF.type,  OWL.Class))

    # Object properties
    props = {
        "hasFlag":        ("GeopoliticalEntity", "Flag"),
        "hasSymbol":      ("Flag",               "Symbol"),
        "locatedIn":      ("Country",            "Continent"),
        "affiliatedWith": ("Organization",       "GeopoliticalEntity"),
        "adoptedIn":      ("Flag",               "Date"),
    }
    for prop, (domain, range_) in props.items():
        g.add((FLAGS[prop], RDF.type,        OWL.ObjectProperty))
        g.add((FLAGS[prop], RDFS.domain,     FLAGS[domain]))
        g.add((FLAGS[prop], RDFS.range,      FLAGS[range_]))
        g.add((FLAGS[prop], RDFS.label,      Literal(prop, lang="en")))

    # Datatype properties
    g.add((FLAGS["entityType"], RDF.type,    OWL.DatatypeProperty))
    g.add((FLAGS["sourceURL"],  RDF.type,    OWL.DatatypeProperty))
    g.add((FLAGS["sourceURL"],  RDFS.range,  XSD.anyURI))

# ----------------------------
# Map spaCy label → OWL class
# ----------------------------
LABEL_CLASS = {
    "GPE":    FLAGS["Country"],
    "ORG":    FLAGS["Organization"],
    "PERSON": FLAGS["Person"],
    "DATE":   FLAGS["Date"],
    "LOC":    FLAGS["GeopoliticalEntity"],
    "NORP":   FLAGS["Organization"],
    "WORK_OF_ART": FLAGS["Symbol"],
    "EVENT":  FLAGS["Symbol"],
}

# Map relation verbs → OWL properties
VERB_MAP = {
    "adopt":   FLAGS["adoptedIn"],
    "use":     FLAGS["hasSymbol"],
    "depict":  FLAGS["hasSymbol"],
    "locate":  FLAGS["locatedIn"],
    "form":    FLAGS["affiliatedWith"],
    "join":    FLAGS["affiliatedWith"],
    "become":  FLAGS["hasFlag"],
    "launch":  FLAGS["hasFlag"],
    "hang":    FLAGS["hasFlag"],
    "inspire": FLAGS["hasFlag"],
}

# ----------------------------
# Populate graph from CSV
# ----------------------------
def populate_entities(g: Graph, df: pd.DataFrame):
    added = 0
    for _, row in df.iterrows():
        entity = str(row["Entity"]).strip()
        label  = str(row["Label"]).strip()
        url    = str(row["Source_URL"]).strip()

        if not entity or entity.lower() == "nan":
            continue

        uri = entity_uri(entity)
        cls = LABEL_CLASS.get(label, FLAGS["Thing"])

        g.add((uri, RDF.type,         cls))
        g.add((uri, RDFS.label,       Literal(entity, lang="en")))
        g.add((uri, FLAGS["sourceURL"], Literal(url, datatype=XSD.anyURI)))

        # Countries automatically get a Flag node
        if label == "GPE":
            flag_uri = FLAGS_R[to_uri_slug(entity) + "_Flag"]
            g.add((flag_uri, RDF.type,   FLAGS["Flag"]))
            g.add((flag_uri, RDFS.label, Literal(f"Flag of {entity}", lang="en")))
            g.add((uri, FLAGS["hasFlag"], flag_uri))

        added += 1
    return added

def populate_relations(g: Graph, df: pd.DataFrame):
    added = 0
    for _, row in df.iterrows():
        subj = str(row["Sujet"]).strip()
        verb = str(row["Verbe"]).strip().lower()
        obj  = str(row["Objet"]).strip()

        if not subj or not obj or subj.lower() == "nan" or obj.lower() == "nan":
            continue

        # Only link if both subject and object look like named entities
        if len(subj) < 2 or len(obj) < 2:
            continue

        prop = None
        for key, uri in VERB_MAP.items():
            if key in verb:
                prop = uri
                break
        if prop is None:
            prop = FLAGS["relatedTo"]
            g.add((FLAGS["relatedTo"], RDF.type, OWL.ObjectProperty))

        g.add((entity_uri(subj), prop, entity_uri(obj)))
        added += 1
    return added

# ----------------------------
# Main
# ----------------------------
def main():
    os.makedirs("kg_artifacts", exist_ok=True)

    # 1. Build ontology
    print("1. Construction de l'ontologie...")
    g_onto = Graph()
    g_onto.bind("flags",  FLAGS)
    g_onto.bind("flagsr", FLAGS_R)
    g_onto.bind("owl",    OWL)
    g_onto.bind("rdfs",   RDFS)
    build_ontology(g_onto)
    g_onto.serialize(destination=OUTPUT_ONTOLOGY, format="turtle")
    print(f"   Ontologie sauvegardée : {OUTPUT_ONTOLOGY} ({len(g_onto)} triplets)")

    # 2. Build instance graph
    print("\n2. Construction du graphe d'instances...")
    g = Graph()
    g.bind("flags",  FLAGS)
    g.bind("flagsr", FLAGS_R)
    g.bind("owl",    OWL)
    g.bind("rdfs",   RDFS)

    # Import ontology triples
    for triple in g_onto:
        g.add(triple)

    df_entities  = pd.read_csv(INPUT_ENTITIES)
    df_relations = pd.read_csv(INPUT_RELATIONS)

    n_ent = populate_entities(g, df_entities)
    n_rel = populate_relations(g, df_relations)

    g.serialize(destination=OUTPUT_GRAPH, format="turtle")

    print(f"   Entités ajoutées   : {n_ent}")
    print(f"   Relations ajoutées : {n_rel}")
    print(f"   Total triplets     : {len(g)}")
    print(f"   Graphe sauvegardé  : {OUTPUT_GRAPH}")

    if len(g) >= 100:
        print("\n   Critere Lab 2 atteint : >= 100 triplets")
    else:
        print(f"\n   ATTENTION : seulement {len(g)} triplets (objectif >= 100)")

if __name__ == "__main__":
    main()
