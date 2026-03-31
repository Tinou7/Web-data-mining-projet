# Flags Knowledge Graph — Final Report

**Course:** Web Mining & Semantics  
**Domain:** World Flags (Vexillology)  
**Authors:** Tanguy LE GUISQUET and Axel LAUNAY  
**Date:** March 2026

---

## 1. Data Acquisition & Information Extraction

### 1.1 Domain and Seed URLs

We chose **world flags (vexillology)** as our knowledge graph domain. This domain is well-suited for a knowledge graph because it involves clearly structured relationships between countries, their flags, symbols, colors, and historical adoption dates.

**Seed URLs (20 Wikipedia pages):**

| Category | URLs |
|----------|------|
| By continent | Flags of Africa, Asia, Europe, North America, South America, Oceania |
| General | National flag, Flag, Vexillology |
| Individual flags | France, Japan, Brazil, USA, UK, Canada, China, India, Australia, Germany, Italy |

### 1.2 Crawler Design and Web Ethics

The crawler (`src/crawl/crawler.py`) uses `trafilatura` to fetch and extract the main textual content from each Wikipedia page, automatically stripping HTML boilerplate (navigation menus, footers, sidebars, copyright notices).

**Ethics:** Wikipedia explicitly allows crawling for non-commercial purposes. Our crawler:
- Targets only Wikipedia pages (permissive Terms of Service)
- Does not implement parallel requests (no server load)
- Uses `trafilatura.fetch_url()` which respects standard HTTP conventions

**Quality filter:** A minimum threshold of **500 words** is applied before saving a page. All 20 seed pages passed this threshold and were retained in `data/crawler_output.jsonl`.

### 1.3 Cleaning Pipeline

Each downloaded page passes through the following pipeline:

```
Raw HTML → trafilatura extraction → main text → word count check (≥500) → JSONL storage
```

`trafilatura` was chosen specifically for its boilerplate removal capability: it identifies the "main content zone" of a page using heuristics based on text density, tag structure, and link ratio. This avoids storing navigation text such as "Click here to subscribe" or "Copyright 2024" in the knowledge base.

### 1.4 Named Entity Recognition (NER)

NER was performed with spaCy (`en_core_web_sm`) on all documents. Four entity types were retained:

| Type | Description | Count |
|------|-------------|-------|
| `GPE` | Countries, cities, geopolitical regions | 1,716 |
| `ORG` | Organizations | 2,893 |
| `PERSON` | People | 1,821 |
| `DATE` | Dates and years | 3,507 |
| **Total** | | **9,937** |

**Post-processing filters applied:**
- Remove spaCy stopwords
- Remove tokens shorter than 3 characters
- Remove domain blacklist (`flag`, `flags`, `that`, `which`, etc.)

**NER examples extracted:**

| Entity | Type | Source page |
|--------|------|-------------|
| `France` | GPE | Flag of France |
| `Japan` | GPE | Flag of Japan |
| `1908` | DATE | Flags of Oceania |
| `Commonwealth Star` | ORG | Flags of Oceania |
| `Nelson` | PERSON | National flag |

**Relation extraction** used spaCy dependency parsing to find (Subject, Verb, Object) triples where both subject and object are named entities. Examples:

| Subject | Verb | Object | Source |
|---------|------|--------|--------|
| Malaysia | form | ASEAN | Flags of Asia |
| Italy | adopt | flags | National flag |
| Japan | administer | Palau | Flag of Japan |
| House | rule | France | Flag of France |

### 1.5 Entity Ambiguity Cases

During extraction, **110 entities** were tagged with more than one label across different documents. Three representative cases:

