import re
import time
import os
import requests
from rdflib import Graph, Namespace, URIRef, OWL

# ----------------------------
# Paths
# ----------------------------
INPUT_ALIGNMENT = "kg_artifacts/alignment.ttl"
INPUT_GRAPH     = "kg_artifacts/initial_graph.ttl"
OUTPUT_EXPANDED = "kg_artifacts/expanded.nt"

# ----------------------------
# Namespaces
# ----------------------------
FLAGS   = Namespace("http://flags-kg.org/ontology#")
FLAGS_R = Namespace("http://flags-kg.org/resource/")
WD      = Namespace("http://www.wikidata.org/entity/")
WDT     = Namespace("http://www.wikidata.org/prop/direct/")

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "FlagsKG/1.0 (knowledge-graph-project; python-requests)"}

# Wikidata properties relevant to flags/countries domain
FLAG_PROPERTIES = [
    "P41",    # flag image
    "P17",    # country
    "P30",    # continent
    "P36",    # capital
    "P37",    # official language
    "P571",   # inception
    "P856",   # official website
    "P18",    # image
    "P298",   # ISO 3166-1 alpha-3
    "P297",   # ISO 3166-1 alpha-2
    "P131",   # located in administrative entity
    "P910",   # topic's main category
    "P361",   # part of
    "P1566",  # GeoNames ID
    "P35",    # head of state
    "P6",     # head of government
    "P38",    # currency
    "P85",    # anthem
    "P94",    # coat of arms image
    "P163",   # flag (used by subdivisions)
    "P122",   # basic form of government
    "P1082",  # population
    "P2131",  # nominal GDP
    "P625",   # coordinate location
    "P242",   # locator map image
    "P150",   # contains administrative territorial entity
    "P421",   # time zone
    "P194",   # legislative body
]

# ----------------------------
# Helpers
# ----------------------------
def extract_qids(g: Graph) -> list[str]:
    """Extract all Wikidata QIDs from owl:sameAs links."""
    qids = []
    for s, p, o in g.triples((None, OWL.sameAs, None)):
        uri = str(o)
        if "wikidata.org/entity/Q" in uri:
            qid = uri.split("/entity/")[-1]
            if re.match(r"^Q\d+$", qid):
                qids.append(qid)
    return list(set(qids))

def batch_sparql_expand(qids: list[str]) -> list[tuple]:
    """Fetch 1-hop triples for a batch of QIDs in one SPARQL query."""
    props = ", ".join(f"wdt:{p}" for p in FLAG_PROPERTIES)
    values = " ".join(f"wd:{qid}" for qid in qids)
    query = f"""
    SELECT ?s ?p ?o WHERE {{
      VALUES ?s {{ {values} }}
      ?s ?p ?o .
      FILTER(?p IN ({props}))
    }}
    LIMIT 5000
    """
    try:
        r = requests.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=60,
        )
        if r.status_code == 429:
            print("   Rate limited, attente 30s...")
            time.sleep(30)
            return []
        if not r.text.strip():
            return []
        data = r.json()
        triples = []
        for row in data["results"]["bindings"]:
            triples.append((
                row["s"]["value"],
                row["p"]["value"],
                row["o"]["value"],
            ))
        return triples
    except Exception as e:
        print(f"   Erreur SPARQL: {e}")
        return []

def batch_sparql_2hop(qids: list[str]) -> list[tuple]:
    """Fetch 2-hop triples: country → capital/language/continent properties."""
    values = " ".join(f"wd:{qid}" for qid in qids)
    query = f"""
    SELECT ?s ?p2 ?o2 WHERE {{
      VALUES ?s {{ {values} }}
      ?s wdt:P36 ?capital .
      ?capital ?p2 ?o2 .
      FILTER(?p2 IN (wdt:P17, wdt:P131, wdt:P30, wdt:P571))
    }}
    LIMIT 3000
    """
    try:
        r = requests.get(
            SPARQL_ENDPOINT,
            params={"query": query, "format": "json"},
            headers=HEADERS,
            timeout=60,
        )
        if not r.text.strip():
            return []
        data = r.json()
        return [
            (row["s"]["value"], row["p2"]["value"], row["o2"]["value"])
            for row in data["results"]["bindings"]
        ]
    except Exception:
        return []

# ----------------------------
# Main
# ----------------------------
def main():
    os.makedirs("kg_artifacts", exist_ok=True)

    print("1. Chargement du graphe d'alignement...")
    g_align = Graph()
    g_align.parse(INPUT_ALIGNMENT, format="turtle")
    qids = extract_qids(g_align)
    print(f"   {len(qids)} entités Wikidata trouvées dans l'alignement")

    print("\n2. Chargement du graphe initial...")
    g = Graph()
    g.parse(INPUT_GRAPH, format="turtle")
    print(f"   {len(g)} triplets initiaux")

    # Batch SPARQL expansion — chunks of 50 QIDs per query
    CHUNK = 50
    chunks = [qids[i:i+CHUNK] for i in range(0, len(qids), CHUNK)]
    print(f"\n3. Expansion SPARQL batch ({len(chunks)} requêtes pour {len(qids)} entités)...")

    def is_valid_uri(value: str) -> bool:
        return value.startswith("http") and " " not in value and not value.startswith("Point")

    def add_triples(g, triples, collect_qids=None):
        for s, p, o in triples:
            if not is_valid_uri(s) or not is_valid_uri(p) or not is_valid_uri(o):
                continue
            try:
                g.add((URIRef(s), URIRef(p), URIRef(o)))
                if collect_qids is not None and "wikidata.org/entity/Q" in o:
                    collect_qids.add(o.split("/entity/")[-1])
            except Exception:
                pass

    # 1-hop expansion
    hop1_objects = set()
    for i, chunk in enumerate(chunks):
        add_triples(g, batch_sparql_expand(chunk), collect_qids=hop1_objects)
        print(f"   1-hop [{i+1}/{len(chunks)}] triplets={len(g)}")
        time.sleep(2)

    # 2-hop expansion from collected objects
    print(f"\n   2-hop sur {len(hop1_objects)} objets collectés...")
    hop2_qids = list(hop1_objects)
    hop2_chunks = [hop2_qids[i:i+CHUNK] for i in range(0, len(hop2_qids), CHUNK)]

    for i, chunk in enumerate(hop2_chunks):
        add_triples(g, batch_sparql_expand(chunk))
        print(f"   2-hop [{i+1}/{len(hop2_chunks)}] triplets={len(g)}")
        time.sleep(2)

        if len(g) >= 150_000:
            print("   Objectif 150k atteint, arrêt expansion.")
            break

    # Save
    print(f"\n4. Sauvegarde...")
    g.serialize(destination=OUTPUT_EXPANDED, format="nt")

    print(f"\n--- Résultats ---")
    print(f"  Triplets totaux   : {len(g)}")
    print(f"  Fichier           : {OUTPUT_EXPANDED}")

    if len(g) >= 50_000:
        print("  Critere Lab 2 atteint : >= 50 000 triplets")
    else:
        print(f"  ATTENTION : {len(g)} triplets — objectif 50 000 non atteint")

if __name__ == "__main__":
    main()
