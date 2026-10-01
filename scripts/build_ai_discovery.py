#!/usr/bin/env python3
from __future__ import annotations
import html, json, pathlib, re
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
BOOKS = ROOT / "books"
BOOKS_JSON = BOOKS / "books.json"
COMPLETED_JSON = BOOKS / "completed.json"
CATALOG_JSON = BOOKS / "catalog.json"
ALL_BOOKS = BOOKS / "all-books" / "index.html"
LLMS_TXT = ROOT / "llms.txt"

SITE = "https://faramarzkowsari.github.io"
BOOKS_BASE = f"{SITE}/books"
AUTHOR = "Faramarz Kowsari"
AUTHOR_URL = f"{BOOKS_BASE}/author/"
SOCIAL_IMAGE = f"{BOOKS_BASE}/images/Social%20Preview.jpg"

def load_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default

def esc(value):
    return html.escape(str(value or ""), quote=True)

def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def merge_public_books():
    raw_books = load_json(BOOKS_JSON, [])
    completed = load_json(COMPLETED_JSON, {})
    if not isinstance(raw_books, list):
        raise SystemExit("books/books.json must contain a JSON array")
    if not isinstance(completed, dict):
        completed = {}
    public = []
    for base in raw_books:
        if not isinstance(base, dict):
            continue
        slug = clean_text(base.get("slug"))
        if not slug:
            continue
        page_exists = (BOOKS / slug / "index.html").exists()
        is_public = slug in completed or (base.get("status") == "active" and page_exists)
        if not is_public:
            continue
        merged = dict(base)
        override = completed.get(slug)
        if isinstance(override, dict):
            for key, value in override.items():
                if value not in ("", None, [], {}):
                    merged[key] = value
        title = clean_text(merged.get("title")) or slug.replace("-", " ").title()
        gid = clean_text(merged.get("google_books_id"))
        google_url = clean_text(merged.get("google_books_url"))
        if not google_url and gid:
            google_url = f"https://play.google.com/store/books/details?id={gid}"
        preview_url = f"https://play.google.com/books/reader?id={gid}&hl=en" if gid else ""
        public.append({
            "slug": slug,
            "title": title,
            "subtitle": clean_text(merged.get("subtitle")),
            "author": AUTHOR,
            "language": clean_text(merged.get("language")) or "English",
            "category": clean_text(merged.get("category")) or "Books",
            "summary": str(merged.get("summary") or "").strip(),
            "seo_description": clean_text(merged.get("seo_description")),
            "key_topics": [clean_text(x) for x in (merged.get("key_topics") or []) if clean_text(x)],
            "learning": [clean_text(x) for x in (merged.get("learning") or []) if clean_text(x)],
            "target_audience": clean_text(merged.get("target_audience")),
            "url": f"{BOOKS_BASE}/{slug}/",
            "google_books_id": gid,
            "google_books_url": google_url,
            "preview_url": preview_url,
            "cover_url": clean_text(merged.get("cover_url")),
            "published_date": clean_text(merged.get("published_date")),
            "isbn": clean_text(merged.get("isbn")),
            "doi": clean_text(merged.get("doi")),
        })
    public.sort(key=lambda b: (b["category"].casefold(), b["title"].casefold()))
    return public

def write_catalog(books):
    payload = {
        "name": "Faramarz Kowsari Official Multilingual Books Library",
        "description": "Machine-readable catalog of the public book landing pages on the official Faramarz Kowsari website.",
        "author": {"name": AUTHOR, "url": AUTHOR_URL, "orcid": "https://orcid.org/0000-0003-1692-0453"},
        "canonical": f"{BOOKS_BASE}/",
        "text_index": f"{BOOKS_BASE}/all-books/",
        "sitemap": f"{BOOKS_BASE}/sitemap.xml",
        "book_count": len(books),
        "books": books,
    }
    CATALOG_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def itemlist_schema(books):
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "@id": f"{BOOKS_BASE}/all-books/#collection",
        "name": "All Books by Faramarz Kowsari — Text Index",
        "url": f"{BOOKS_BASE}/all-books/",
        "description": "Text-first index of the official multilingual books library of Faramarz Kowsari.",
        "author": {"@type": "Person", "@id": f"{SITE}/#person", "name": AUTHOR, "url": AUTHOR_URL},
        "mainEntity": {
            "@type": "ItemList",
            "numberOfItems": len(books),
            "itemListElement": [
                {"@type": "ListItem", "position": i, "name": b["title"], "url": b["url"]}
                for i, b in enumerate(books, start=1)
            ],
        },
    }

