import pandas as pd
import requests
import time
from rdflib import Graph, Namespace, URIRef, Literal, RDF, RDFS, OWL, XSD
import re
import os

# ----------------------------
# Paths
# ----------------------------
INPUT_ENTITIES   = "data/extracted_knowledge.csv"
OUTPUT_ALIGNMENT = "kg_artifacts/alignment.ttl"

# ----------------------------
# Namespaces
# ----------------------------
FLAGS   = Namespace("http://flags-kg.org/ontology#")
FLAGS_R = Namespace("http://flags-kg.org/resource/")
WD      = Namespace("http://www.wikidata.org/entity/")
WDT     = Namespace("http://www.wikidata.org/prop/direct/")

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "FlagsKG/1.0 (knowledge-graph-project; python-requests)"}

# ----------------------------
# Helpers
# ----------------------------
def to_uri_slug(text: str) -> str:
    slug = re.sub(r"[^\w]", "_", text.strip())
    slug = re.sub(r"_+", "_", slug).strip("_")
    return slug

def entity_uri(name: str) -> URIRef:
    return FLAGS_R[to_uri_slug(name)]

def is_clean(name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 40:
        return False
    if name.startswith("http"):
        return False
    if any(c in name for c in ["[", "]", "{", "}", "|"]):
        return False
    if name[0].isdigit():
        return False
    if name.lower().strip() in {"flag", "flags", "the", "a", "an", "see", "pdf", "canton"}:
        return False
    return True

# ----------------------------
# Batch SPARQL lookup on Wikidata
# (one query for all entities at once)
# ----------------------------
def batch_link_wikidata(entity_names: list[str]) -> dict[str, dict]:
    """
    Query Wikidata SPARQL to find QIDs for a list of entity names.
    Returns a dict: name -> {qid, uri, label, confidence}
    """
    results_map = {}

    # Process in chunks of 50 to avoid query size limits
    chunk_size = 50
    chunks = [entity_names[i:i+chunk_size]
              for i in range(0, len(entity_names), chunk_size)]

    for ci, chunk in enumerate(chunks):
        values = " ".join(f'"{name}"@en' for name in chunk)
        query = f"""
        SELECT ?item ?itemLabel WHERE {{
          VALUES ?itemLabel {{ {values} }}
          ?item rdfs:label ?itemLabel .
          ?item wikibase:sitelinks ?sitelinks .
          FILTER(?sitelinks > 5)
        }}
        LIMIT {chunk_size * 2}
        """
        try:
            r = requests.get(
                SPARQL_ENDPOINT,
                params={"query": query, "format": "json"},
                headers=HEADERS,
                timeout=30,
            )
            if r.status_code == 429:
                print(f"   Rate limited, attente 30s...")
                time.sleep(30)
                # retry once
                r = requests.get(
                    SPARQL_ENDPOINT,
                    params={"query": query, "format": "json"},
                    headers=HEADERS,
                    timeout=30,
                )
            if not r.text.strip():
                time.sleep(5)
                continue

            data = r.json()
            for row in data["results"]["bindings"]:
                qid   = row["item"]["value"].split("/entity/")[-1]
                label = row["itemLabel"]["value"]
                # Match back to original name (case-insensitive)
                for name in chunk:
                    if name.lower() == label.lower():
                        if name not in results_map:
                            results_map[name] = {
                                "qid": qid,
                                "uri": WD[qid],
                                "label": label,
                                "confidence": 0.99,
                            }
                        break
                    elif name.lower() in label.lower() or label.lower() in name.lower():
                        if name not in results_map:
                            results_map[name] = {
                                "qid": qid,
                                "uri": WD[qid],
                                "label": label,
                                "confidence": 0.85,
                            }

            print(f"   Chunk [{ci+1}/{len(chunks)}] — {len(results_map)} entités liées jusqu'ici")
            time.sleep(2)  # polite delay between chunks

        except Exception as e:
            print(f"   Erreur chunk {ci+1}: {e}")
            time.sleep(5)

    return results_map

# ----------------------------
# Main
# ----------------------------
def main():
    os.makedirs("kg_artifacts", exist_ok=True)

    df = pd.read_csv(INPUT_ENTITIES)

    # GPE only, clean names
    df_target = df[df["Label"] == "GPE"].copy()
    df_target = df_target.drop_duplicates(subset=["Entity"])
    df_target = df_target[df_target["Entity"].apply(is_clean)]
    entity_names = df_target["Entity"].tolist()
    print(f"Entités à lier : {len(entity_names)} (GPE uniques, filtrées)")

    # Batch SPARQL lookup
    print("\nRecherche batch sur Wikidata SPARQL...")
    results_map = batch_link_wikidata(entity_names)

    # Build RDF graph
    g = Graph()
    g.bind("flags",  FLAGS)
    g.bind("flagsr", FLAGS_R)
    g.bind("wd",     WD)
    g.bind("wdt",    WDT)
    g.bind("owl",    OWL)
    g.bind("rdfs",   RDFS)

    mapping_rows = []
    for name, result in results_map.items():
        local_uri = entity_uri(name)
        wd_uri    = result["uri"]
        g.add((local_uri, OWL.sameAs, wd_uri))
        g.add((local_uri, FLAGS["wikidataConfidence"],
               Literal(result["confidence"], datatype=XSD.float)))
        g.add((local_uri, RDFS.label, Literal(name, lang="en")))
        mapping_rows.append({
            "Private Entity": name,
            "External URI": str(wd_uri),
            "QID": result["qid"],
            "Label": result["label"],
            "Confidence": result["confidence"],
        })

    # Predicate alignment
    print("\nAlignement des prédicats...")
    predicate_alignments = [
        (FLAGS["hasFlag"],        WDT["P41"],  "flag"),
        (FLAGS["locatedIn"],      WDT["P17"],  "country"),
        (FLAGS["adoptedIn"],      WDT["P571"], "inception"),
        (FLAGS["hasSymbol"],      WDT["P154"], "logo image"),
        (FLAGS["affiliatedWith"], WDT["P361"], "part of"),
    ]
    for local_prop, wd_prop, label in predicate_alignments:
        g.add((local_prop, OWL.equivalentProperty, wd_prop))
        g.add((local_prop, RDFS.label, Literal(label, lang="en")))
        print(f"   {local_prop.split('#')[-1]} → {wd_prop}")

    # Save
    g.serialize(destination=OUTPUT_ALIGNMENT, format="turtle")
    pd.DataFrame(mapping_rows).to_csv("kg_artifacts/entity_mapping.csv", index=False)

    print(f"\n--- Résultats ---")
    print(f"  Entités liées  : {len(results_map)}")
    print(f"  Triplets RDF   : {len(g)}")
    print(f"  Fichiers       : {OUTPUT_ALIGNMENT}, kg_artifacts/entity_mapping.csv")

if __name__ == "__main__":
    main()
