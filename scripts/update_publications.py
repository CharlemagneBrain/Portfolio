#!/usr/bin/env python3
"""
Fetch publications from OpenAlex and save to JSON.

OpenAlex is a free, open catalog of the global research system. Unlike
Google Scholar, it exposes a proper REST API that works reliably from
GitHub Actions runners (Google Scholar blocks datacenter IPs with
CAPTCHA).

Output format is kept identical to the previous scholarly-based script
so the frontend (script.js) does not need any change.
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import requests


# --- Configuration --------------------------------------------------------

# Author full name (used to resolve the OpenAlex author id)
AUTHOR_NAME = "Charles Abdoulaye Ngom"

# Affiliation hint used to disambiguate when multiple authors share a name
AFFILIATION_HINT = "INRAE"

# Google Scholar id kept in the JSON for the frontend profile link
SCHOLAR_ID = "v2VkcZEAAAAJ"

# Polite pool: OpenAlex asks clients to identify themselves via mailto
# (it doesn't need to be valid, just present). This makes the API faster
# and more reliable.
CONTACT_EMAIL = os.environ.get("OPENALEX_MAILTO", "charlesabdoulayengom@esp.sn")

OPENALEX_BASE = "https://api.openalex.org"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "publications.json")
HTTP_TIMEOUT = 30


# --- Helpers --------------------------------------------------------------

def _get(url, params=None):
    """GET an OpenAlex URL with mailto and light retry."""
    params = dict(params or {})
    params.setdefault("mailto", CONTACT_EMAIL)

    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as e:  # noqa: BLE001 — retry on any transient error
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"OpenAlex request failed for {url}: {last_err}")


def resolve_author():
    """Find the OpenAlex author id matching AUTHOR_NAME + AFFILIATION_HINT."""
    data = _get(
        f"{OPENALEX_BASE}/authors",
        params={"search": AUTHOR_NAME, "per-page": 25},
    )
    results = data.get("results", [])
    if not results:
        raise RuntimeError(f"No OpenAlex author found for '{AUTHOR_NAME}'")

    def score(a):
        inst = (a.get("last_known_institution") or {}).get("display_name", "") or ""
        affiliations = " ".join(
            (x.get("institution") or {}).get("display_name", "") or ""
            for x in (a.get("affiliations") or [])
        )
        text = f"{inst} {affiliations}".lower()
        return (
            1 if AFFILIATION_HINT.lower() in text else 0,
            a.get("works_count", 0),
        )

    results.sort(key=score, reverse=True)
    return results[0]


def reconstruct_abstract(inv_index):
    """OpenAlex stores abstracts as inverted indexes. Rebuild the text."""
    if not inv_index:
        return ""
    positions = []
    for word, idxs in inv_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(w for _, w in positions)


def format_authors(work):
    """Return a short author list in the 'CA Ngom, M Teisseire, ...' style."""
    parts = []
    for a in work.get("authorships", []) or []:
        name = ((a.get("author") or {}).get("display_name")) or ""
        if not name:
            continue
        tokens = name.split()
        if len(tokens) >= 2:
            initials = "".join(t[0] for t in tokens[:-1] if t)
            parts.append(f"{initials} {tokens[-1]}")
        else:
            parts.append(name)
    return ", ".join(parts)


def pick_venue(work):
    loc = work.get("primary_location") or {}
    src = loc.get("source") or {}
    return src.get("display_name") or work.get("host_venue", {}).get("display_name", "") or ""


def pick_url(work):
    loc = work.get("primary_location") or {}
    return loc.get("landing_page_url") or work.get("doi") or ""


def pick_pdf(work):
    best = work.get("best_oa_location") or {}
    return best.get("pdf_url") or ""


def fetch_publications():
    author = resolve_author()
    author_id = author["id"].rsplit("/", 1)[-1]  # e.g. 'A1234567'
    print(f"Resolved OpenAlex author: {author.get('display_name')} ({author_id})")

    publications = []
    cursor = "*"
    while cursor:
        page = _get(
            f"{OPENALEX_BASE}/works",
            params={
                "filter": f"author.id:{author_id}",
                "per-page": 200,
                "cursor": cursor,
            },
        )
        for w in page.get("results", []):
            title = w.get("title") or w.get("display_name") or ""
            if not title:
                continue
            publications.append({
                "title": title,
                "authors": format_authors(w),
                "year": str(w.get("publication_year") or ""),
                "venue": pick_venue(w),
                "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
                "citations": int(w.get("cited_by_count") or 0),
                "url": pick_url(w),
                "pdf_url": pick_pdf(w),
            })
        cursor = (page.get("meta") or {}).get("next_cursor")

    publications.sort(key=lambda p: (p["year"], p["citations"]), reverse=True)

    summary = author.get("summary_stats") or {}
    return {
        "author": {
            "name": author.get("display_name", AUTHOR_NAME),
            "affiliation": (author.get("last_known_institution") or {}).get("display_name", ""),
            "scholar_id": SCHOLAR_ID,
            "openalex_id": author_id,
            "citations": int(author.get("cited_by_count") or 0),
            "h_index": int(summary.get("h_index") or 0),
            "i10_index": int(summary.get("i10_index") or 0),
        },
        "publications": publications,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(publications),
    }


def _norm_title(t):
    # Keep only the first 60 alphanumeric characters (lowercased) so minor
    # punctuation / subtitle differences don't create duplicates.
    cleaned = re.sub(r"[^a-z0-9]+", "", (t or "").lower())
    return cleaned[:60]


def load_existing():
    if not os.path.exists(OUTPUT_PATH):
        return None
    try:
        with open(OUTPUT_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def merge_with_existing(fresh):
    """Merge fresh OpenAlex data with the existing JSON file.

    - Publications present in OpenAlex are refreshed (citations, urls, etc.).
    - Publications that existed before but are NOT in OpenAlex are kept
      (OpenAlex misses some conference proceedings that Google Scholar
      indexes). This makes the update strictly additive.
    """
    existing = load_existing()
    if not existing:
        return fresh

    fresh_by_key = {_norm_title(p["title"]): p for p in fresh["publications"]}
    merged = []

    # Start from OpenAlex (fresher data)
    for p in fresh["publications"]:
        merged.append(p)

    # Add any legacy publication not returned by OpenAlex
    existing_pubs = existing.get("publications", [])
    for p in existing_pubs:
        key = _norm_title(p.get("title", ""))
        if key and key not in fresh_by_key:
            merged.append(p)

    merged.sort(key=lambda p: (p.get("year", ""), p.get("citations", 0)), reverse=True)

    # Prefer fresh author stats, but fall back to existing values if OpenAlex
    # returned 0 (can happen when summary_stats is still being computed).
    ex_author = existing.get("author", {})
    fr_author = fresh["author"]
    for stat in ("citations", "h_index", "i10_index"):
        if not fr_author.get(stat) and ex_author.get(stat):
            fr_author[stat] = ex_author[stat]
    if not fr_author.get("affiliation") and ex_author.get("affiliation"):
        fr_author["affiliation"] = ex_author["affiliation"]

    return {
        "author": fr_author,
        "publications": merged,
        "updated_at": fresh["updated_at"],
        "total": len(merged),
    }


def main():
    fresh = fetch_publications()
    data = merge_with_existing(fresh)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Saved {data['total']} publications to {OUTPUT_PATH}")
    print(
        f"Author citations: {data['author']['citations']}, "
        f"h-index: {data['author']['h_index']}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        # Exit 0 so the workflow doesn't fail loudly on a transient API
        # issue; the existing JSON file is left untouched and no commit
        # will be made (git diff --quiet will be clean).
        sys.exit(0)
