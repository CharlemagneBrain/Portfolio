#!/usr/bin/env python3
"""
Scrape Google Scholar publications and save to JSON.
Uses the scholarly library to fetch data for a given author.
"""

import json
import os
import sys
from datetime import datetime

from scholarly import scholarly


# Google Scholar author ID
AUTHOR_ID = "v2VkcZEAAAAJ"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "publications.json")


def fetch_publications():
    """Fetch all publications for the configured author from Google Scholar."""
    print(f"Fetching author profile for ID: {AUTHOR_ID}")
    author = scholarly.search_author_id(AUTHOR_ID)
    author = scholarly.fill(author, sections=["basics", "publications"])

    publications = []

    for pub in author.get("publications", []):
        # Fill each publication to get full details
        try:
            filled = scholarly.fill(pub)
        except Exception as e:
            print(f"Warning: could not fill publication: {e}")
            filled = pub

        bib = filled.get("bib", {})
        pub_year = bib.get("pub_year", "")
        title = bib.get("title", "")
        authors = bib.get("author", "")
        venue = bib.get("journal", "") or bib.get("conference", "") or bib.get("venue", "")
        abstract = bib.get("abstract", "")
        num_citations = filled.get("num_citations", 0)
        pub_url = filled.get("pub_url", "")
        eprint_url = filled.get("eprint_url", "")

        if not title:
            continue

        publications.append({
            "title": title,
            "authors": authors,
            "year": str(pub_year),
            "venue": venue,
            "abstract": abstract,
            "citations": num_citations,
            "url": pub_url,
            "pdf_url": eprint_url,
        })

    # Sort by year descending, then by citations descending
    publications.sort(key=lambda p: (p["year"], p["citations"]), reverse=True)

    return {
        "author": {
            "name": author.get("name", ""),
            "affiliation": author.get("affiliation", ""),
            "scholar_id": AUTHOR_ID,
            "citations": author.get("citedby", 0),
            "h_index": author.get("hindex", 0),
            "i10_index": author.get("i10index", 0),
        },
        "publications": publications,
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "total": len(publications),
    }


def main():
    data = fetch_publications()

    # Ensure output directory exists
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Saved {data['total']} publications to {OUTPUT_PATH}")
    print(f"Author citations: {data['author']['citations']}, h-index: {data['author']['h_index']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
