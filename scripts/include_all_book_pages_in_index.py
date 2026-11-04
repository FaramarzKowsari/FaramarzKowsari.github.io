#!/usr/bin/env python3
"""Keep every existing public book landing page discoverable in /books/.

The reviewed catalog drives the main book grid. Other published editions and
legacy titles also have dedicated pages and Google Books destinations, and
must remain discoverable while their source review is being prepared. This
additive post-build step never changes existing cards or their URLs.
"""

from __future__ import annotations

from html import escape, unescape
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
INDEX = BOOKS / "index.html"
SKIP = {"all-books", "author", "covers", "topics", "de", "es", "fr", "pt-br", "ru", "tr"}
START = "<!-- additional-published-book-pages:start -->"
END = "<!-- additional-published-book-pages:end -->"


def match_attr(tag: str, name: str) -> str:
    result = re.search(rf'\b{re.escape(name)}="([^"]+)"', tag, re.I)
    return unescape(result.group(1)) if result else ""


def book_information(path: Path) -> dict | None:
    page = path.read_text(encoding="utf-8")
    h1 = re.search(r"<h1\b[^>]*>(.*?)</h1>", page, re.I | re.S)
    cover_link = re.search(
        r'<a\b(?=[^>]*class="[^"]*\bbook-cover-link\b)[^>]*>\s*<img\b[^>]*>',
        page, re.I | re.S,
    )
    if not h1 or not cover_link:
        return None
    title = unescape(re.sub(r"<[^>]+>", "", h1.group(1))).strip()
    anchor_tag, image_tag = cover_link.group(0).split(">", 1)
    href = match_attr(anchor_tag, "href")
    src = match_attr(image_tag, "src")
    if not title or not href.startswith("https://play.google.com/") or not src.startswith("https://"):
        return None
    lang_match = re.search(r'<html\b[^>]*lang="([^"]+)"', page, re.I)
    lang = lang_match.group(1) if lang_match else "en"
    return {"slug": path.parent.name, "title": title, "href": href, "src": src, "lang": lang}


def add_schema_entries(document: str, additions: list[dict]) -> str:
    # Keep the JSON-LD ItemList consistent with the visible catalog results.
    def enhance(match: re.Match) -> str:
        script = match.group(1)
        if '"@graph"' not in script or '"ItemList"' not in script:
            return match.group(0)
        try:
            data = json.loads(script)
        except json.JSONDecodeError:
            return match.group(0)
        item_list = next((x for x in data.get("@graph", []) if x.get("@type") == "ItemList"), None)
        if item_list is None:
            return match.group(0)
        entries = item_list.setdefault("itemListElement", [])
        existing = {x.get("url") for x in entries}
        for book in additions:
            url = f"https://faramarzkowsari.github.io/books/{book['slug']}/"
            if url not in existing:
                entries.append({"@type": "ListItem", "position": len(entries) + 1, "url": url, "name": book["title"]})
                existing.add(url)
        item_list["numberOfItems"] = len(entries)
        return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "</script>"

    return re.sub(r'<script type="application/ld\+json">(.*?)</script>', enhance, document, flags=re.I | re.S)


def main() -> None:
    document = INDEX.read_text(encoding="utf-8")
    document = re.sub(re.escape(START) + r".*?" + re.escape(END), "", document, flags=re.S)
    known = set(re.findall(r'<h2><a href="\./([^/]+)/">', document))
    additions = []
    for path in sorted(BOOKS.glob("*/index.html")):
        if path.parent.name in SKIP or path.parent.name in known:
            continue
        book = book_information(path)
        if book:
            additions.append(book)
    if not additions:
        print("All discoverable book pages are already indexed.")
        return

    cards = []
    for book in additions:
        title = escape(book["title"])
        slug = escape(book["slug"], quote=True)
        href = escape(book["href"], quote=True)
        src = escape(book["src"], quote=True)
        label = escape(f"Book cover of {book['title']} by Faramarz Kowsari", quote=True)
        search = escape(f"{book['title']} {book['lang']}".lower(), quote=True)
        cards.append(
            f'<article class="card" data-search="{search}">'
            f'<a href="{href}" target="_blank" rel="noopener noreferrer" aria-label="View {title} on Google Books">'
            f'<img class="cover" src="{src}" alt="{label}" loading="lazy" decoding="async"></a>'
            f'<div class="card-body"><h2><a href="./{slug}/">{title}</a></h2>'
            f'<div class="meta">{escape(book["lang"].upper())}</div>'
            f'<a class="btn" href="./{slug}/" aria-label="View book: {title}">View book</a>'
            '</div></article>'
        )
    section = (
        f'\n{START}\n<section aria-labelledby="additional-book-pages-title" class="additional-book-pages">'
        '<h2 id="additional-book-pages-title">More Published Books &amp; Special Editions</h2>'
        '<p>Browse further published titles and language editions. Editorial descriptions for some of these books are being reviewed against their source text.</p>'
        '<div class="grid" aria-label="Additional published books">'
        + ''.join(cards) + f'</div></section>\n{END}\n'
    )
    document = document.replace("</main>", section + "</main>", 1)
    document = add_schema_entries(document, additions)
    total = len(known) + len(additions)
    document = re.sub(r'(<p id="completed-count"[^>]*>)\d+ books\.', rf'\g<1>{total} books.', document, count=1)
    INDEX.write_text(document, encoding="utf-8")
    print(f"Added {len(additions)} existing book pages to the main book library index ({total} total).")


if __name__ == "__main__":
    main()
