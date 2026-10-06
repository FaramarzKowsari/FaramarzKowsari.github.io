#!/usr/bin/env python3
"""Build a paginated Google-hosted book-cover gallery for image discovery.

The gallery contains only HTML references to Google Books cover URLs. It stores
no cover image bytes in the repository and remains practical as the catalog grows
well beyond one thousand titles.
"""

from __future__ import annotations

import html
import json
import math
import pathlib
import shutil

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
DATA = BOOKS / "books.json"
INDEX = BOOKS / "google-books-cover-index.json"
OUT = BOOKS / "covers"
SITE = "https://faramarzkowsari.github.io/books"
AUTHOR = "Faramarz Kowsari"
PAGE_SIZE = 96


def load_json(path: pathlib.Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def esc(value):
    return html.escape(str(value or ""), quote=True)


def public_books():
    books = load_json(DATA, [])
    cache = load_json(INDEX, {})
    if not isinstance(books, list):
        raise SystemExit("books/books.json must contain a JSON array")
    if not isinstance(cache, dict):
        cache = {}

    rows = []
    for book in books:
        if not isinstance(book, dict) or book.get("status", "active") != "active":
            continue
        slug = str(book.get("slug") or "").strip("/")
        gid = str(book.get("google_books_id") or "").strip()
        if not slug or not gid or not (BOOKS / slug / "index.html").exists():
            continue
        entry = cache.get(gid) if isinstance(cache.get(gid), dict) else {}
        cover = str(entry.get("url") or book.get("cover_url") or "").strip()
        if not cover.startswith(("https://books.google.com/", "https://books.googleusercontent.com/")):
            continue
        rows.append(
            {
                "slug": slug,
                "gid": gid,
                "title": book.get("title") or "Untitled",
                "subtitle": book.get("subtitle") or "",
                "language": book.get("language") or "",
                "category": book.get("category") or "",
                "cover": cover,
            }
        )
    rows.sort(key=lambda row: (str(row["title"]).casefold(), row["gid"]))
    return rows


def page_url(page_number: int) -> str:
    if page_number == 1:
        return f"{SITE}/covers/"
    return f"{SITE}/covers/page/{page_number}/"


def page_path(page_number: int) -> pathlib.Path:
    if page_number == 1:
        return OUT / "index.html"
    return OUT / "page" / str(page_number) / "index.html"


def nav_html(page_number: int, page_count: int) -> str:
    links = []
    if page_number > 1:
        links.append(f'<a href="{esc(page_url(page_number - 1))}">← Previous</a>')
    links.append(f'<span>Page {page_number} of {page_count}</span>')
    if page_number < page_count:
        links.append(f'<a href="{esc(page_url(page_number + 1))}">Next →</a>')
    return '<nav class="pager" aria-label="Cover gallery pages">' + "".join(links) + "</nav>"


def render_page(items, page_number: int, page_count: int, total: int) -> str:
    canonical = page_url(page_number)
    title = "Book Covers by Faramarz Kowsari" if page_number == 1 else f"Book Covers by Faramarz Kowsari — Page {page_number}"
    description = (
        f"Browse {total} Google Books cover images for books by Faramarz Kowsari. "
        "Each cover links to its dedicated book page with structured metadata and Google Books access."
    )
    first_cover = items[0]["cover"] if items else ""
    prev_link = f'<link rel="prev" href="{esc(page_url(page_number - 1))}">' if page_number > 1 else ""
    next_link = f'<link rel="next" href="{esc(page_url(page_number + 1))}">' if page_number < page_count else ""
    og_image = f'<meta property="og:image" content="{esc(first_cover)}">' if first_cover else ""

    cards = []
    item_list = []
    start_position = (page_number - 1) * PAGE_SIZE
    for offset, item in enumerate(items, start=1):
        position = start_position + offset
        book_url = f"{SITE}/{item['slug']}/"
        alt = f"Book cover of {item['title']} by {AUTHOR}"
        meta_bits = [x for x in (item["language"], item["category"]) if x]
        meta = " · ".join(meta_bits)
        cards.append(
            f'''<article class="cover-card">
  <a class="cover-link" href="{esc(book_url)}" aria-label="Open {esc(item['title'])}">
    <img src="{esc(item['cover'])}" alt="{esc(alt)}" title="{esc(item['title'])} — book cover by {AUTHOR}" loading="lazy" decoding="async">
  </a>
  <div class="cover-body">
    <h2><a href="{esc(book_url)}">{esc(item['title'])}</a></h2>
    <p class="author">By <a rel="author" href="{SITE}/author/">{AUTHOR}</a></p>
    {f'<p class="meta">{esc(meta)}</p>' if meta else ''}
  </div>
</article>'''
        )
        item_list.append(
            {
                "@type": "ListItem",
                "position": position,
                "url": book_url,
                "name": item["title"],
                "image": item["cover"],
            }
        )

    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "CollectionPage",
                "@id": canonical + "#collection",
                "url": canonical,
                "name": title,
                "description": description,
                "author": {"@id": "https://faramarzkowsari.github.io/#person"},
                "mainEntity": {"@id": canonical + "#covers"},
            },
            {
                "@type": "ItemList",
                "@id": canonical + "#covers",
                "numberOfItems": total,
                "itemListElement": item_list,
            },
        ],
    }

    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large,max-video-preview:-1">
