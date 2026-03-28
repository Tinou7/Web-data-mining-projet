import re
import requests
from rdflib import Graph

# ----------------------------
# Configuration
# ----------------------------
TTL_FILE   = "kg_artifacts/initial_graph.ttl"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL      = "llama3.2:3b"

MAX_PREDICATES = 40
MAX_CLASSES    = 20
SAMPLE_TRIPLES = 15

# ----------------------------
# 0) Call local LLM
# ----------------------------
def ask_local_llm(prompt: str) -> str:
    payload = {"model": MODEL, "prompt": prompt, "stream": False}
    response = requests.post(OLLAMA_URL, json=payload, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
    return response.json().get("response", "")

# ----------------------------
# 1) Load RDF graph
# ----------------------------
def load_graph(path: str) -> Graph:
    g = Graph()
    g.parse(path, format="turtle")
    print(f"Graphe chargé : {len(g)} triplets depuis {path}")
    return g

# ----------------------------
# 2) Build schema summary
# ----------------------------
def build_schema_summary(g: Graph) -> str:
    # Prefixes
    ns_map = {p: str(ns) for p, ns in g.namespace_manager.namespaces()}
    prefix_lines = "\n".join(f"PREFIX {p}: <{ns}>" for p, ns in sorted(ns_map.items()))

    # Predicates
    q_pred = f"SELECT DISTINCT ?p WHERE {{ ?s ?p ?o . }} LIMIT {MAX_PREDICATES}"
    preds = [str(r.p) for r in g.query(q_pred)]

    # Classes
    q_cls = f"SELECT DISTINCT ?cls WHERE {{ ?s a ?cls . }} LIMIT {MAX_CLASSES}"
    clss = [str(r.cls) for r in g.query(q_cls)]

    # Sample triples
    q_sample = f"SELECT ?s ?p ?o WHERE {{ ?s ?p ?o . }} LIMIT {SAMPLE_TRIPLES}"
    samples = [(str(r.s), str(r.p), str(r.o)) for r in g.query(q_sample)]

    pred_lines   = "\n".join(f"- {p}" for p in preds)
    cls_lines    = "\n".join(f"- {c}" for c in clss)
    sample_lines = "\n".join(f"- {s} {p} {o}" for s, p, o in samples)

    return f"""{prefix_lines}

# Predicates
{pred_lines}

# Classes
{cls_lines}

# Sample triples
{sample_lines}""".strip()

# ----------------------------
# 3) NL -> SPARQL
# ----------------------------
SPARQL_INSTRUCTIONS = """You are a SPARQL generator for an RDF knowledge graph about world flags.
The graph uses these exact prefixes and predicates:

PREFIX flags: <http://flags-kg.org/ontology#>
PREFIX flagsr: <http://flags-kg.org/resource/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Classes: flags:Country, flags:Flag, flags:Person, flags:Organization, flags:Date
Predicates: rdf:type, rdfs:label, flags:hasFlag, flags:hasSymbol, flags:adoptedIn, flags:affiliatedWith, flags:relatedTo, flags:sourceURL

Example queries:
- List countries: SELECT ?c WHERE { ?c rdf:type flags:Country . }
- List flags: SELECT ?f WHERE { ?f rdf:type flags:Flag . }
- Country with its flag: SELECT ?country ?flag WHERE { ?country rdf:type flags:Country . ?country flags:hasFlag ?flag . }
- Label of entity: SELECT ?label WHERE { flagsr:France rdfs:label ?label . }

Rules:
- Use ONLY the prefixes and predicates shown above
- Return ONLY the SPARQL query in a ```sparql code block
- No explanations outside the code block
"""

CODE_BLOCK_RE = re.compile(r"```(?:sparql)?\s*(.*?)```", re.IGNORECASE | re.DOTALL)

def extract_sparql(text: str) -> str:
    m = CODE_BLOCK_RE.search(text)
    return m.group(1).strip() if m else text.strip()

def generate_sparql(question: str, schema: str) -> str:
    prompt = f"""{SPARQL_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema}

QUESTION:
{question}

Return only the SPARQL query in a code block."""
    raw = ask_local_llm(prompt)
    return extract_sparql(raw)

# ----------------------------
# 4) Execute SPARQL
# ----------------------------
def run_sparql(g: Graph, query: str):
    res = g.query(query)
    vars_ = [str(v) for v in res.vars]
    rows  = [tuple(str(cell) for cell in r) for r in res]
    return vars_, rows

# ----------------------------
# 5) Self-repair
# ----------------------------
REPAIR_INSTRUCTIONS = """The previous SPARQL query failed. Using the SCHEMA SUMMARY and ERROR MESSAGE,
return a corrected SPARQL 1.1 SELECT query in a ```sparql code block."""

def repair_sparql(schema: str, question: str, bad_query: str, error: str) -> str:
    prompt = f"""{REPAIR_INSTRUCTIONS}

SCHEMA SUMMARY:
{schema}

QUESTION: {question}
BAD SPARQL:
{bad_query}

ERROR: {error}

Return only the corrected SPARQL in a code block."""
    return extract_sparql(ask_local_llm(prompt))

def answer_with_rag(g: Graph, schema: str, question: str) -> dict:
    sparql = generate_sparql(question, schema)
    try:
        vars_, rows = run_sparql(g, sparql)
        return {"query": sparql, "vars": vars_, "rows": rows, "repaired": False, "error": None}
    except Exception as e:
        repaired = repair_sparql(schema, question, sparql, str(e))
        try:
            vars_, rows = run_sparql(g, repaired)
            return {"query": repaired, "vars": vars_, "rows": rows, "repaired": True, "error": None}
        except Exception as e2:
            return {"query": repaired, "vars": [], "rows": [], "repaired": True, "error": str(e2)}

# ----------------------------
# 6) Baseline (no RAG)
# ----------------------------
def answer_no_rag(question: str) -> str:
    return ask_local_llm(f"Answer this question as best you can:\n\n{question}")

# ----------------------------
# 7) Pretty print
# ----------------------------
def pretty_print(result: dict):
    if result.get("error"):
        print(f"\n[Erreur] {result['error']}")
    print(f"\n[SPARQL utilisé]")
    print(result["query"])
    print(f"[Réparé ?] {result['repaired']}")
    rows = result.get("rows", [])
    if not rows:
        print("[Aucun résultat]")
        return
    print(f"\n[Résultats] ({len(rows)} lignes)")
    print(" | ".join(result.get("vars", [])))
    for r in rows[:10]:
        print(" | ".join(r))
    if len(rows) > 10:
        print(f"... ({len(rows)} résultats total)")

# ----------------------------
# 8) CLI demo
# ----------------------------
if __name__ == "__main__":
    g      = load_graph(TTL_FILE)
    schema = build_schema_summary(g)

    print("\nSchéma du graphe prêt. Démo RAG — Flags Knowledge Graph")
    print("Tape 'quit' pour quitter\n")

    while True:
        q = input("Question : ").strip()
        if q.lower() == "quit":
            break

        print("\n--- Baseline (sans RAG) ---")
        print(answer_no_rag(q))

        print("\n--- RAG (SPARQL + graphe) ---")
        result = answer_with_rag(g, schema, q)
        pretty_print(result)
        print()