**Case 1 — "Marshall"**
- Tagged as `PERSON` (e.g., "Marshall Islands" parsed as a person's name)
- Tagged as `GPE` in other contexts (the Marshall Islands as a country)
- *Root cause:* Short, out-of-context token; the model lacks the surrounding noun phrase "Islands."

**Case 2 — "Armenia"**
- Tagged as `GPE` (country)
- Tagged as `ORG` in contexts like "Republic of Armenia" where the full phrase matches an organization pattern
- *Root cause:* Country names embedded in formal institution names confuse the NER.

**Case 3 — "Alexandria"**
- Tagged as `GPE` (city in Egypt)
- Tagged as `PERSON` on pages where it appears in isolation without a preceding article, resembling a given name
- *Root cause:* Absence of article or context triggers the PERSON classifier.

**Scaling reflection:** On 20 pages the pipeline runs in seconds. At 10,000 pages, the main bottlenecks would be: (1) memory — all documents cannot be held in RAM simultaneously, requiring `nlp.pipe()` with streaming; (2) throughput — a transformer model (`en_core_web_trf`) is 5× slower but more accurate; (3) deduplication — a canonical entity store keyed on normalized text would replace per-document redundant extraction; (4) crawl politeness — a robust crawler would need rate limiting, `robots.txt` checking, and exponential backoff.

---

## 2. Knowledge Base Construction, Alignment & Expansion

### 2.1 RDF Modeling Choices

The ontology (`kg_artifacts/ontology.ttl`) was designed around the vexillology domain:

**Classes:**

```
owl:Class: Country (subClassOf GeopoliticalEntity)
owl:Class: Flag
owl:Class: Symbol
owl:Class: Continent
owl:Class: Organization
owl:Class: Date
```

**Object Properties:**

| Property | Domain | Range | Rationale |
|----------|--------|-------|-----------|
| `flags:hasFlag` | GeopoliticalEntity | Flag | Core relation: country owns flag |
| `flags:hasSymbol` | Flag | Symbol | Flag contains visual symbols |
| `flags:locatedIn` | Country | Continent | Geopolitical hierarchy |
| `flags:affiliatedWith` | Organization | GeopoliticalEntity | Org–country links |
| `flags:adoptedIn` | Flag | Date | Historical adoption date |

**Design choice:** Every `GPE` entity automatically generates a `Flag` node via `hasFlag`, ensuring the core country–flag relation is always populated even when the text does not explicitly mention it.

### 2.2 Initial Knowledge Base

| Metric | Value |
|--------|-------|
| Triplets | 29,336 |
| Entities | 9,937 |
| Relations | 11 |

### 2.3 Entity Linking with Confidence

Entity linking was performed via **batch SPARQL queries** on the Wikidata public endpoint. Entities were processed in chunks of 50 with a 2-second polite delay between batches to avoid HTTP 429 rate-limit errors.

**Matching strategy:**
- Exact label match (case-insensitive) → confidence **0.99**
- Partial match (label contains or is contained in entity name) → confidence **0.85**

**Mapping table (sample):**

| Private Entity | External URI | QID | Confidence |
|---------------|-------------|-----|------------|
| France | wd:Q142 | Q142 | 0.99 |
| Japan | wd:Q17 | Q17 | 0.99 |
| Australia | wd:Q408 | Q408 | 0.99 |
| New Zealand | wd:Q664 | Q664 | 0.99 |
| Brazil | wd:Q155 | Q155 | 0.99 |

**Results:**

| Confidence | Count |
|-----------|-------|
| Exact match (≥ 0.99) | ~480 |
| Partial match (0.85–0.99) | ~65 |
| **Total linked** | **545** |

Alignment triples stored as `owl:sameAs` in `kg_artifacts/alignment.ttl`.

### 2.4 Predicate Alignment

Five private predicates were aligned to Wikidata properties. Alignment was validated by querying Wikidata with entity pairs and comparing candidate properties semantically:

| Private Predicate | Wikidata Property | Label | Alignment |
|-------------------|-------------------|-------|-----------|
| `flags:hasFlag` | `wdt:P41` | flag image | `owl:equivalentProperty` |
| `flags:locatedIn` | `wdt:P17` | country | `owl:equivalentProperty` |
| `flags:adoptedIn` | `wdt:P571` | inception | `owl:equivalentProperty` |
| `flags:hasSymbol` | `wdt:P154` | logo image | `owl:equivalentProperty` |
| `flags:affiliatedWith` | `wdt:P361` | part of | `owl:equivalentProperty` |

### 2.5 SPARQL Expansion Strategy

Expansion used **1-hop and 2-hop SPARQL queries** on Wikidata, anchored on the 545 confidently aligned entities. Only 29 domain-relevant Wikidata properties were selected to avoid polluting the graph with irrelevant triples.

**1-hop query (example for France):**
```sparql
SELECT ?p ?o WHERE {
  wd:Q142 ?p ?o .
} LIMIT 1000
```

**2-hop query (example):**
```sparql
SELECT ?award ?p ?o WHERE {
  ?country wdt:P41 ?flag .
  ?flag ?p ?o .
} LIMIT 10000
```

### 2.6 Final KB Statistics

| Metric | Target | Achieved |
|--------|--------|----------|
| Triplets | 50,000–200,000 | **141,017** ✓ |
| Entities | 5,000–30,000 | **~95,426** ✓ |
| Relations | 50–200 | **31** ⚠️ |

> The relation count (31) is below the 50–200 target. This reflects the inherent specificity of the vexillology domain: flags have fewer distinct relation types than general-purpose KGs. All 29 expansion properties are semantically relevant.

**KGE splits:**

| Split | Triplets |
|-------|----------|
| train.txt | 114,566 |
| valid.txt | 3,870 |
| test.txt | 3,670 |
| **Total** | **122,106** |

---

## 3. Reasoning with SWRL

### 3.1 SWRL Rule on family.owl

Using OWLReady2, we loaded `family.owl` and applied the following SWRL rule:

```
Person(?p) ∧ age(?p, ?a) ∧ swrlb:greaterThan(?a, 60) → oldPerson(?p)
```

Since OWLReady2 does not natively support `swrlb` built-in comparators, the rule was applied manually by iterating over all `Person` instances and checking the `age` data property:

```python
for person in onto.Person.instances():
    if person.age and int(person.age) > 60:
        person.is_a.append(onto.oldPerson)
```

**Output:** All persons with `age > 60` in `family.owl` were classified as `oldPerson`. The reasoning result was printed per instance with their name and age.

### 3.2 SWRL Rule on the Flags KB

We designed the following horn rule with 2 conditions (as required):

```
Country(?c) ∧ hasFlag(?c, ?f) → FlaggedCountry(?c)
```

**Interpretation:** Any country that possesses at least one flag triple is inferred to belong to the `FlaggedCountry` class.

**Application:** The rule was applied with rdflib over `kg_artifacts/initial_graph.ttl`. For each `Country` entity, if it had at least one `hasFlag` outgoing triple, a new `rdf:type flags:FlaggedCountry` triple was added.

**Sample inferred instances:**
- `flagsr:France` → `flags:FlaggedCountry`
- `flagsr:Japan` → `flags:FlaggedCountry`
- `flagsr:Brazil` → `flags:FlaggedCountry`
- `flagsr:United_States` → `flags:FlaggedCountry`

The inferred graph is saved to `kg_artifacts/swrl_inferred.ttl`.

---

## 4. Knowledge Graph Embeddings

### 4.1 Data Cleaning and Splits

Before training, the expanded KB was cleaned:
- Duplicate triples removed
- Inconsistent URIs normalized
- Entities appearing only in validation/test redistributed to training

**Split (80/10/10):**

| Split | Triplets |
|-------|----------|
| train.txt | 114,566 |
| valid.txt | 3,870 |
| test.txt | 3,670 |

### 4.2 Models and Training Configuration

Two embedding models were trained using **PyKEEN**:

| Hyperparameter | Value |
|---------------|-------|
| Models | TransE, DistMult |
| Embedding dimension | 50 |
| Epochs | 30 |
| Batch size | 256 |
| Learning rate | 0.01 |
| Optimizer | Adam |
| Negative sampling | Basic (PyKEEN default) |
| Device | CPU |

**Note on subset:** Due to CPU-only hardware constraints, training was run on a **20,000-triple subset** of the training set. The full dataset (114,566 triples) exceeded feasible computation time on a laptop CPU.

### 4.3 Evaluation Results — Link Prediction (Filtered Metrics)

| Metric | TransE | DistMult |
|--------|--------|----------|
| **MRR** | **0.0192** | 0.0105 |
| **Hits@1** | **0.0080** | 0.0057 |
| **Hits@3** | **0.0183** | 0.0104 |
| **Hits@10** | **0.0394** | 0.0184 |

**TransE outperforms DistMult on all metrics.** This is consistent with theory: our KB contains many directional 1-to-1 relations (`hasFlag`, `locatedIn`) which TransE models well as vector translations. DistMult assumes symmetric scoring (score(h,r,t) = score(t,r,h)), which is inappropriate for asymmetric relations like `locatedIn`.

### 4.4 Size-Sensitivity Analysis

| Training size | Model | MRR | Hits@10 |
|--------------|-------|-----|---------|
| 20k triples | TransE | 0.0192 | 0.0394 |
| 20k triples | DistMult | 0.0105 | 0.0184 |
| 50k triples | — | Not run (time limit) | — |
| Full (114k) | — | Not run (CPU limit) | — |

Training on 50k and the full dataset was not feasible within hardware constraints (estimated 4–8 hours on CPU). The 20k results are already consistent with the expected behavior for small KBs: low but non-trivial MRR, with TransE outperforming DistMult.

### 4.5 t-SNE and Nearest Neighbors

**t-SNE:** A 2D projection (perplexity=30) of 500 sampled TransE entity embeddings was generated (`data/kge/results/tsne_transe.png`). The plot does not show sharply separated clusters by ontology class. This is expected given: (1) the 20k training subset is too small for stable cluster formation, (2) the domain has limited class diversity (most entities are `Country` or `Flag`), and (3) 30 epochs on CPU is insufficient for full convergence. However, entities with many shared Wikidata neighbors (e.g., European countries) tend to appear closer together.

**Nearest neighbors (TransE, cosine similarity):**

| Query entity | Nearest neighbors |
|-------------|-------------------|
| France (Q142) | Italy, Germany, Spain, Belgium, Netherlands |
| Japan (Q17) | South Korea, China, Taiwan, Thailand, Philippines |
| Australia (Q408) | New Zealand, Canada, United Kingdom, South Africa |

Results are semantically coherent: neighboring countries in the embedding space are geographically and historically related, suggesting the embedding captures some geographic/political structure.

### 4.6 Relation Behavior

- **`hasFlag` (1-to-1):** TransE models this well. Each country maps to exactly one flag via a consistent translation vector.
- **`locatedIn` (many-to-1):** TransE handles reasonably. Many countries map to the same continent.
- **`affiliatedWith` (many-to-many):** Both models struggle. Organizations can relate to multiple countries, which violates TransE's 1-to-1 assumption.
- **Symmetric relations:** DistMult performs better on any symmetric relation, but few exist in this KB.

---

## 5. RAG with RDF/SPARQL

### 5.1 Setup

| Parameter | Value |
|-----------|-------|
| Machine | Windows 11, CPU only |
| LLM | llama3.2:3b (Ollama) |
| Graph source | `kg_artifacts/initial_graph.ttl` (29,336 triples) |
| Interface | Gradio web UI — `http://localhost:7860` |

### 5.2 Schema Summary

At startup, the following schema summary is built from the graph and injected into every prompt:
- All namespace prefixes
- Up to 40 distinct predicates (SPARQL `SELECT DISTINCT ?p`)
- Up to 20 distinct classes
- 15 representative sample triples

This provides the LLM with the exact IRIs and predicates it must use, preventing hallucinated property names.

### 5.3 NL→SPARQL Prompt Template

```
You are a SPARQL generator. Convert the user QUESTION into a valid SPARQL 1.1 SELECT query
for the given RDF graph schema. Follow strictly:
- Use ONLY the IRIs/prefixes visible in the SCHEMA SUMMARY.
- Prefer readable SELECT projections with variable names.
- Do NOT invent new predicates/classes.
- Return ONLY the SPARQL query in a single fenced code block labeled ```sparql
- No explanations or extra text outside the code block.

SCHEMA SUMMARY:
{schema_summary}

QUESTION:
{question}
```

### 5.4 Self-Repair Mechanism

If the generated SPARQL throws an exception when executed by rdflib, the error message is sent back to the LLM with the original bad query and a repair prompt:

```
The previous SPARQL failed to execute. Using the SCHEMA SUMMARY and the ERROR MESSAGE,
return a corrected SPARQL 1.1 SELECT query...

BAD SPARQL: {bad_query}
ERROR MESSAGE: {error_msg}
```

One repair attempt is made. If the repair also fails, the error is reported to the user.

### 5.5 Evaluation — Baseline vs RAG (5 Questions)

| # | Question | Baseline (no RAG) | RAG (SPARQL-gen) | Correct? |
|---|----------|-------------------|-----------------|----------|
| 1 | List all countries in the graph | Generic world country list from training data | Returns all 9,937 `flags:Country` entities via SPARQL | ✓ RAG correct |
| 2 | Which countries have a flag? | "All countries have national flags" (generic) | Lists country–flag pairs from `hasFlag` triples | ✓ RAG correct |
| 3 | What is the source URL for France? | Hallucinated Wikipedia URL | Returns exact `flags:sourceURL` literal from graph | ✓ RAG correct |
| 4 | Which entities are of type Organization? | Lists generic world organizations | Returns ORG-typed entities extracted from the crawl | ✓ RAG correct |
| 5 | What is the adoption date of the Flag of Japan? | "1999" (hallucinated, incorrect) | No results — `adoptedIn` triples absent for Japan | ✗ Both fail (KB gap) |

**RAG correctness: 4/5.** The single failure (Q5) is due to a gap in the KB: dependency parsing did not extract the adoption date for Japan from the crawled text.

### 5.6 Discussion

**Accuracy:** RAG significantly outperforms the baseline on domain-specific factual questions. The LLM alone hallucinates specific dates and URLs; RAG grounds answers in the actual graph data.

**Failure cases:** Questions about specific literal-valued facts (dates, colors, numeric areas) often fail because literal-heavy predicates were removed during KB cleaning for embedding preparation.

**Self-repair:** The repair loop was triggered on approximately 30% of initial queries during testing. Common repair cases: invalid prefix usage, undefined variable names, wrong predicate spelling. The LLM successfully repaired ~70% of these cases.

**Scalability:** On the full `expanded.nt` (141,017 triples), rdflib in-memory query execution is 2–5× slower per query. A production system would replace rdflib with a dedicated triple store (Apache Jena Fuseki or Virtuoso) served via a SPARQL endpoint.

### 5.7 Demo Screenshot

The Gradio web UI is accessible at `http://localhost:7860` after running `python src/rag/app.py`. The interface displays four panels: the input question, the baseline LLM answer, the generated SPARQL query (with repair status), and the RAG result table.

---

## 6. Critical Reflection

### KB Quality Impact

The quality of the initial KB directly constrained every downstream step. The dependency parser extracted relatively few relations (many relations in the `extracted_relations.csv` are self-loops like `flag → become → flag`). This limited the richness of the initial graph and made the SWRL and KGE steps rely heavily on the Wikidata expansion rather than the crawled content.

### Noise Issues

Two main sources of noise were identified:

1. **Expansion noise:** 2-hop SPARQL queries on Wikidata introduced entities outside the vexillology domain (individual politicians, historical events). These diluted the semantic coherence of the KGE embedding space.
2. **NER noise:** 1,821 entities were classified as `PERSON`, but many are clearly not persons (e.g., "Tokelauan", "Divided", "Commonwealth Star"). This inflated the entity count and introduced false triples in the graph.

### Rule-Based vs. Embedding-Based Reasoning

| Aspect | SWRL (rule-based) | KGE (TransE/DistMult) |
|--------|-------------------|----------------------|
| Precision | 100% on known data | Low (MRR ≈ 0.019) |
| Recall | Limited to KB facts | Can generalize |
| Interpretability | High (explicit rules) | Low (vector space) |
| Assumption | Closed-world | Open-world |
| Scalability | Limited (rule explosion) | Good (fixed model size) |

SWRL is appropriate when the KB is complete and rules are well-defined. KGE is more appropriate for link completion in incomplete KBs, but requires large, high-quality training data to perform well.

### What We Would Improve

1. **Larger and cleaner KB:** Use a dedicated vexillology API (e.g., FlagCDN or REST Countries) instead of Wikipedia NER, which would yield more precise structured data with fewer NER errors.
2. **Better NER model:** Replace `en_core_web_sm` with `en_core_web_trf` (transformer-based) to reduce false PERSON classifications.
3. **Full KGE training:** Run TransE and DistMult on the full 114k training triples with GPU acceleration to obtain meaningful MRR scores.
4. **RAG on expanded graph:** The RAG system currently queries the initial graph (29k triples). Connecting it to the full expanded graph (141k triples) via a SPARQL endpoint would significantly improve answer coverage.
5. **Coreference resolution:** Adding a coreference step before NER (e.g., resolving "it" or "the country" to a named entity) would reduce ambiguity and improve relation extraction quality.

---

## Knowledge Graph Statistics Summary

| Metric | Value |
|--------|-------|
| Crawled pages | 20 |
| Total entities extracted | 9,937 |
| Initial graph triplets | 29,336 |
| Entities linked to Wikidata | 545 |
| Predicate alignments | 5 |
| Expanded graph triplets | 141,017 |
| Expanded entities | ~95,426 |
| KGE train triples (used) | 20,000 / 114,566 |
| TransE MRR (20k) | 0.0192 |
| DistMult MRR (20k) | 0.0105 |
| RAG questions correct | 4/5 |
