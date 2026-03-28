# Flags Knowledge Graph

A full Knowledge Graph pipeline on the domain of **world flags (vexillology)**, built as part of the Web Mining & Semantics course project.

## Domain

World flags and their associated countries, continents, symbols, and historical adoption dates. Data crawled from Wikipedia.

## Project Structure

```
flags-knowledge-graph/
├── src/
│   ├── crawl/          # Lab 1 - Web crawling
│   ├── ie/             # Lab 1 - NER & relation extraction
│   ├── kg/             # Lab 2 - RDF graph, entity linking, SPARQL expansion
│   ├── reason/         # Lab 3 - SWRL reasoning
│   ├── kge/            # Lab 3 - Knowledge Graph Embedding
│   └── rag/            # Lab 4 - RAG with local LLM
├── data/
│   └── samples/        # Sample data files
├── kg_artifacts/       # RDF files (ontology, alignment, stats)
├── reports/            # Final report
├── notebooks/          # Original Lab 1 notebook
├── requirements.txt
└── README.md
```

## Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

Install Ollama from https://ollama.com and pull the model:
```bash
ollama pull llama3.2:3b
```

## How to Run Each Module

> All commands must be run from the project root: `flags-knowledge-graph/`

### Lab 1 — Crawling & NER
```bash
python src/crawl/crawler.py
python src/ie/extract_entities.py
```
Outputs: `data/crawler_output.jsonl`, `data/extracted_knowledge.csv`, `data/extracted_relations.csv`

### Lab 2 — KB Construction
```bash
python src/kg/build_graph.py
python src/kg/entity_linking.py
python src/kg/expand_kb.py
```
Outputs: `kg_artifacts/ontology.ttl`, `kg_artifacts/initial_graph.ttl`, `kg_artifacts/alignment.ttl`, `kg_artifacts/expanded.nt`

### Lab 3 — Reasoning & KGE
```bash
# SWRL on family.owl
python src/reason/swrl_family.py

# SWRL on flags KB
python src/reason/swrl_flags.py

# KGE data preparation
python src/kge/prepare_data.py

# KGE training & evaluation (TransE + DistMult)
python src/kge/train_eval.py
```

### Lab 4 — RAG Demo (CLI)
```bash
python src/rag/lab_rag_sparql_gen.py
```

### Lab 4 — RAG Demo (Web UI)
```bash
python src/rag/app.py
```
Then open http://localhost:7860 in your browser.

## Knowledge Graph Statistics

| Metric | Value |
|--------|-------|
| Initial triplets | 29,336 |
| Expanded triplets | 141,017 |
| Entities linked to Wikidata | 545 |
| KGE train triples | 114,566 |

Large files (`expanded.nt`, KGE splits) are excluded from the repo due to size.
Download link: *(add Google Drive link here)*

## Hardware Requirements

- RAM: 8GB minimum recommended
- Storage: ~2GB (Ollama model + dependencies)
- GPU: not required (CPU only)
- OS: Windows 10/11

## Ollama Setup

```bash
# Start Ollama (runs automatically after install)
ollama pull llama3.2:3b

# Test
ollama run llama3.2:3b "What is a flag?"
```

## Screenshots

See the final report (`reports/final_report.pdf`) for screenshots of the RAG web UI demo.