def book_entry(book):
    subtitle = f'<p class="subtitle">{esc(book["subtitle"])}</p>' if book["subtitle"] else ""
    summary = str(book["summary"] or "").strip()
    if summary:
        summary_html = "\n".join(f"<p>{esc(p.strip())}</p>" for p in summary.split("\n\n") if p.strip())
    elif book["seo_description"]:
        summary_html = f'<p>{esc(book["seo_description"])}</p>'
    else:
        summary_html = "<p>Open the canonical book page for the full description.</p>"
    topic_html = ""
    if book["key_topics"]:
        topics = "".join(f"<li>{esc(topic)}</li>" for topic in book["key_topics"][:12])
        topic_html = f'<ul class="topics">{topics}</ul>'
    links = [f'<a href="{esc(book["url"])}">Official book page</a>']
    if book["google_books_url"]:
        links.append(f'<a href="{esc(book["google_books_url"])}" target="_blank" rel="noopener noreferrer">Google Books</a>')
    if book["preview_url"]:
        links.append(f'<a href="{esc(book["preview_url"])}" target="_blank" rel="noopener noreferrer">Free preview</a>')
    meta = " · ".join(x for x in [book["language"], book["category"]] if x)
    return f"""<article class="book-entry">
<h3><a href="{esc(book['url'])}">{esc(book['title'])}</a></h3>
{subtitle}
<p class="meta">{esc(meta)}</p>
{summary_html}
{topic_html}
<p class="links">{' · '.join(links)}</p>
</article>"""

def write_all_books(books):
    grouped = defaultdict(list)
    for book in books:
        grouped[book["category"]].append(book)
    sections = []
    for category in sorted(grouped, key=str.casefold):
        cat_id = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-") or "books"
        entries = "\n".join(book_entry(book) for book in grouped[category])
        sections.append(f'<section class="category" aria-labelledby="cat-{cat_id}"><h2 id="cat-{cat_id}">{esc(category)}</h2>{entries}</section>')
    schema = json.dumps(itemlist_schema(books), ensure_ascii=False)
    css = """:root{color-scheme:light dark;--bg:#f7f8fc;--surface:#fff;--text:#152033;--muted:#5d687a;--line:#dfe4ee;--accent:#3157d5}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:16px/1.65 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
main{width:min(1120px,calc(100% - 32px));margin:auto;padding:34px 0 70px}.top{padding:28px;border:1px solid var(--line);border-radius:22px;background:var(--surface);margin-bottom:28px}
h1{margin:.1em 0 .35em;font-size:clamp(2rem,5vw,3.4rem);line-height:1.05}h2{margin:40px 0 16px}h3{margin:.1em 0 .25em;font-size:1.24rem}a{color:var(--accent);text-underline-offset:3px}
.nav{display:flex;flex-wrap:wrap;gap:12px;margin-top:18px}.count,.meta,.subtitle{color:var(--muted)}
.book-entry{padding:20px 0;border-top:1px solid var(--line)}.book-entry:first-of-type{border-top:0}.book-entry p{max-width:88ch}.topics{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}
.topics li{border:1px solid var(--line);background:var(--surface);padding:5px 9px;border-radius:999px;font-size:.9rem}.links{font-weight:700}.category{scroll-margin-top:16px}
@media (prefers-color-scheme:dark){:root{--bg:#0f1420;--surface:#171e2d;--text:#f1f4fa;--muted:#b1bac9;--line:#2b3548;--accent:#9eb4ff}}
@media print{body{background:#fff;color:#000}.top,.book-entry{border-color:#bbb}.nav{display:none}}"""
    html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">
