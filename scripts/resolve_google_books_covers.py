#!/usr/bin/env python3
"""Resolve the best available Google Books cover URL without storing cover bytes.

This script keeps a tiny URL-only cache in books/google-books-cover-index.json.
Existing cached entries are reused, so a library with thousands of books does not
hammer the Google Books API on every build. New books are resolved once.

No image is downloaded, proxied, cached, or committed to this repository.
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
INDEX = BOOKS / "google-books-cover-index.json"
API = "https://www.googleapis.com/books/v1/volumes/{}"
PRIORITY = ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail")
FORCE = os.getenv("REFRESH_GOOGLE_BOOK_COVERS", "").strip().lower() in {"1", "true", "yes"}
MAX_WORKERS = max(1, min(8, int(os.getenv("GOOGLE_BOOKS_COVER_WORKERS", "6") or "6")))
TIMEOUT = float(os.getenv("GOOGLE_BOOKS_COVER_TIMEOUT", "12") or "12")


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def is_google_books_cover(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    host = (urlsplit(url).hostname or "").lower()
    return host in {"books.google.com", "books.googleusercontent.com"} and "/books/content" in urlsplit(url).path


def normalize_cover(url: str) -> str:
    """Use HTTPS and remove the decorative edge=curl query parameter."""
    parts = urlsplit(str(url or "").strip())
    if not parts.scheme or not parts.netloc:
        return str(url or "").strip()
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k.lower() != "edge"]
    return urlunsplit(("https", parts.netloc, parts.path, urlencode(query), parts.fragment))


def fetch_one(gid: str) -> tuple[str, dict | None, str | None]:
    req = urllib.request.Request(
        API.format(gid),
        headers={
            "Accept": "application/json",
            "User-Agent": "FaramarzKowsari-GitHubBooks/1.0 (+https://faramarzkowsari.github.io/books/)",
        },
    )
    last_error = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as response:
                payload = json.load(response)
            links = ((payload or {}).get("volumeInfo") or {}).get("imageLinks") or {}
            for variant in PRIORITY:
                url = normalize_cover(links.get(variant) or "")
                if is_google_books_cover(url):
                    return gid, {"url": url, "variant": variant, "source": "google_books_api"}, None
            return gid, None, "Google Books returned no usable imageLinks"
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.5 * (attempt + 1))
    return gid, None, last_error or "unknown error"


def main() -> None:
    books = load_json(DATA, [])
    cache = load_json(INDEX, {})
    if not isinstance(books, list):
        raise SystemExit("books/books.json must contain a JSON array")
    if not isinstance(cache, dict):
        cache = {}

    catalog_by_gid = {}
    for row in books:
        if not isinstance(row, dict):
            continue
        gid = str(row.get("google_books_id") or "").strip()
        if gid:
            catalog_by_gid[gid] = row

    # Remove stale entries for books no longer in the catalog.
    cache = {gid: value for gid, value in cache.items() if gid in catalog_by_gid and isinstance(value, dict)}

    unresolved = []
    for gid, row in catalog_by_gid.items():
        cached = cache.get(gid) or {}
        cached_url = cached.get("url") or ""
        if not FORCE and is_google_books_cover(cached_url):
            continue
        unresolved.append(gid)

    resolved = 0
    failed = []
    if unresolved:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(fetch_one, gid) for gid in unresolved]
            for future in concurrent.futures.as_completed(futures):
                gid, entry, error = future.result()
                if entry:
                    cache[gid] = entry
                    resolved += 1
                else:
                    # Keep a usable catalog URL as a non-sticky fallback. Because
                    # it is not written to the cache, a later build will retry.
                    row = catalog_by_gid[gid]
                    fallback = normalize_cover(str(row.get("cover_url") or ""))
                    failed.append((gid, error or "unresolved", fallback if is_google_books_cover(fallback) else ""))

    INDEX.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(dict(sorted(cache.items())), ensure_ascii=False, indent=2) + "\n"
    old = INDEX.read_text(encoding="utf-8") if INDEX.exists() else ""
    if rendered != old:
        INDEX.write_text(rendered, encoding="utf-8")

    print(
        f"Google Books cover resolver: {len(catalog_by_gid)} catalog IDs; "
        f"{len(cache)} cached best-cover URLs; {resolved} newly resolved; {len(failed)} retryable failure(s)."
    )
    for gid, error, fallback in failed[:30]:
        note = "catalog fallback remains available" if fallback else "no fallback"
        print(f"WARNING: {gid}: {error} ({note})")
    if len(failed) > 30:
        print(f"WARNING: {len(failed) - 30} additional cover-resolution failure(s) omitted.")


if __name__ == "__main__":
    main()
