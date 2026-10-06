#!/usr/bin/env python3
"""Apply cached Google Books cover URLs to generated HTML without hosting images.

Every matching Google Books cover URL in books/**/*.html is rewritten to the
single best Google Books URL recorded for that volume ID. This keeps the cover
external while making <img>, Open Graph, Twitter and JSON-LD inputs converge on
one stable Google-hosted asset before the image-SEO pass runs.
"""

from __future__ import annotations

import html
import json
import pathlib
import re
from urllib.parse import parse_qs, urlsplit

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
INDEX = BOOKS / "google-books-cover-index.json"

# Match both normal query strings and HTML-escaped &amp; separators.
GOOGLE_COVER_RE = re.compile(
    r'https?://(?:(?:books\.google\.com|books\.googleusercontent\.com)/books/content\?[^"\'<>\s]+|play\.google\.com/books/publisher/content/images/frontcover/[^"\'<>\s]+)',
    re.I,
)


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def gid_from_url(url: str) -> str:
    raw = html.unescape(url)
    try:
        parts = urlsplit(raw)
        query = parse_qs(parts.query)
    except ValueError:
        return ""
    values = query.get("id") or []
    if values:
        return str(values[0]).strip()
    if (parts.hostname or "").lower() == "play.google.com":
        match = re.search(r"/frontcover/([^/?#]+)", parts.path)
        if match:
            return match.group(1)
    return ""


def replacement(match: re.Match[str], cache: dict) -> str:
    original = match.group(0)
    gid = gid_from_url(original)
    entry = cache.get(gid) if gid else None
    if not isinstance(entry, dict):
        return original
    url = str(entry.get("url") or "").strip()
    if not url:
        return original
    # Preserve HTML escaping when replacing an HTML attribute. Raw URLs are
    # retained inside JSON-LD script blocks.
    return html.escape(url, quote=True) if "&amp;" in original else url


def main() -> None:
    cache = load_json(INDEX, {})
    if not isinstance(cache, dict) or not cache:
        print("Google Books cover application: no cached cover index; nothing changed.")
        return

    checked = 0
    changed = 0
    replacements = 0

    for path in sorted(BOOKS.rglob("*.html")):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        checked += 1
        count = 0

        def repl(match: re.Match[str]) -> str:
            nonlocal count
            new = replacement(match, cache)
            if new != match.group(0):
                count += 1
            return new

        out = GOOGLE_COVER_RE.sub(repl, text)
        if out != text:
            path.write_text(out, encoding="utf-8")
            changed += 1
            replacements += count

    print(
        f"Google Books cover application: {checked} HTML file(s) checked; "
        f"{changed} file(s) updated; {replacements} cover URL occurrence(s) synchronized."
    )


if __name__ == "__main__":
    main()