<title>All Books by Faramarz Kowsari | Text Index</title>
<meta name="description" content="Text-first, crawlable index of the official multilingual books library of Faramarz Kowsari, with canonical book pages, topics, Google Books links and previews.">
<link rel="canonical" href="{BOOKS_BASE}/all-books/">
<link rel="alternate" type="application/json" href="{BOOKS_BASE}/catalog.json" title="Machine-readable book catalog">
<link rel="alternate" type="text/plain" href="{SITE}/llms.txt" title="LLM-readable site index">
<meta property="og:type" content="website"><meta property="og:title" content="All Books by Faramarz Kowsari">
<meta property="og:description" content="Text-first index of the official multilingual books library.">
<meta property="og:url" content="{BOOKS_BASE}/all-books/"><meta property="og:image" content="{SOCIAL_IMAGE}">
<meta name="twitter:card" content="summary_large_image"><script type="application/ld+json">{schema}</script><style>{css}</style></head>
<body><main><header class="top"><p><strong>Official Books Library</strong></p><h1>All Books by Faramarz Kowsari</h1>
<p>This text-first index exposes the public catalog in a simple, crawlable format for readers, search engines and answer engines. Each title links to its canonical landing page, and Google Books links are included where available.</p>
<p class="count">{len(books)} public book pages in this index.</p>
<nav class="nav" aria-label="Books discovery navigation"><a href="{SITE}/">Official website</a><a href="{BOOKS_BASE}/">Visual book catalog</a><a href="{BOOKS_BASE}/topics/">Browse by topic</a><a href="{AUTHOR_URL}">Author profile</a><a href="{BOOKS_BASE}/catalog.json">JSON catalog</a><a href="{BOOKS_BASE}/sitemap.xml">Books sitemap</a><a href="{SITE}/llms.txt">llms.txt</a></nav></header>
{''.join(sections)}</main></body></html>"""
    ALL_BOOKS.parent.mkdir(parents=True, exist_ok=True)
    ALL_BOOKS.write_text(html_doc, encoding="utf-8")

def write_llms(books):
    lines = [
        "# Faramarz Kowsari — Official Website and Multilingual Books Library", "",
        "> Canonical public discovery index for the official website, author profile, books library and book landing pages of Faramarz Kowsari.", "",
        f"- Official website: {SITE}/", f"- Author profile: {AUTHOR_URL}", f"- Books library: {BOOKS_BASE}/",
        f"- Text-first all-books index: {BOOKS_BASE}/all-books/", f"- Machine-readable catalog: {BOOKS_BASE}/catalog.json",
        f"- Books sitemap: {BOOKS_BASE}/sitemap.xml", f"- Master sitemap: {SITE}/sitemap.xml",
        "- ORCID: https://orcid.org/0000-0003-1692-0453",
        "- Google Scholar: https://scholar.google.com/citations?user=G7tP5WMAAAAJ&hl=en",
        "- GitHub: https://github.com/FaramarzKowsari",
        "- LinkedIn: https://www.linkedin.com/in/faramarzkowsari",
        "- Instagram: https://www.instagram.com/faramarzkowsari/",
        "- Zenodo project DOI: https://doi.org/10.5281/zenodo.23046366", "",
        "## Source priority", "",
        "- Use each canonical book landing page for book-specific descriptions, topics, intended audience and outbound Google Books links.",
        "- Use the author profile for biographical information.",
        "- Use catalog.json for structured discovery and the all-books text index for a crawlable human-readable overview.",
        "- The repository/site DOI identifies the evolving website and books-library project; it is not a DOI for every individual book.", "",
        f"## Books ({len(books)})", ""
    ]
    for book in sorted(books, key=lambda b: b["title"].casefold()):
        description = book["seo_description"] or clean_text(book["summary"])[:280]
        suffix = f" — {book['language']}; {book['category']}"
        if description:
            suffix += f". {description}"
        lines.append(f"- [{book['title']}]({book['url']}){suffix}")
    lines.extend(["", "## Discovery notes", "",
        "- Public pages are intended to be discoverable by general search and answer engines.",
        "- robots.txt and XML sitemaps are the authoritative crawl-discovery controls.",
        "- llms.txt is an additional convenience index and is not a replacement for robots.txt, sitemaps or canonical HTML pages.", ""])
    LLMS_TXT.write_text("\n".join(lines), encoding="utf-8")

def patch_books_index():
    path = BOOKS / "index.html"
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    original = text
    text = re.sub(r'\n?<link[^>]+data-ai-discovery="[^"]+"[^>]*>', "", text)
    alternates = (
        '\n<link rel="alternate" type="application/json" href="./catalog.json" title="Machine-readable book catalog" data-ai-discovery="catalog">'
        '\n<link rel="alternate" type="text/plain" href="../llms.txt" title="LLM-readable site index" data-ai-discovery="llms">'
    )
    text = text.replace("</head>", alternates + "\n</head>", 1)
    text = re.sub(r'<a class="action" href="\./all-books/"[^>]*data-ai-discovery="text-index"[^>]*>.*?</a>', "", text, count=1, flags=re.S)
    link = '<a class="action" href="./all-books/" data-ai-discovery="text-index" aria-label="Open the text-first index of all Faramarz Kowsari books">All books · text index</a>'
    text = text.replace('<div class="actions">', '<div class="actions">' + link, 1)
    if text != original:
        path.write_text(text, encoding="utf-8")

def main():
    books = merge_public_books()
    write_catalog(books)
    write_all_books(books)
    write_llms(books)
    patch_books_index()
    print(f"AI discovery surfaces generated for {len(books)} public books.")

if __name__ == "__main__":
    main()
