#!/usr/bin/env python3
"""
Fetch publications and citing works, save to JSON.

Primary source: Google Scholar via SerpAPI (needs SERPAPI_KEY env var).
Fallback:       OpenAlex (no auth, less citation coverage).

Google Scholar does not expose a public API and blocks datacenter IPs,
so direct scraping does not work on GitHub Actions. SerpAPI handles the
scraping, rotates proxies and solves CAPTCHAs for us. Free tier is 100
queries/month which is plenty for a weekly run on a handful of papers.
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
SERPAPI_BASE = "https://serpapi.com/search.json"
SERPAPI_KEY = os.environ.get("SERPAPI_KEY")

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "publications.json")
HTTP_TIMEOUT = 30

# Max number of citing works to store per publication (keeps JSON small).
MAX_CITING_WORKS = 50
# For SerpAPI we fetch a single page of 20 citing works per publication to
# keep the monthly quota low (free tier = 100 searches/month).
SERPAPI_CITES_PER_PUB = 20


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


def fetch_citing_works(work_openalex_id):
    """Return a small list of works citing the given work, newest first."""
    if not work_openalex_id:
        return []
    try:
        page = _get(
            f"{OPENALEX_BASE}/works",
            params={
                "filter": f"cites:{work_openalex_id}",
                "per-page": MAX_CITING_WORKS,
                "sort": "publication_year:desc",
                "select": ",".join([
                    "id",
                    "title",
                    "display_name",
                    "publication_year",
                    "authorships",
                    "primary_location",
                    "doi",
                    "cited_by_count",
                ]),
            },
        )
    except Exception as e:  # noqa: BLE001
        print(f"Warning: could not fetch citing works for {work_openalex_id}: {e}")
        return []

    citing = []
    for w in page.get("results", []):
        title = w.get("title") or w.get("display_name") or ""
        if not title:
            continue
        citing.append({
            "title": title,
            "authors": format_authors(w),
            "year": str(w.get("publication_year") or ""),
            "venue": pick_venue(w),
            "url": pick_url(w),
            "citations": int(w.get("cited_by_count") or 0),
        })
    return citing


# --- SerpAPI (Google Scholar) ---------------------------------------------

def _serpapi_get(params):
    """GET serpapi.com/search.json with retry."""
    params = dict(params or {})
    params["api_key"] = SERPAPI_KEY
    last_err = None
    for attempt in range(3):
        try:
            r = requests.get(SERPAPI_BASE, params=params, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            if "error" in data:
                raise RuntimeError(f"SerpAPI returned error: {data['error']}")
            return data
        except Exception as e:  # noqa: BLE001
            last_err = e
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"SerpAPI request failed: {last_err}")


def _scholar_citing_works(cites_id):
    """Fetch the first page of citing works for a Scholar cluster id."""
    if not cites_id:
        return []
    try:
        data = _serpapi_get({
            "engine": "google_scholar",
            "cites": cites_id,
            "num": SERPAPI_CITES_PER_PUB,
            "hl": "en",
        })
    except Exception as e:  # noqa: BLE001
        print(f"Warning: SerpAPI cites fetch failed for {cites_id}: {e}")
        return []

    out = []
    for r in data.get("organic_results", []) or []:
        title = r.get("title") or ""
        if not title:
            continue
        info = r.get("publication_info", {}) or {}
        # publication_info.summary is like "Author1, Author2 - Journal, 2024 - publisher"
        summary = info.get("summary", "") or ""
        year = ""
        m = re.search(r"\b(19|20)\d{2}\b", summary)
        if m:
            year = m.group(0)
        # Extract authors (everything before the first ' - ')
        authors = ""
        venue = ""
        if " - " in summary:
            parts = summary.split(" - ")
            authors = parts[0].strip()
            if len(parts) >= 2:
                venue = re.sub(r",?\s*(19|20)\d{2}\b.*$", "", parts[1]).strip()

        out.append({
            "title": title,
            "authors": authors,
            "year": year,
            "venue": venue,
            "url": r.get("link", "") or "",
            "citations": int(((r.get("inline_links") or {}).get("cited_by") or {}).get("total") or 0),
        })
    return out


def fetch_via_serpapi():
    """Fetch author profile + publications + citing works from Google Scholar."""
    print(f"Using SerpAPI (Google Scholar) for author {SCHOLAR_ID}")
    # SerpAPI's google_scholar_author endpoint returns up to 100 articles
    # per request, with pagination via 'start'.
    articles = []
    start = 0
    author_block = None
    cited_by_block = None

    while True:
        data = _serpapi_get({
            "engine": "google_scholar_author",
            "author_id": SCHOLAR_ID,
            "hl": "en",
            "num": 100,
            "start": start,
            "sort": "pubdate",
        })
        if author_block is None:
            author_block = data.get("author", {}) or {}
        if cited_by_block is None:
            cited_by_block = data.get("cited_by", {}) or {}

        page_articles = data.get("articles", []) or []
        articles.extend(page_articles)
        if len(page_articles) < 100:
            break
        start += 100

    # Extract author stats from the cited_by table (rows: "Citations",
    # "h-index", "i10-index", each with all/since_2019 columns)
    stats = {"citations": 0, "h_index": 0, "i10_index": 0}
    for row in (cited_by_block.get("table", []) or []):
        if "citations" in row:
            stats["citations"] = int(row["citations"].get("all", 0) or 0)
        elif "h_index" in row:
            stats["h_index"] = int(row["h_index"].get("all", 0) or 0)
        elif "i10_index" in row:
            stats["i10_index"] = int(row["i10_index"].get("all", 0) or 0)

    publications = []
    for a in articles:
        title = a.get("title") or ""
        if not title:
            continue
        cited_by = (a.get("cited_by") or {})
        citations = int(cited_by.get("value") or 0)
        cites_id = cited_by.get("cites_id") or ""
        citing = _scholar_citing_works(cites_id) if (citations > 0 and cites_id) else []

        publications.append({
            "title": title,
            "authors": a.get("authors", "") or "",
            "year": str(a.get("year", "") or ""),
            "venue": a.get("publication", "") or "",
            "abstract": "",  # Scholar profile doesn't expose abstracts
            "citations": citations,
            "url": a.get("link", "") or "",
            "pdf_url": "",
            "scholar_cites_id": cites_id,
            "scholar_cited_by_url": cited_by.get("link", "") or "",
            "cited_by": citing,
        })

    publications.sort(key=lambda p: (p["year"], p["citations"]), reverse=True)

    affiliations = author_block.get("affiliations", "") or ""
    return {
        "author": {
            "name": author_block.get("name", AUTHOR_NAME),
            "affiliation": affiliations,
            "scholar_id": SCHOLAR_ID,
            "citations": stats["citations"],
            "h_index": stats["h_index"],
            "i10_index": stats["i10_index"],
            "source": "serpapi_scholar",
        },
        "publications": publications,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(publications),
    }


# --- OpenAlex (fallback) --------------------------------------------------

def fetch_via_openalex():
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
            work_openalex_id = (w.get("id") or "").rsplit("/", 1)[-1]
            citations = int(w.get("cited_by_count") or 0)
            cited_by = fetch_citing_works(work_openalex_id) if citations > 0 else []
            publications.append({
                "title": title,
                "authors": format_authors(w),
                "year": str(w.get("publication_year") or ""),
                "venue": pick_venue(w),
                "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
                "citations": citations,
                "url": pick_url(w),
                "pdf_url": pick_pdf(w),
                "openalex_id": work_openalex_id,
                "cited_by": cited_by,
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
            "source": "openalex",
        },
        "publications": publications,
        "updated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "total": len(publications),
    }


# --- Dispatcher -----------------------------------------------------------

def fetch_publications():
    """Fetch via SerpAPI if a key is available, fall back to OpenAlex."""
    if SERPAPI_KEY:
        try:
            return fetch_via_serpapi()
        except Exception as e:  # noqa: BLE001
            print(f"SerpAPI failed, falling back to OpenAlex: {e}", file=sys.stderr)
    else:
        print("No SERPAPI_KEY set, using OpenAlex.")
    return fetch_via_openalex()


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
    existing_pubs = existing.get("publications", [])
    existing_by_key = {_norm_title(p.get("title", "")): p for p in existing_pubs}
    merged = []

    # Start from fresh data. Preserve prior enrichment fields (abstract,
    # pdf_url, openalex_id, cited_by) when the fresh fetch didn't produce
    # them — e.g. Scholar never exposes abstracts, so we fall back to the
    # OpenAlex-enriched values stored in previous runs.
    preserve_fields = ("cited_by", "abstract", "pdf_url", "openalex_id")
    for p in fresh["publications"]:
        key = _norm_title(p.get("title", ""))
        prior = existing_by_key.get(key) or {}
        for field in preserve_fields:
            if not p.get(field) and prior.get(field):
                p[field] = prior[field]
        merged.append(p)

    # Add any legacy publication not returned by OpenAlex
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