<meta name="author" content="{AUTHOR}">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{esc(canonical)}">
<link rel="author" href="{SITE}/author/" title="{AUTHOR} author profile">
{prev_link}
{next_link}
<meta property="og:type" content="website">
<meta property="og:site_name" content="Faramarz Kowsari Books">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:url" content="{esc(canonical)}">
{og_image}
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False, separators=(",", ":"))}</script>
<style>
:root{{--bg:#f7f7f8;--card:#fff;--text:#171717;--muted:#667085;--line:#e4e7ec;--accent:#111827}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--text);font:16px/1.55 Inter,system-ui,-apple-system,Segoe UI,sans-serif}}
a{{color:inherit}}main{{width:min(1240px,calc(100% - 32px));margin:auto;padding:34px 0 70px}}.crumbs{{margin-bottom:20px;color:var(--muted);font-size:14px}}
.hero{{margin-bottom:28px}}.hero h1{{font-size:clamp(34px,5vw,62px);line-height:1.04;letter-spacing:-.045em;margin:0 0 12px}}.hero p{{max-width:780px;color:var(--muted);font-size:18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:18px}}.cover-card{{background:var(--card);border:1px solid var(--line);border-radius:16px;overflow:hidden;box-shadow:0 7px 22px rgba(0,0,0,.04)}}
.cover-link{{display:block;background:#eceef1}}.cover-link img{{display:block;width:100%;aspect-ratio:2/3;object-fit:cover}}.cover-body{{padding:13px 14px 16px}}
.cover-body h2{{font-size:16px;line-height:1.3;margin:0 0 8px}}.cover-body h2 a{{text-decoration:none}}.cover-body h2 a:hover{{text-decoration:underline}}
.author,.meta{{margin:5px 0;color:var(--muted);font-size:13px}}.author a{{font-weight:700}}.pager{{display:flex;justify-content:center;align-items:center;gap:14px;flex-wrap:wrap;margin:32px 0 0}}
.pager a,.pager span{{padding:10px 13px;border:1px solid var(--line);border-radius:999px;background:#fff;text-decoration:none}}@media(max-width:600px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}}}}
</style>
</head>
<body>
<main>
<nav class="crumbs"><a href="../">Books</a> › Book Covers</nav>
<section class="hero">
  <p>Official visual catalog</p>
  <h1>{esc(title)}</h1>
  <p>{esc(description)}</p>
  <p><a href="{SITE}/author/">Author profile</a> · <a href="{SITE}/">All books</a></p>
</section>
{nav_html(page_number, page_count)}
<section class="grid" aria-label="Book cover gallery">
{''.join(cards)}
</section>
{nav_html(page_number, page_count)}
</main>
</body>
</html>'''


def main() -> None:
    rows = public_books()
    if OUT.exists():
        for child in OUT.iterdir():
            if child.name == "index.html" or child.name == "page":
                if child.is_dir():
                    shutil.rmtree(child)
                else:
                    child.unlink()
    OUT.mkdir(parents=True, exist_ok=True)

    page_count = max(1, math.ceil(len(rows) / PAGE_SIZE))
    for page_number in range(1, page_count + 1):
        start = (page_number - 1) * PAGE_SIZE
        items = rows[start : start + PAGE_SIZE]
        path = page_path(page_number)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_page(items, page_number, page_count, len(rows)), encoding="utf-8")

    print(f"Google Books cover gallery: {len(rows)} cover(s) across {page_count} page(s); image bytes remain on Google Books.")


if __name__ == "__main__":
    main()
