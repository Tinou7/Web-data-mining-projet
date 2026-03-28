"""
src/crawl/crawler.py

Crawle les pages Wikipedia sur les drapeaux du monde et sauvegarde
le contenu nettoyé dans data/crawler_output.jsonl.

Usage :
    python src/crawl/crawler.py
"""

import trafilatura
import json
from pathlib import Path

# ----------------------------
# Configuration
# ----------------------------
OUTPUT_FILE = Path("data/crawler_output.jsonl")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

MIN_WORDS = 500

URLS = [
    "https://en.wikipedia.org/wiki/Flags_of_Oceania",
    "https://en.wikipedia.org/wiki/Flags_of_South_America",
    "https://en.wikipedia.org/wiki/Flags_of_North_America",
    "https://en.wikipedia.org/wiki/Flags_of_Asia",
    "https://en.wikipedia.org/wiki/Flags_of_Africa",
    "https://en.wikipedia.org/wiki/Flags_of_Europe",
    "https://en.wikipedia.org/wiki/National_flag",
    "https://en.wikipedia.org/wiki/Flag",
    "https://en.wikipedia.org/wiki/Vexillology",
    "https://en.wikipedia.org/wiki/Flag_of_France",
    "https://en.wikipedia.org/wiki/Flag_of_Japan",
    "https://en.wikipedia.org/wiki/Flag_of_Brazil",
    "https://en.wikipedia.org/wiki/Flag_of_the_United_States",
    "https://en.wikipedia.org/wiki/Flag_of_the_United_Kingdom",
    "https://en.wikipedia.org/wiki/Flag_of_Canada",
    "https://en.wikipedia.org/wiki/Flag_of_China",
    "https://en.wikipedia.org/wiki/Flag_of_India",
    "https://en.wikipedia.org/wiki/Flag_of_Australia",
    "https://en.wikipedia.org/wiki/Flag_of_Germany",
    "https://en.wikipedia.org/wiki/Flag_of_Italy",
]

# ----------------------------
# Pipeline
# ----------------------------
def is_useful(text: str, min_words: int = MIN_WORDS) -> bool:
    """Retourne True si la page contient assez de contenu."""
    return len(text.split()) >= min_words


def crawl(urls: list, output_file: Path) -> int:
    """
    Crawle chaque URL, extrait le texte principal avec trafilatura,
    filtre les pages trop courtes, et sauvegarde en JSONL.
    Retourne le nombre de pages conservées.
    """
    kept = 0

    with open(output_file, "w", encoding="utf-8") as f:
        for url in urls:
            downloaded = trafilatura.fetch_url(url)

            if not downloaded:
                print(f"  erreur de téléchargement : {url}")
                continue

            text = trafilatura.extract(downloaded)

            if not text:
                print(f"  pas de texte extrait : {url}")
                continue

            word_count = len(text.split())

            if not is_useful(text):
                print(f"  ignoré (trop court, {word_count} mots) : {url}")
                continue

            entry = {"url": url, "text": text, "word_count": word_count}
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            kept += 1
            print(f"  gardé ({word_count} mots) : {url}")

    return kept


def main():
    print(f"Crawling de {len(URLS)} URLs...\n")
    kept = crawl(URLS, OUTPUT_FILE)
    print(f"\nTerminé : {kept}/{len(URLS)} pages conservées")
    print(f"Sortie  : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
