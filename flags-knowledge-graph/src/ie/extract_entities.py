"""
src/ie/extract_entities.py

Lit data/crawler_output.jsonl, applique spaCy pour :
  - extraire les entités nommées (NER) → data/extracted_knowledge.csv
  - extraire les relations sujet→verbe→objet → data/extracted_relations.csv

Usage :
    python src/ie/extract_entities.py
"""

import spacy
import json
import pandas as pd
from pathlib import Path

# ----------------------------
# Configuration
# ----------------------------
INPUT_FILE       = Path("data/crawler_output.jsonl")
OUTPUT_ENTITIES  = Path("data/extracted_knowledge.csv")
OUTPUT_RELATIONS = Path("data/extracted_relations.csv")

for p in [OUTPUT_ENTITIES, OUTPUT_RELATIONS]:
    p.parent.mkdir(parents=True, exist_ok=True)

# Types d'entités à conserver (consigne Lab 1)
KEPT_LABELS = {"GPE", "DATE", "ORG", "PERSON"}

# Mots à exclure manuellement
BLACKLIST = {"that", "which", "each", "these", "those", "flag", "flags"}

# ----------------------------
# Chargement des données
# ----------------------------
def load_jsonl(path: Path) -> list:
    data = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            data.append(json.loads(line))
    print(f"  {len(data)} documents chargés depuis {path}")
    return data


# ----------------------------
# NER
# ----------------------------
def extract_entities(nlp, data: list) -> pd.DataFrame:
    """
    Extrait les entités nommées de chaque document.
    Applique les filtres : type, stop words, longueur, blacklist.
    """
    rows = []

    for entry in data:
        url  = entry["url"]
        text = entry["text"]
        doc  = nlp(text)

        for ent in doc.ents:
            if ent.label_ not in KEPT_LABELS:
                continue

            clean = ent.text.strip().lower()

            if nlp.vocab[clean].is_stop:
                continue
            if len(clean) < 3:
                continue
            if clean in BLACKLIST:
                continue

            rows.append({
                "Entity":     ent.text.strip(),
                "Label":      ent.label_,
                "Source_URL": url,
            })

    df = pd.DataFrame(rows).drop_duplicates()
    print(f"  {len(df)} entités extraites après nettoyage")
    return df


# ----------------------------
# Extraction de relations
# ----------------------------
def extract_relations(nlp, data: list) -> pd.DataFrame:
    """
    Cherche des triplets (sujet, verbe, objet) via le dependency parser spaCy.
    Garde uniquement les triplets où sujet ET objet sont des entités nommées.
    """
    rows = []

    for entry in data:
        url  = entry["url"]
        text = entry["text"]
        doc  = nlp(text)

        # Index des entités nommées pour filtrage rapide
        ent_texts = {ent.text.lower() for ent in doc.ents if ent.label_ in KEPT_LABELS}

        for token in doc:
            if token.pos_ != "VERB":
                continue

            subj = ""
            obj  = ""

            for child in token.children:
                if child.dep_ == "nsubj":
                    subj = child.text
                if child.dep_ in {"dobj", "attr", "acomp"}:
                    obj = child.text

            # On garde uniquement si les deux sont des entités connues
            if subj and obj:
                if subj.lower() in ent_texts and obj.lower() in ent_texts:
                    rows.append({
                        "Sujet":  subj,
                        "Verbe":  token.lemma_,
                        "Objet":  obj,
                        "Source": url,
                    })

    df = pd.DataFrame(rows).drop_duplicates()
    print(f"  {len(df)} relations extraites")
    return df


# ----------------------------
# Ambiguïtés (rapport Lab 1)
# ----------------------------
def print_ambiguity_examples(df_entities: pd.DataFrame) -> None:
    """
    Affiche 3 exemples d'ambiguïté pour le rapport Lab 1.
    Ce sont des entités qui apparaissent avec plusieurs labels différents.
    """
    ambiguous = (
        df_entities.groupby("Entity")["Label"]
        .nunique()
        .reset_index()
        .query("Label > 1")
        .head(3)
    )

    print("\n--- Exemples d'ambiguïté (pour le rapport) ---")
    if ambiguous.empty:
        print("  Aucune ambiguïté détectée automatiquement.")
        print("  Cherche manuellement dans le CSV des entités mal classées.")
    else:
        for _, row in ambiguous.iterrows():
            labels = df_entities[df_entities["Entity"] == row["Entity"]]["Label"].unique()
            print(f"  '{row['Entity']}' classé comme : {labels}")


# ----------------------------
# Main
# ----------------------------
def main():
    print("1. Chargement du modèle spaCy (en_core_web_sm)...")
    nlp = spacy.load("en_core_web_sm")

    print("\n2. Chargement des données crawlées...")
    data = load_jsonl(INPUT_FILE)

    print("\n3. Extraction des entités (NER)...")
    df_entities = extract_entities(nlp, data)
    df_entities.to_csv(OUTPUT_ENTITIES, index=False)
    print(f"   Sauvegardé : {OUTPUT_ENTITIES}")

    print("\n4. Extraction des relations...")
    df_relations = extract_relations(nlp, data)
    df_relations.to_csv(OUTPUT_RELATIONS, index=False)
    print(f"   Sauvegardé : {OUTPUT_RELATIONS}")

    print_ambiguity_examples(df_entities)

    print("\n--- Résumé ---")
    print(f"  Entités  : {len(df_entities)}")
    print(f"  Relations: {len(df_relations)}")
    print(f"  Types d'entités : {df_entities['Label'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
